"""
Live win-probability history, per game.

A probability timeline is only interesting if it survives a page reload, so it
is kept here rather than accumulated in the browser. Each reading is appended
as the live model produces one, and a game's series can be read back for a
chart or handed to Edge AI when someone asks why a number moved.

Deliberately in memory and bounded. This is a chart of a game in progress, not
a record of anything the product claims accountability for — the graded record
lives in the ledger and is durable. Losing a timeline to a restart costs a
chart; nothing that is graded or published depends on it. Keeping it out of
durable storage also keeps a high-frequency write off the same backend the
ledger relies on.

Readings are deduplicated: the live board is polled far faster than the
probability actually moves, and appending an identical point every few seconds
would produce a flat line made of thousands of samples.
"""
from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional

# Enough for a full game at a reading every few seconds of game action, with
# room for overtime.
MAX_POINTS_PER_GAME = 400

# How many games to keep timelines for at once. A busy college Saturday is
# around 60 games; this holds a weekend without growing without bound.
MAX_GAMES = 200

# A reading is only stored when the probability has actually moved by this
# much, or the score changed, or enough time has passed.
MIN_PROBABILITY_MOVE = 0.004
MIN_SECONDS_BETWEEN = 20.0

_LOCK = threading.Lock()


@dataclass
class WinPoint:
    """One reading of the live model."""
    at: str                 # ISO timestamp
    home_win: float
    home_score: int
    away_score: int
    period: Optional[int]
    clock: str
    possession: str
    note: str = ""
    scored: bool = False    # this reading is the first after the score changed


_series: dict[str, list[WinPoint]] = {}
_last_write: dict[str, float] = {}


def _key(league: str, event_id: str) -> str:
    return f"{league.lower()}:{event_id}"


def record(
    *,
    league: str,
    event_id: str,
    home_win: float,
    home_score: int,
    away_score: int,
    period: Optional[int] = None,
    clock: str = "",
    possession: str = "",
    note: str = "",
) -> None:
    """
    Append a reading, unless it says nothing the last one did not.

    Never raises: a timeline is a nice-to-have on a page whose job is to show a
    live game, and a bookkeeping failure must not take that page down.
    """
    try:
        key = _key(league, event_id)
        now = time.monotonic()
        with _LOCK:
            points = _series.get(key)
            if points is None:
                if len(_series) >= MAX_GAMES:
                    _evict_oldest_locked()
                points = _series[key] = []

            scored = False
            if points:
                last = points[-1]
                scored = (last.home_score, last.away_score) != (home_score, away_score)
                moved = abs(last.home_win - home_win) >= MIN_PROBABILITY_MOVE
                waited = (now - _last_write.get(key, 0.0)) >= MIN_SECONDS_BETWEEN
                if not (scored or moved or waited):
                    return

            points.append(WinPoint(
                at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                home_win=round(float(home_win), 4),
                home_score=int(home_score), away_score=int(away_score),
                period=period, clock=clock, possession=possession,
                note=note, scored=scored,
            ))
            _last_write[key] = now
            if len(points) > MAX_POINTS_PER_GAME:
                # Drop from the middle rather than the start: the opening
                # reading is the pre-game anchor the chart is measured against.
                del points[1:len(points) - MAX_POINTS_PER_GAME + 1]
    except Exception:                                    # pragma: no cover
        return


def _evict_oldest_locked() -> None:
    oldest = min(_last_write, key=_last_write.get, default=None)
    if oldest is None:
        oldest = next(iter(_series), None)
    if oldest is not None:
        _series.pop(oldest, None)
        _last_write.pop(oldest, None)


def series(league: str, event_id: str) -> list[dict]:
    """Every stored reading for one game, oldest first."""
    with _LOCK:
        return [asdict(p) for p in _series.get(_key(league, event_id), [])]


def swing(league: str, event_id: str) -> Optional[dict]:
    """
    How far the number has travelled since the first reading.

    None when there is nothing yet — an empty timeline is not a zero swing.
    """
    points = series(league, event_id)
    if len(points) < 2:
        return None
    first, last = points[0], points[-1]
    return {
        "opened_at": first["at"],
        "opening_home_win": first["home_win"],
        "current_home_win": last["home_win"],
        "change": round(last["home_win"] - first["home_win"], 4),
        "readings": len(points),
        "high": max(p["home_win"] for p in points),
        "low": min(p["home_win"] for p in points),
    }


def stats() -> dict:
    """Size of the store, for the staff page."""
    with _LOCK:
        return {
            "games_tracked": len(_series),
            "points_stored": sum(len(v) for v in _series.values()),
            "max_games": MAX_GAMES,
        }


def reset() -> None:
    with _LOCK:
        _series.clear()
        _last_write.clear()
