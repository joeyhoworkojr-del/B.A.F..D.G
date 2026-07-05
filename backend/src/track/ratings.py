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
K = 20.0            # settled base update step (once a team has enough games)
DELTA_CAP = 150.0   # cap on cumulative adjustment per team (Elo points)

# Confidence-weighted learning rate: a brand-new team's rating should move fast
# and then settle as evidence accumulates (a cheap stand-in for a Bayesian
# rating with shrinking variance). K starts at K*(1+PROV_BOOST) and decays
# linearly to K over the first PROV_GAMES graded games.
PROV_GAMES = 10
PROV_BOOST = 1.0

# Regression to the mean: each time a team plays, its accumulated form is pulled
# a little back toward its static prior (delta → 0). This down-weights stale
# results so recent form dominates and no rating drifts permanently.
REGRESS = 0.99


def _k_factor(games: int) -> float:
    """Higher learning rate while a team has few graded games, settling to K."""
    if games >= PROV_GAMES:
        return K
    return K * (1.0 + PROV_BOOST * (PROV_GAMES - games) / PROV_GAMES)

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


def _update_team(conn: sqlite3.Connection, sport: str, code: str, signed_base: float) -> float:
    """
    Fold one result into a team's rating delta with a confidence-weighted step
    and regression to the mean. `signed_base` is the outcome term
    log(|margin|+1)·(actual − expected), positive if the team over-performed.
    Returns the outcome-driven change applied (before regression).
    """
    row = conn.execute(
        "SELECT delta, games FROM ratings WHERE sport = ? AND code = ?",
        (sport, code.upper()),
    ).fetchone()
    prev = float(row["delta"]) if row else 0.0
    games = int(row["games"]) if row else 0

    change = _k_factor(games) * signed_base
    new_delta = _clamp(prev * REGRESS + change)   # regress old form, then update
    conn.execute(
        """
        INSERT INTO ratings (sport, code, delta, games, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(sport, code) DO UPDATE SET
            delta = excluded.delta, games = excluded.games, updated_at = excluded.updated_at
        """,
        (sport, code.upper(), new_delta, games + 1, _now()),
    )
    return change


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
    Elo update from one final score. `home_elo`/`away_elo` are the ratings that
    were in effect for the game (base + delta at snapshot time). Each team
    learns at its own confidence-weighted rate and its prior form is regressed
    slightly toward baseline. Returns the outcome change applied to the home
    side (negative if the home side lost ground).
    """
    if home_score == away_score:
        return 0.0   # ties don't move ratings here
    hfa = _HFA.get(sport, 30.0)
    dr = (home_elo + hfa) - away_elo
    exp_home = 1.0 / (1.0 + 10 ** (-dr / BASE))
    s_home = 1.0 if home_score > away_score else 0.0
    signed_base = math.log(abs(home_score - away_score) + 1.0) * (s_home - exp_home)
    with _LOCK, _connect() as conn:
        home_change = _update_team(conn, sport, home_code, signed_base)
        _update_team(conn, sport, away_code, -signed_base)
    return home_change


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
