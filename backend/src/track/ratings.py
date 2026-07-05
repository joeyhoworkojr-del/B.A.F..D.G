"""
Self-correcting team ratings.

Team Elos ship as static priors. That is fine on day one, but a model that
never learns from results is leaving accuracy on the table. This module keeps
a per-team Elo *delta* that is nudged after every graded game via a standard
Elo update, so predictions sharpen as real outcomes come in.

The update runs on the classic base-400 logistic scale (independent of how
each sport's predictor turns an Elo into probabilities — the ratings live on
the same ~1500-2100 scale they arrived on). A margin-of-victory multiplier
rewards decisive results; deltas are capped so a small early sample can never
send a rating haywire.

Deltas are stored in the same SQLite file as the prediction ledger and are
reconciled from graded games, so the two records stay consistent.
"""
from __future__ import annotations

import math
import sqlite3
import threading
from datetime import datetime, timezone

from src.track.ledger import _db_path

_LOCK = threading.Lock()

BASE = 400.0        # logistic scale for the win-probability expectation
K = 20.0            # base update step
DELTA_CAP = 150.0   # cap on cumulative adjustment per team (Elo points)

# Modest home-field advantage per sport, on the 400 scale, so the expected
# result isn't biased. Over a balanced home/away schedule any misspecification
# averages out, but including it keeps early updates honest.
_HFA: dict[str, float] = {"nfl": 48.0, "cfl": 48.0, "mlb": 24.0, "wc": 30.0}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ratings (
    sport      TEXT NOT NULL,
    code       TEXT NOT NULL,
    delta      REAL NOT NULL DEFAULT 0,
    games      INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT,
    PRIMARY KEY (sport, code)
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute(_SCHEMA)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clamp(x: float) -> float:
    return max(-DELTA_CAP, min(DELTA_CAP, x))


def get_delta(sport: str, code: str) -> float:
    with _LOCK, _connect() as conn:
        row = conn.execute(
            "SELECT delta FROM ratings WHERE sport = ? AND code = ?",
            (sport, code.upper()),
        ).fetchone()
    return float(row["delta"]) if row else 0.0


def adjust(sport: str, code: str, base_elo: float) -> float:
    """Apply the learned adjustment to a static base rating."""
    return base_elo + get_delta(sport, code)


def _apply_delta(conn: sqlite3.Connection, sport: str, code: str, change: float) -> None:
    row = conn.execute(
        "SELECT delta, games FROM ratings WHERE sport = ? AND code = ?",
        (sport, code.upper()),
    ).fetchone()
    prev = float(row["delta"]) if row else 0.0
    games = (int(row["games"]) if row else 0) + 1
    conn.execute(
        """
        INSERT INTO ratings (sport, code, delta, games, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(sport, code) DO UPDATE SET
            delta = excluded.delta, games = excluded.games, updated_at = excluded.updated_at
        """,
        (sport, code.upper(), _clamp(prev + change), games, _now()),
    )


def record_result(
    sport: str,
    home_code: str,
    away_code: str,
    home_elo: float,
    away_elo: float,
    home_score: int,
    away_score: int,
) -> float:
    """
    Standard Elo update from one final score. `home_elo`/`away_elo` are the
    ratings that were in effect for the game (base + delta at snapshot time).
    Returns the signed rating change applied to the home side.
    """
    if home_score == away_score:
        return 0.0   # ties don't move ratings here
    hfa = _HFA.get(sport, 30.0)
    dr = (home_elo + hfa) - away_elo
    exp_home = 1.0 / (1.0 + 10 ** (-dr / BASE))
    s_home = 1.0 if home_score > away_score else 0.0
    mov_mult = math.log(abs(home_score - away_score) + 1.0)
    change = K * mov_mult * (s_home - exp_home)
    with _LOCK, _connect() as conn:
        _apply_delta(conn, sport, home_code, change)
        _apply_delta(conn, sport, away_code, -change)
    return change


def reconcile() -> int:
    """
    Apply Elo updates for every graded game that carries the data we need and
    hasn't been folded into the ratings yet. Idempotent — safe to call from any
    endpoint that touches the ledger. Returns the number of games applied.
    """
    with _LOCK, _connect() as conn:
        # elo_applied / the code+elo columns are added by the ledger schema.
        try:
            rows = conn.execute(
                """
                SELECT event_id, league, home_code, away_code,
                       home_elo, away_elo, home_score, away_score
                FROM predictions
                WHERE graded = 1 AND elo_applied = 0
                  AND home_code IS NOT NULL AND home_elo IS NOT NULL
                """
            ).fetchall()
        except sqlite3.OperationalError:
            return 0   # columns not present yet (fresh DB before first snapshot)

    applied = 0
    for r in rows:
        record_result(
            r["league"], r["home_code"], r["away_code"],
            r["home_elo"], r["away_elo"], r["home_score"], r["away_score"],
        )
        with _LOCK, _connect() as conn:
            conn.execute(
                "UPDATE predictions SET elo_applied = 1 WHERE event_id = ?",
                (r["event_id"],),
            )
        applied += 1
    return applied


def standings(sport: str) -> list[dict]:
    """Current learned adjustments for a sport, biggest movers first."""
    with _LOCK, _connect() as conn:
        rows = conn.execute(
            "SELECT code, delta, games FROM ratings WHERE sport = ? ORDER BY delta DESC",
            (sport,),
        ).fetchall()
    return [dict(r) for r in rows]


def reset() -> None:
    """Test helper — wipe learned ratings."""
    with _LOCK, _connect() as conn:
        conn.execute("DELETE FROM ratings")
