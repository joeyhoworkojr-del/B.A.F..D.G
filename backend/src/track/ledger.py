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

import functools
import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Optional

from . import db
from .store import build_store, config_report

log = logging.getLogger(__name__)

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
    closing_home_prob REAL,
    opening_spread  REAL,
    opening_total   REAL,
    opening_home_prob REAL,
    pick_spread_side TEXT,
    pick_total_side  TEXT
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
    # The line we actually recommended at, and the side we took. Frozen on the
    # first snapshot; `market_*` keeps moving. Without these, closing line
    # value cannot be computed at all.
    ("opening_spread", "REAL"),
    ("opening_total", "REAL"),
    ("opening_home_prob", "REAL"),
    ("pick_spread_side", "TEXT"),
    ("pick_total_side", "TEXT"),
    ("closing_home_prob", "REAL"),
]


def _db_path() -> str:
    """Kept for callers that report where a SQLite ledger lives."""
    return db.sqlite_path()


def _connect():
    """A ready connection on whichever SQL backend is configured."""
    return db.connect(_SCHEMA, _MIGRATIONS, "predictions")


_store = None


def _safe(default):
    """
    Storage failures must not 500 a page.

    The ledger is one feature; a live scoreboard, the game pages and the props
    all call into it incidentally. If storage is unreachable those pages should
    still render, with the record simply empty, rather than the whole site
    returning an error.
    """
    def decorate(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                log.error("ledger %s failed: %s", fn.__name__, exc)
                return default() if callable(default) else default
        return wrapper
    return decorate


def _get_store():
    """
    The row store, chosen from the environment on first use.

    Resolved lazily rather than at import so tests (and a deploy that sets its
    variables late) can change backend without reimporting the module.
    """
    global _store
    if _store is None:
        _store = build_store(_SCHEMA, _MIGRATIONS, "predictions")
    return _store


def reset_store() -> None:
    """Test seam: forget the resolved backend so the next call re-reads the env."""
    global _store
    _store = None


@_safe("unavailable")
def storage_backend() -> str:
    """"sqlite", "postgres" or "redis" — so the record can state its durability."""
    return _get_store().backend


@_safe(False)
def storage_durable() -> bool:
    """
    Whether the record survives a deploy.

    A SQLite ledger on a container's own disk does not: the disk is replaced
    each release. The UI must not present a graded record as permanent when the
    storage behind it is not.

    Unreadable storage answers False. Guessing that a record is durable when
    the store cannot even be opened is the one wrong answer here.
    """
    return _get_store().durable or bool(os.getenv("LEDGER_DURABLE"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@_safe(None)
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
    pick_spread_side: Optional[str] = None,
    pick_total_side: Optional[str] = None,
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
    with _LOCK:
        _get_store().upsert_pregame({
            "event_id": event_id, "league": league, "kickoff": kickoff,
            "home": home, "away": away, "snapshot_at": _now(),
            "model_home_prob": model_home_prob, "model_total": model_total,
            "book_home_prob": book_home_prob, "crowd_home_prob": crowd_home_prob,
            "market_spread": market_spread, "market_total": market_total,
            "home_code": home_code, "away_code": away_code,
            "home_elo": home_elo, "away_elo": away_elo,
            "consensus_home_prob": consensus_home_prob,
            "model_version": model_version, "book_source": book_source,
            # Sent on every snapshot; the store refuses to refresh them, so
            # what sticks is the line and the side from the first one. That is
            # the recommendation closing line value is measured against.
            "opening_spread": market_spread,
            "opening_total": market_total,
            "opening_home_prob": book_home_prob,
            "pick_spread_side": pick_spread_side,
            "pick_total_side": pick_total_side,
        })


@_safe(False)
def grade(event_id: str, home_score: int, away_score: int) -> bool:
    """Grade a stored snapshot against the final score. Ties are ignored."""
    if home_score == away_score:
        return False
    with _LOCK:
        return _get_store().mark_graded(
            event_id, home_score, away_score,
            1 if home_score > away_score else 0, _now(),
        )


def grade_board(league: str, games) -> int:
    """Settle every finished game on a scoreboard against pending snapshots.

    Called from every endpoint that touches a live board, so the track record
    keeps grading itself no matter which page users are on. Returns the
    number of picks newly graded.
    """
    graded = 0
    for g in games:
        if g.state == "post" and g.home_score is not None and g.away_score is not None:
            game_id = f"{league}:{g.event_id}"
            if grade(game_id, g.home_score, g.away_score):
                graded += 1
            # User predictions settle on the same signal as the model's own.
            # Imported here rather than at module scope: picks depend on the
            # document store, which depends on this module.
            try:
                from src.picks.service import grade_game
                grade_game(game_id, g.home_score, g.away_score)
            except Exception as exc:      # never let grading break a page
                log.error("user pick grading failed for %s: %s", game_id, exc)
    return graded


def _brier(rows: list[Any], col: str) -> Optional[dict]:
    # A stored row is whatever the build that wrote it wrote. Rows predating a
    # column simply do not have it, so the column is read with .get() and a row
    # that cannot be scored is skipped rather than subscripted — the difference
    # between one old row and the whole track record failing to load.
    vals = [
        (r.get(col), r.get("home_won"))
        for r in rows
        if r.get(col) is not None and r.get("home_won") is not None
    ]
    if not vals:
        return None
    briers = [(p - won) ** 2 for p, won in vals]
    hits = sum(1 for p, won in vals if (p >= 0.5) == bool(won))
    return {
        "n": len(vals),
        "brier": sum(briers) / len(briers),
        "winner_hit_rate": hits / len(vals),
    }


_EMPTY_SUMMARY_BASE = {
    "games_graded": 0, "model": None, "book": None, "crowd": None,
}


def _empty_summary() -> dict:
    """The shape the page expects when the ledger cannot be read at all."""
    return {
        "overall": dict(_EMPTY_SUMMARY_BASE),
        "by_league": {},
        "pending": 0,
        "note": "",
        "scope": "pregame",
        "live_record_available": False,
        "live_note": "",
        "model_versions": [],
        "storage_backend": storage_backend(),
        "storage_durable": storage_durable(),
        # A fallback that can itself raise is not a fallback, and this one runs
        # precisely when something is already broken.
        "storage_config": _safe(dict)(config_report)(),
        # Said out loud rather than shown as a genuine 0–0 record: an empty
        # scorecard and an unreadable one look identical otherwise, and only
        # one of them is a claim about how the model has done.
        "unavailable": True,
    }


@_safe(_empty_summary)
def accuracy_summary() -> dict:
    """Head-to-head scorecard: model vs book vs crowd on identical games."""
    with _LOCK:
        store = _get_store()
        rows = store.rows(graded=True)
        pending = store.count(graded=False)

    leagues: dict[str, list[Any]] = {}
    for r in rows:
        leagues.setdefault(r.get("league") or "unknown", []).append(r)

    def summarize(subset: list[Any]) -> dict:
        return {
            "games_graded": len(subset),
            "model": _brier(subset, "model_home_prob"),
            "book": _brier(subset, "book_home_prob"),
            "crowd": _brier(subset, "crowd_home_prob"),
        }

    versions = sorted({r.get("model_version") for r in rows if r.get("model_version")})

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
        # Names and scheme validity only — never a secret's value.
        "storage_config": config_report(),
    }


@_safe(dict)
def openings_for(event_ids: list[str]) -> dict[str, dict]:
    """
    The frozen opening line and side for the games asked about, in one read.

    Scoped to the ids the caller needs rather than scanning the whole ledger:
    the board wants a hundred games, and the ledger holds every game of the
    season and keeps growing. Reading all of it twice a minute to answer a
    question about today would get slower every week.
    """
    ids = [str(i) for i in event_ids if i]
    if not ids:
        return {}
    with _LOCK:
        found = _get_store().get_many(ids)
    return {
        key: {
            "opening_spread": r.get("opening_spread"),
            "opening_total": r.get("opening_total"),
            "opening_home_prob": r.get("opening_home_prob"),
            "pick_spread_side": r.get("pick_spread_side"),
            "pick_total_side": r.get("pick_total_side"),
            "snapshot_at": r.get("snapshot_at"),
        }
        for key, r in found.items()
    }


# ─── Closing line value, and the spread / total records ──────────────────────

def _num(v) -> Optional[float]:
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


def clv_points(row: dict) -> Optional[float]:
    """
    How many points better than the close the recommended spread was.

    Signed from the point of view of the side we took. Backing the home team
    at -3.5 into a -4.5 close is a point in hand, so +1.0; backing the away
    team at +3.5 into that same close is a point given away, so -1.0.

    This is worth tracking separately from win and loss because it is the one
    number that says whether the model is finding real value rather than
    getting lucky: a bet can lose and still have beaten the close, and a model
    that consistently beats the close is doing something.

    Returns None when there is nothing to compare — no opening line on file, no
    close, or no side taken. None is not zero, and averaging it in as zero
    would quietly dilute the figure towards "no edge".
    """
    opening = _num(row.get("opening_spread"))
    closing = _num(row.get("closing_spread"))
    side = (row.get("pick_spread_side") or "").lower()
    if opening is None or closing is None or side not in ("home", "away"):
        return None
    delta = opening - closing
    return round(delta if side == "home" else -delta, 2)


def _ats_result(row: dict) -> Optional[str]:
    """
    Did the recommended spread side cover the line we took? "push" is neither.

    Graded against `opening_spread` — the line the recommendation was made at —
    not against the close. Grading against a line we never had would flatter or
    punish the record for a move that happened afterwards.
    """
    line = _num(row.get("opening_spread"))
    side = (row.get("pick_spread_side") or "").lower()
    hs, as_ = _num(row.get("home_score")), _num(row.get("away_score"))
    if line is None or side not in ("home", "away") or hs is None or as_ is None:
        return None
    # A home line of -3.5 means the home team must win by more than 3.5.
    margin = hs - as_
    edge = margin + line          # >0 home covers, <0 away covers, ==0 push
    if edge == 0:
        return "push"
    home_covered = edge > 0
    return "win" if home_covered == (side == "home") else "loss"


def _total_result(row: dict) -> Optional[str]:
    """Did the recommended over/under hit, against the line we took?"""
    line = _num(row.get("opening_total"))
    side = (row.get("pick_total_side") or "").lower()
    hs, as_ = _num(row.get("home_score")), _num(row.get("away_score"))
    if line is None or side not in ("over", "under") or hs is None or as_ is None:
        return None
    combined = hs + as_
    if combined == line:
        return "push"
    went_over = combined > line
    return "win" if went_over == (side == "over") else "loss"


def _record_of(results: list[str]) -> dict:
    wins = sum(1 for r in results if r == "win")
    losses = sum(1 for r in results if r == "loss")
    pushes = sum(1 for r in results if r == "push")
    decided = wins + losses
    return {
        "wins": wins, "losses": losses, "pushes": pushes,
        # A push is not a loss, so it is out of the denominator rather than
        # dragging the rate down.
        "win_rate": (wins / decided) if decided else None,
        "graded": len(results),
    }


_EMPTY_RECORD = {"wins": 0, "losses": 0, "pushes": 0, "win_rate": None, "graded": 0}

_EMPTY_PERFORMANCE = {
    "total_picks": 0, "wins": 0, "losses": 0, "win_rate": None,
    "priced_picks": 0, "avg_edge_pp": None,
    "profit_units": None, "roi_pct": None, "series": [],
    "ats": dict(_EMPTY_RECORD), "totals": dict(_EMPTY_RECORD),
    "avg_clv_points": None, "clv_tracked": 0, "clv_beat_close": 0,
}


@_safe(lambda: dict(_EMPTY_PERFORMANCE))
def performance() -> dict:
    """
    Honest trading-desk stats for the graded ledger. The recommended pick is
    settled as a 1-unit bet at the book's no-vig fair odds:
      win  → +(1/p_book − 1) units,  loss → −1 unit.

    The pick follows the market-anchored *consensus* probability (what the
    product actually advises) when present, falling back to the raw model for
    older rows. `avg_edge_pp` still measures the raw model's divergence from the
    book on the bet side, so we can see what the model adds.

    Every field is read with `.get`. A durable store accumulates rows across
    schema changes, and one row written before a column existed used to raise
    KeyError here — which took the whole Results page down, because this was
    the only ledger call the route did not guard.
    """
    with _LOCK:
        rows = _get_store().rows(graded=True)
    # Oldest first, so the P/L series reads left to right.
    rows.sort(key=lambda r: (r.get("graded_at") or ""))

    series: list[float] = []
    cum = 0.0
    staked = 0
    wins = 0
    edge_sum = 0.0
    edge_n = 0

    usable = 0
    for r in rows:
        raw_p = r.get("model_home_prob")
        won = r.get("home_won")
        if raw_p is None or won is None:
            # Not enough of the row survived to settle it. Skipping keeps one
            # bad row from distorting the record; counting it would.
            continue
        usable += 1
        cons_p = r.get("consensus_home_prob")
        pick_p = cons_p if cons_p is not None else raw_p
        pick_home = pick_p >= 0.5
        pick_won = bool(won) == pick_home
        wins += 1 if pick_won else 0

        book_home = r.get("book_home_prob")
        if book_home is not None:
            pick_book_p = book_home if pick_home else 1 - book_home
            pick_raw_p = raw_p if pick_home else 1 - raw_p
            edge_sum += (pick_raw_p - pick_book_p) * 100
            edge_n += 1
            payout = (1.0 / max(pick_book_p, 1e-6)) - 1.0
            cum += payout if pick_won else -1.0
            staked += 1
            series.append(round(cum, 3))

    # ── The spread and total records, and closing line value ──
    # Separate from the moneyline record above, because they are separate bets
    # graded against separate lines, and a single blended "record" hides which
    # of them the model is actually good at.
    ats = _record_of([r for r in (_ats_result(x) for x in rows) if r])
    totals = _record_of([r for r in (_total_result(x) for x in rows) if r])
    clvs = [c for c in (clv_points(x) for x in rows) if c is not None]

    return {
        # Rows that could be settled, not rows on file — a win rate divided by
        # a denominator that includes unsettleable rows is understated.
        "total_picks": usable,
        "ats": ats,
        "totals": totals,
        # Averaged over the rows that have both an opening and a closing line,
        # which is said rather than implied: a thin denominator is a weaker
        # claim than a fat one and the page should be able to show which.
        "avg_clv_points": round(sum(clvs) / len(clvs), 2) if clvs else None,
        "clv_tracked": len(clvs),
        "clv_beat_close": sum(1 for c in clvs if c > 0),
        # Stated, not inferred. The page used to rebuild the split by
        # multiplying a rounded rate back out by the total, which is a derived
        # number presented as a record.
        "wins": wins,
        "losses": usable - wins,
        "win_rate": (wins / usable) if usable else None,
        # How many of those could be priced. ROI needs a book price on the
        # side we took; without one there is no stake and no return, and a
        # blank ROI beside a healthy win rate needs to say why rather than
        # leaving an unexplained dash.
        "priced_picks": staked,
        "avg_edge_pp": (edge_sum / edge_n) if edge_n else None,
        "profit_units": round(cum, 2) if staked else None,
        "roi_pct": round(100 * cum / staked, 1) if staked else None,
        "series": series,
    }


@_safe(None)
def get_snapshot(event_id: str) -> Optional[dict]:
    """The frozen prediction for one event, or None if nothing is stored yet.

    This is what the game page shows as "what the model said beforehand" — it
    never recomputes, so a graded call can be compared against the closing line
    exactly as it was made.
    """
    with _LOCK:
        return _get_store().get(event_id)


@_safe(list)
def recent_graded(limit: int = 25) -> list[dict]:
    with _LOCK:
        rows = _get_store().rows(graded=True)
    rows.sort(key=lambda r: (r.get("graded_at") or ""), reverse=True)
    return rows[:limit]


def reset() -> None:
    """Test helper — wipe the ledger."""
    with _LOCK:
        _get_store().clear()
