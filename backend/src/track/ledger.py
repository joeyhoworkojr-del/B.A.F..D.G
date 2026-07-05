"""
Prediction ledger — the platform's verifiable track record.

Every mapped pre-game prediction on the Today slate is snapshotted (model,
sportsbook, and Polymarket crowd probabilities, all at the same moment).
When the game goes final, the snapshot is graded automatically:

  Brier score = (home_prob − home_won)²   — lower is better, 0.25 = coin flip

Because all three signals are captured together, the scorecard is a fair
head-to-head: model vs the book vs the crowd on identical games.

SQLite-backed (stdlib). Path via LEDGER_PATH (default ./ledger.db).
On Fly, attach a volume and set LEDGER_PATH=/data/ledger.db to make the
record durable across deploys.
"""
from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional

_LOCK = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS predictions (
    event_id        TEXT PRIMARY KEY,
    league          TEXT NOT NULL,
    kickoff         TEXT,
    home            TEXT,
    away            TEXT,
    snapshot_at     TEXT,
    model_home_prob REAL,
    model_total     REAL,
    book_home_prob  REAL,
    crowd_home_prob REAL,
    market_spread   REAL,
    market_total    REAL,
    graded          INTEGER DEFAULT 0,
    home_score      INTEGER,
    away_score      INTEGER,
    home_won        INTEGER,
    graded_at       TEXT,
    home_code       TEXT,
    away_code       TEXT,
    home_elo        REAL,
    away_elo        REAL,
    elo_applied     INTEGER DEFAULT 0
);
"""

# Columns added after the original release — backfilled onto existing DBs.
_MIGRATIONS = [
    ("home_code", "TEXT"),
    ("away_code", "TEXT"),
    ("home_elo", "REAL"),
    ("away_elo", "REAL"),
    ("elo_applied", "INTEGER DEFAULT 0"),
]


def _db_path() -> str:
    """
    Resolve the ledger path, guaranteeing it is writable. If the configured
    path's directory can't be created or written (e.g. the Fly volume didn't
    mount), fall back to a local file so the API never 500s over storage.
    """
    path = os.getenv("LEDGER_PATH", "ledger.db")
    parent = os.path.dirname(path)
    try:
        if parent:
            os.makedirs(parent, exist_ok=True)
        # cheap writability probe on the directory
        if not os.access(parent or ".", os.W_OK):
            raise OSError(f"{parent!r} not writable")
        return path
    except OSError:
        return "ledger.db"   # ephemeral fallback — better than a hard failure


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute(_SCHEMA)
    # Backfill columns for DBs created before they existed.
    existing = {r["name"] for r in conn.execute("PRAGMA table_info(predictions)")}
    for col, decl in _MIGRATIONS:
        if col not in existing:
            conn.execute(f"ALTER TABLE predictions ADD COLUMN {col} {decl}")
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record_pregame(
    *,
    event_id: str,
    league: str,
    kickoff: str,
    home: str,
    away: str,
    model_home_prob: float,
    model_total: Optional[float] = None,
    book_home_prob: Optional[float] = None,
    crowd_home_prob: Optional[float] = None,
    market_spread: Optional[float] = None,
    market_total: Optional[float] = None,
    home_code: Optional[str] = None,
    away_code: Optional[str] = None,
    home_elo: Optional[float] = None,
    away_elo: Optional[float] = None,
) -> None:
    """Upsert the latest pre-game snapshot; frozen once the game is graded.

    `home_code`/`away_code` and the snapshot Elos are what the self-correcting
    ratings module reconciles from once the game grades.
    """
    with _LOCK, _connect() as conn:
        conn.execute(
            """
            INSERT INTO predictions (
                event_id, league, kickoff, home, away, snapshot_at,
                model_home_prob, model_total, book_home_prob,
                crowd_home_prob, market_spread, market_total,
                home_code, away_code, home_elo, away_elo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_id) DO UPDATE SET
                snapshot_at     = excluded.snapshot_at,
                model_home_prob = excluded.model_home_prob,
                model_total     = excluded.model_total,
                book_home_prob  = excluded.book_home_prob,
                crowd_home_prob = excluded.crowd_home_prob,
                market_spread   = excluded.market_spread,
                market_total    = excluded.market_total,
                home_code       = excluded.home_code,
                away_code       = excluded.away_code,
                home_elo        = excluded.home_elo,
                away_elo        = excluded.away_elo
            WHERE predictions.graded = 0
            """,
            (event_id, league, kickoff, home, away, _now(),
             model_home_prob, model_total, book_home_prob,
             crowd_home_prob, market_spread, market_total,
             home_code, away_code, home_elo, away_elo),
        )


def grade(event_id: str, home_score: int, away_score: int) -> bool:
    """Grade a stored snapshot against the final score. Ties are ignored."""
    if home_score == away_score:
        return False
    with _LOCK, _connect() as conn:
        cur = conn.execute(
            """
            UPDATE predictions
            SET graded = 1, home_score = ?, away_score = ?,
                home_won = ?, graded_at = ?
            WHERE event_id = ? AND graded = 0
            """,
            (home_score, away_score,
             1 if home_score > away_score else 0, _now(), event_id),
        )
        return cur.rowcount > 0


def grade_board(league: str, games) -> int:
    """Settle every finished game on a scoreboard against pending snapshots.

    Called from every endpoint that touches a live board, so the track record
    keeps grading itself no matter which page users are on. Returns the
    number of picks newly graded.
    """
    graded = 0
    for g in games:
        if g.state == "post" and g.home_score is not None and g.away_score is not None:
            if grade(f"{league}:{g.event_id}", g.home_score, g.away_score):
                graded += 1
    return graded


def _brier(rows: list[sqlite3.Row], col: str) -> Optional[dict]:
    vals = [(r[col], r["home_won"]) for r in rows if r[col] is not None]
    if not vals:
        return None
    briers = [(p - won) ** 2 for p, won in vals]
    hits = sum(1 for p, won in vals if (p >= 0.5) == bool(won))
    return {
        "n": len(vals),
        "brier": sum(briers) / len(briers),
        "winner_hit_rate": hits / len(vals),
    }


def accuracy_summary() -> dict:
    """Head-to-head scorecard: model vs book vs crowd on identical games."""
    with _LOCK, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM predictions WHERE graded = 1",
        ).fetchall()
        pending = conn.execute(
            "SELECT COUNT(*) AS n FROM predictions WHERE graded = 0",
        ).fetchone()["n"]

    leagues: dict[str, list[sqlite3.Row]] = {}
    for r in rows:
        leagues.setdefault(r["league"], []).append(r)

    def summarize(subset: list[sqlite3.Row]) -> dict:
        return {
            "games_graded": len(subset),
            "model": _brier(subset, "model_home_prob"),
            "book": _brier(subset, "book_home_prob"),
            "crowd": _brier(subset, "crowd_home_prob"),
        }

    return {
        "overall": summarize(rows),
        "by_league": {lg: summarize(rs) for lg, rs in sorted(leagues.items())},
        "pending": pending,
        "note": "Brier score: lower is better; 0.25 = coin flip. All signals snapshotted pre-game at the same moment.",
    }


def performance() -> dict:
    """
    Honest trading-desk stats for the graded ledger, treating the model's
    moneyline pick as a 1-unit bet settled at the book's no-vig fair odds:
      win  → +(1/p_book − 1) units,  loss → −1 unit.
    """
    with _LOCK, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM predictions WHERE graded = 1 ORDER BY graded_at ASC",
        ).fetchall()

    series: list[float] = []
    cum = 0.0
    staked = 0
    wins = 0
    edge_sum = 0.0
    edge_n = 0

    for r in rows:
        model_p = r["model_home_prob"]
        if model_p is None:
            continue
        pick_home = model_p >= 0.5
        pick_won = bool(r["home_won"]) == pick_home
        wins += 1 if pick_won else 0

        book_home = r["book_home_prob"]
        if book_home is not None:
            pick_book_p = book_home if pick_home else 1 - book_home
            pick_model_p = model_p if pick_home else 1 - model_p
            edge_sum += (pick_model_p - pick_book_p) * 100
            edge_n += 1
            payout = (1.0 / max(pick_book_p, 1e-6)) - 1.0
            cum += payout if pick_won else -1.0
            staked += 1
            series.append(round(cum, 3))

    return {
        "total_picks": len(rows),
        "win_rate": (wins / len(rows)) if rows else None,
        "avg_edge_pp": (edge_sum / edge_n) if edge_n else None,
        "profit_units": round(cum, 2) if staked else None,
        "roi_pct": round(100 * cum / staked, 1) if staked else None,
        "series": series,
    }


def recent_graded(limit: int = 25) -> list[dict]:
    with _LOCK, _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM predictions WHERE graded = 1
            ORDER BY graded_at DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def reset() -> None:
    """Test helper — wipe the ledger."""
    with _LOCK, _connect() as conn:
        conn.execute("DELETE FROM predictions")
