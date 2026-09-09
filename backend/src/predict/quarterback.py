"""
Quarterback change as a points adjustment.

The single largest roster factor in football. A team's rating already reflects
whoever has been playing quarterback for it, so this deliberately does **not**
add a quarterback's value on top — that would count the same player twice, and
would shift every game rather than the ones that have actually changed.

What it measures is a *change*: the delta between the quarterback the depth
chart says is starting and the one whose play the rating was earned with. When
the usual starter is playing — most games, most weeks — the adjustment is
exactly zero and the model behaves as before. It speaks up only when a team is
starting someone else, which is the case the market moves several points on and
a ratings model would otherwise miss entirely.

Ratings are EPA per dropback, shrunk toward the league mean by attempts. Raw
EPA per attempt over a handful of throws is meaningless — an unshrunk table has
a third-string quarterback leading the league on thirty-five attempts — so a
rating only escapes the mean in proportion to how much evidence sits behind it.
"""
from __future__ import annotations

import csv
import io
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from src.ingest.nflverse import (
    PLAYER_WEEK, SEASON_LOOKBACK, _download_csv, stream_csv_rows,
)

log = logging.getLogger(__name__)

DEPTH_CHART = "depth_charts/depth_charts_{season}.csv"

# Attempts of league-average play blended into every quarterback's record.
# Calibrated on 2025: at 350 the ordering is sane (the season's best starters
# at the top, its worst at the bottom) and the spread is about ±5 points rather
# than the ±27 an unshrunk rating produces.
SHRINK_ATTEMPTS = 350.0

# Dropbacks in a game. EPA is already in points, so this converts a per-attempt
# rating into points of margin.
DROPBACKS_PER_GAME = 34.0

# A quarterback change cannot move a game by more than this, whatever the
# arithmetic says. Books move roughly 3-7 points on a starting quarterback
# ruled out; anything past this is a small sample talking.
MAX_SWING_POINTS = 7.0

# Below this an "expected starter" is not established enough to say anyone has
# replaced him, so no change is claimed.
MIN_STARTER_ATTEMPTS = 50.0

TTL_SECONDS = 6 * 3600.0


@dataclass(frozen=True)
class QbRating:
    """One quarterback's value, in points of margin against an average starter."""
    name: str
    team: str
    attempts: float
    points: float


@dataclass(frozen=True)
class QbChange:
    """A team starting someone other than the quarterback its rating reflects."""
    team: str
    starter: str
    expected: str
    points: float          # signed: negative is a downgrade for this team

    @property
    def detail(self) -> str:
        direction = "downgrade" if self.points < 0 else "upgrade"
        return (
            f"{self.starter} starts in place of {self.expected} — "
            f"a {abs(self.points):.1f}-point {direction} on recent play."
        )


_cache: dict[str, tuple[float, object]] = {}


def _fresh(key: str):
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < TTL_SECONDS:
        return hit[1]
    return None


def _seasons() -> list[int]:
    year = datetime.now(timezone.utc).year
    return [year - i for i in range(SEASON_LOOKBACK)]


def _norm(name: str) -> str:
    """nflverse writes 'D.Maye'; depth charts write 'Drake Maye'."""
    parts = (name or "").replace(".", ". ").split()
    if len(parts) < 2:
        return (name or "").strip().lower()
    return f"{parts[0][:1]}.{parts[-1]}".lower()


def parse_qb_ratings(csv_text: str) -> dict[str, QbRating]:
    """Weekly player stats → one shrunk rating per quarterback, keyed by name."""
    totals: dict[str, dict] = {}
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        if (row.get("position") or "").upper() != "QB":
            continue
        if (row.get("season_type") or "REG").upper() != "REG":
            continue
        try:
            attempts = float(row.get("attempts") or 0)
            epa = float(row.get("passing_epa") or 0)
        except (TypeError, ValueError):
            continue
        if attempts < 1:
            continue
        key = _norm(row.get("player_name") or "")
        if not key:
            continue
        entry = totals.setdefault(key, {"att": 0.0, "epa": 0.0, "team": ""})
        entry["att"] += attempts
        entry["epa"] += epa
        entry["team"] = (row.get("team") or entry["team"]).upper()

    total_att = sum(e["att"] for e in totals.values())
    if total_att <= 0:
        return {}
    league = sum(e["epa"] for e in totals.values()) / total_att

    out: dict[str, QbRating] = {}
    for key, e in totals.items():
        shrunk = (e["epa"] + SHRINK_ATTEMPTS * league) / (e["att"] + SHRINK_ATTEMPTS)
        points = (shrunk - league) * DROPBACKS_PER_GAME
        out[key] = QbRating(name=key, team=e["team"], attempts=e["att"], points=points)
    return out


def parse_expected_starters(csv_text: str) -> dict[str, str]:
    """
    Whose play each team's rating actually reflects: the quarterback with the
    most attempts for that team. Not the depth chart — the rating was earned on
    the field, not on paper.
    """
    by_team: dict[str, dict[str, float]] = {}
    for row in csv.DictReader(io.StringIO(csv_text)):
        if (row.get("position") or "").upper() != "QB":
            continue
        try:
            attempts = float(row.get("attempts") or 0)
        except (TypeError, ValueError):
            continue
        team = (row.get("team") or "").upper()
        key = _norm(row.get("player_name") or "")
        if not team or not key or attempts < 1:
            continue
        by_team.setdefault(team, {})
        by_team[team][key] = by_team[team].get(key, 0.0) + attempts

    starters: dict[str, str] = {}
    for team, arms in by_team.items():
        name, attempts = max(arms.items(), key=lambda kv: kv[1])
        if attempts >= MIN_STARTER_ATTEMPTS:
            starters[team] = name
    return starters


def is_first_string_qb(row: dict) -> bool:
    """The only rows worth keeping out of a season of daily depth charts."""
    return (
        (row.get("pos_abb") or "").upper() == "QB"
        and str(row.get("pos_rank") or "").strip() == "1"
    )


def starters_from_rows(rows: list[dict]) -> dict[str, str]:
    """The quarterback each team lists first, taken from its newest chart."""
    latest: dict[str, tuple[str, str]] = {}   # team -> (timestamp, name)
    for row in rows:
        team = (row.get("team") or "").upper()
        stamp = row.get("dt") or ""
        name = _norm(row.get("player_name") or "")
        if not team or not name:
            continue
        if team not in latest or stamp > latest[team][0]:
            latest[team] = (stamp, name)
    return {team: name for team, (_, name) in latest.items()}


def parse_depth_chart_starters(csv_text: str) -> dict[str, str]:
    """Same, from a whole file — used by tests and by any small chart."""
    rows = [r for r in csv.DictReader(io.StringIO(csv_text)) if is_first_string_qb(r)]
    return starters_from_rows(rows)


async def _load() -> tuple[dict[str, QbRating], dict[str, str], dict[str, str]]:
    cached = _fresh("qb")
    if cached is not None:
        return cached                                    # type: ignore[return-value]

    ratings: dict[str, QbRating] = {}
    expected: dict[str, str] = {}
    for season in _seasons():
        text, note = await _download_csv(PLAYER_WEEK.format(season=season))
        if text:
            ratings = parse_qb_ratings(text)
            expected = parse_expected_starters(text)
            break
        log.info("nflverse QB stats %s: %s", season, note)

    depth: dict[str, str] = {}
    for season in _seasons():
        # A season of daily snapshots runs to hundreds of thousands of rows and
        # well past the download cap, but only the first-string quarterbacks
        # are ever wanted — so the rest is streamed past rather than held.
        rows, note = await stream_csv_rows(
            DEPTH_CHART.format(season=season), is_first_string_qb,
        )
        if rows:
            depth = starters_from_rows(rows)
            break
        log.info("nflverse depth chart %s: %s", season, note)

    result = (ratings, expected, depth)
    _cache["qb"] = (time.monotonic(), result)
    return result


def compute_change(
    team: str,
    ratings: dict[str, QbRating],
    expected: dict[str, str],
    depth: dict[str, str],
) -> Optional[QbChange]:
    """The points swing from a quarterback change, or None when nothing changed."""
    team = team.upper()
    starter = depth.get(team)
    usual = expected.get(team)
    # No chart, no established starter, or the usual man is playing: the rating
    # already says everything there is to say.
    if not starter or not usual or starter == usual:
        return None

    starter_rating = ratings.get(starter)
    usual_rating = ratings.get(usual)
    if usual_rating is None:
        return None

    # A quarterback with no record at all is treated as replacement level
    # rather than as average — an unknown arm is not neutral news — but the
    # figure is deliberately modest, because it is an assumption, not a
    # measurement.
    starter_points = starter_rating.points if starter_rating else -2.0
    swing = starter_points - usual_rating.points
    swing = max(-MAX_SWING_POINTS, min(MAX_SWING_POINTS, swing))
    if abs(swing) < 0.25:
        return None
    return QbChange(team=team, starter=starter, expected=usual, points=swing)


async def changes_for(home: str, away: str) -> tuple[Optional[QbChange], Optional[QbChange]]:
    """Quarterback changes for both sides of one game."""
    try:
        ratings, expected, depth = await _load()
    except Exception as exc:                              # never break a page
        log.warning("QB adjustment unavailable: %s", type(exc).__name__)
        return None, None
    return (
        compute_change(home, ratings, expected, depth),
        compute_change(away, ratings, expected, depth),
    )


def reset_cache() -> None:
    _cache.clear()
