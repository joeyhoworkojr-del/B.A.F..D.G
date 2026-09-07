"""
Prediction ledger — the platform's verifiable track record.

Every mapped pre-game prediction on the Today slate is snapshotted (model,
sportsbook, and Polymarket crowd probabilities, all at the same moment).
When the game goes final, the snapshot is graded automatically:

  Brier score = (home_prob − home_won)²   — lower is better, 0.25 = coin flip

Because all three signals are captured together, the scorecard is a fair
head-to-head: model vs the book vs the crowd on identical games.

Storage is SQLite by default and Postgres when DATABASE_URL is set — see
src/track/db.py. This matters: on Fly the container disk is replaced on every
deploy, so a SQLite ledger silently restarts each release. Pointing
DATABASE_URL at a managed Postgres is what makes the record durable.
"""
from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from typing import Any, Optional

from . import db

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
    elo_applied     INTEGER DEFAULT 0,
    consensus_home_prob REAL,
    model_version   TEXT,
    book_source     TEXT,
    closing_spread  REAL,
    closing_total   REAL,
    closing_home_prob REAL
);
"""

# Columns added after the original release — backfilled onto existing DBs.
_MIGRATIONS = [
    ("home_code", "TEXT"),
    ("away_code", "TEXT"),
    ("home_elo", "REAL"),
    ("away_elo", "REAL"),
    ("elo_applied", "INTEGER DEFAULT 0"),
    # Market-anchored "consensus" prob — what the product actually recommends.
    ("consensus_home_prob", "REAL"),
    # Integrity: which model made the call, which book priced it, and the
    # line as it stood at kickoff (frozen when the game grades).
    ("model_version", "TEXT"),
    ("book_source", "TEXT"),
    ("closing_spread", "REAL"),
    ("closing_total", "REAL"),
    ("closing_home_prob", "REAL"),
]


def _db_path() -> str:
    """Kept for callers that report where a SQLite ledger lives."""
    return db.sqlite_path()


def _connect():
    """A ready connection on whichever backend is configured."""
    return db.connect(_SCHEMA, _MIGRATIONS, "predictions")


def storage_backend() -> str:
    """"sqlite" or "postgres" — surfaced so the record can state its durability."""
    return db.backend_name()


def storage_durable() -> bool:
    """
    Whether the record survives a deploy.

    A SQLite ledger on a container's own disk does not: the disk is replaced
    each release. The UI must not present a graded record as permanent when the
    storage behind it is not.
    """
    return db.is_postgres() or bool(os.getenv("LEDGER_DURABLE"))


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
    consensus_home_prob: Optional[float] = None,
    model_version: Optional[str] = None,
    book_source: Optional[str] = None,
) -> None:
    """Upsert the latest pre-game snapshot; frozen once the game is graded.

    `home_code`/`away_code` and the snapshot Elos are what the self-correcting
    ratings module reconciles from once the game grades. `consensus_home_prob`
    is the market-anchored recommendation (what P/L is settled on); the raw
    `model_home_prob` is kept for the honest model-vs-book Brier comparison.

    Integrity: a row is only refreshed while it is ungraded AND was produced by
    the same `model_version`. A newer model therefore cannot silently rewrite a
    prediction an older model already made and is being judged on.
    """
    with _LOCK, _connect() as conn:
        conn.execute(
            """
            INSERT INTO predictions (
                event_id, league, kickoff, home, away, snapshot_at,
                model_home_prob, model_total, book_home_prob,
                crowd_home_prob, market_spread, market_total,
                home_code, away_code, home_elo, away_elo, consensus_home_prob,
                model_version, book_source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                away_elo        = excluded.away_elo,
                consensus_home_prob = excluded.consensus_home_prob,
                book_source     = excluded.book_source
            WHERE predictions.graded = 0
              AND (predictions.model_version IS NULL
                   OR predictions.model_version = excluded.model_version)
            """,
            (event_id, league, kickoff, home, away, _now(),
             model_home_prob, model_total, book_home_prob,
             crowd_home_prob, market_spread, market_total,
             home_code, away_code, home_elo, away_elo, consensus_home_prob,
             model_version, book_source),
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
                home_won = ?, graded_at = ?,
                -- Freeze the line as it last stood pre-kickoff: that is the
                -- closing number the prediction is judged against.
                closing_spread    = COALESCE(closing_spread, market_spread),
                closing_total     = COALESCE(closing_total, market_total),
                closing_home_prob = COALESCE(closing_home_prob, book_home_prob)
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


def _brier(rows: list[Any], col: str) -> Optional[dict]:
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

    leagues: dict[str, list[Any]] = {}
    for r in rows:
        leagues.setdefault(r["league"], []).append(r)

    def summarize(subset: list[Any]) -> dict:
        return {
            "games_graded": len(subset),
            "model": _brier(subset, "model_home_prob"),
            "book": _brier(subset, "book_home_prob"),
            "crowd": _brier(subset, "crowd_home_prob"),
        }

    versions = sorted({r["model_version"] for r in rows if r["model_version"]})

    return {
        "overall": summarize(rows),
        "by_league": {lg: summarize(rs) for lg, rs in sorted(leagues.items())},
        "pending": pending,
        "note": "Brier score: lower is better; 0.25 = coin flip. All signals snapshotted pre-game at the same moment.",
        # Everything in this ledger is a pre-game snapshot. In-game updates are
        # shown live but never stored or graded, so they cannot flatter the
        # record — and the UI must not present the two as one number.
        "scope": "pregame",
        "live_record_available": False,
        "live_note": (
            "Live in-game win probabilities are recalculated from the score and "
            "clock while a game is running. They are not snapshotted or graded, "
            "so they are not part of the record above."
        ),
        "model_versions": versions,
        # Storage honesty: a SQLite ledger lives on the container's own disk,
        # which is replaced on every deploy. Saying so is the difference
        # between a verifiable record and one that quietly resets.
        "storage_backend": storage_backend(),
        "storage_durable": storage_durable(),
    }


def performance() -> dict:
    """
    Honest trading-desk stats for the graded ledger. The recommended pick is
    settled as a 1-unit bet at the book's no-vig fair odds:
      win  → +(1/p_book − 1) units,  loss → −1 unit.

    The pick follows the market-anchored *consensus* probability (what the
    product actually advises) when present, falling back to the raw model for
    older rows. `avg_edge_pp` still measures the raw model's divergence from the
    book on the bet side, so we can see what the model adds.
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
        raw_p = r["model_home_prob"]
        if raw_p is None:
            continue
        cons_p = r["consensus_home_prob"]
        pick_p = cons_p if cons_p is not None else raw_p
        pick_home = pick_p >= 0.5
        pick_won = bool(r["home_won"]) == pick_home
        wins += 1 if pick_won else 0

        book_home = r["book_home_prob"]
        if book_home is not None:
            pick_book_p = book_home if pick_home else 1 - book_home
            pick_raw_p = raw_p if pick_home else 1 - raw_p
            edge_sum += (pick_raw_p - pick_book_p) * 100
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


def get_snapshot(event_id: str) -> Optional[dict]:
    """The frozen prediction for one event, or None if nothing is stored yet.

    This is what the game page shows as "what the model said beforehand" — it
    never recomputes, so a graded call can be compared against the closing line
    exactly as it was made.
    """
    with _LOCK, _connect() as conn:
        row = conn.execute(
            "SELECT * FROM predictions WHERE event_id = ?", (event_id,),
        ).fetchone()
    return dict(row) if row else None


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
