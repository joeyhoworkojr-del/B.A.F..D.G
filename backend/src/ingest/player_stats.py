"""
Per-player season usage from ESPN's keyless game summary.

The summary endpoint already backs play-by-play, and it also carries a
`leaders` block: for each team, the season's leading passer, rusher and
receiver with their per-game averages. That is enough to build a usage profile
for the players who actually matter to a prop line, in one request per game,
with no credentials.

Parsing is deliberately forgiving. ESPN publishes several shapes for the same
field depending on sport and season state, and this module can never raise —
a missing or unfamiliar payload yields no players, which the caller reports as
"no projection available" rather than inventing one.
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import httpx

from .espn import ESPN_BASE, LEAGUE_PATHS

log = logging.getLogger(__name__)

# Season usage barely moves inside a day; the game model refreshes far faster.
STATS_TTL_SECONDS = 900.0
_cache: dict[str, tuple[float, "PlayerPool"]] = {}

# ESPN's leader categories, mapped to the role the projection model needs.
_ROLE_BY_CATEGORY = {
    "passingYards": "passer",
    "passingLeader": "passer",
    "rushingYards": "rusher",
    "rushingLeader": "rusher",
    "receivingYards": "receiver",
    "receivingLeader": "receiver",
}


@dataclass
class PlayerUsage:
    """One player's per-game season averages, as published by ESPN."""
    athlete_id: str
    name: str
    short_name: str
    position: str
    team_abbr: str
    role: str                       # passer | rusher | receiver
    # True when the numbers are this game's actual box score rather than a
    # season average. Live props must never be presented as a projection.
    actual: bool = False
    games_played: int = 0
    # Only the fields the role actually uses are populated; the rest stay None
    # so a projection can tell "zero" from "not published".
    pass_attempts_pg: Optional[float] = None
    pass_yards_pg: Optional[float] = None
    pass_tds_pg: Optional[float] = None
    carries_pg: Optional[float] = None
    rush_yards_pg: Optional[float] = None
    rush_tds_pg: Optional[float] = None
    targets_pg: Optional[float] = None
    receptions_pg: Optional[float] = None
    rec_yards_pg: Optional[float] = None
    rec_tds_pg: Optional[float] = None


@dataclass
class PlayerPool:
    league: str
    event_id: str
    home_abbr: str = ""
    away_abbr: str = ""
    players: list[PlayerUsage] = field(default_factory=list)
    ok: bool = True
    fetched_at: str = ""
    source: str = "ESPN"


def _num(value) -> Optional[float]:
    """Pull a number out of ESPN's mixed string/number stat fields."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    # Values arrive as "271.4", "24-38", "1,204" or "3.9 AVG" depending on field.
    match = re.search(r"-?\d[\d,]*\.?\d*", text)
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def _stat_map(entry: dict) -> dict[str, float]:
    """Flatten a leader entry's statistics into name → value."""
    out: dict[str, float] = {}
    for stat in entry.get("statistics", []) or []:
        name = (stat.get("name") or stat.get("abbreviation") or "").strip()
        val = _num(stat.get("value", stat.get("displayValue")))
        if name and val is not None:
            out[name] = out.setdefault(name, val)
    # Some payloads put the headline number on the entry itself.
    headline = _num(entry.get("value", entry.get("displayValue")))
    if headline is not None:
        out.setdefault("_headline", headline)
    return out


def _per_game(total: Optional[float], games: int) -> Optional[float]:
    """ESPN mixes season totals and per-game averages; normalise to per game."""
    if total is None:
        return None
    if games and total > games * 1.5:   # looks like a season total, not an average
        return round(total / games, 2)
    return round(total, 2)


def _usage(entry: dict, category: str, team_abbr: str) -> Optional[PlayerUsage]:
    athlete = entry.get("athlete") or {}
    name = (athlete.get("displayName") or athlete.get("fullName") or "").strip()
    if not name:
        return None
    role = _ROLE_BY_CATEGORY.get(category)
    if role is None:
        return None

    stats = _stat_map(entry)
    games = int(stats.get("gamesPlayed") or stats.get("GP") or 0)

    usage = PlayerUsage(
        athlete_id=str(athlete.get("id") or name),
        name=name,
        short_name=(athlete.get("shortName") or name).strip(),
        position=((athlete.get("position") or {}).get("abbreviation") or "").strip(),
        team_abbr=team_abbr,
        role=role,
        games_played=games,
    )

    if role == "passer":
        usage.pass_attempts_pg = _per_game(stats.get("passingAttempts"), games)
        usage.pass_yards_pg = _per_game(stats.get("passingYards") or stats.get("_headline"), games)
        usage.pass_tds_pg = _per_game(stats.get("passingTouchdowns"), games)
    elif role == "rusher":
        usage.carries_pg = _per_game(stats.get("rushingAttempts"), games)
        usage.rush_yards_pg = _per_game(stats.get("rushingYards") or stats.get("_headline"), games)
        usage.rush_tds_pg = _per_game(stats.get("rushingTouchdowns"), games)
    else:
        usage.targets_pg = _per_game(stats.get("receivingTargets"), games)
        usage.receptions_pg = _per_game(stats.get("receptions"), games)
        usage.rec_yards_pg = _per_game(stats.get("receivingYards") or stats.get("_headline"), games)
        usage.rec_tds_pg = _per_game(stats.get("receivingTouchdowns"), games)

    return usage


# ESPN's boxscore stat groups, and the column order it publishes for each.
_BOX_GROUPS = {
    "passing": ("passer", ("C/ATT", "YDS", "AVG", "TD", "INT")),
    "rushing": ("rusher", ("CAR", "YDS", "AVG", "TD", "LONG")),
    "receiving": ("receiver", ("REC", "YDS", "AVG", "TD", "LONG")),
}


def _box_usage(entry: dict, group: str, team_abbr: str, keys: tuple[str, ...]) -> Optional[PlayerUsage]:
    """One player's actual line from the box score."""
    athlete = entry.get("athlete") or {}
    name = (athlete.get("displayName") or athlete.get("fullName") or "").strip()
    if not name:
        return None
    role = _BOX_GROUPS[group][0]
    values = entry.get("stats", []) or []
    stats = {k: _num(v) for k, v in zip(keys, values)}

    usage = PlayerUsage(
        athlete_id=str(athlete.get("id") or name),
        name=name,
        short_name=(athlete.get("shortName") or name).strip(),
        position=((athlete.get("position") or {}).get("abbreviation") or "").strip(),
        team_abbr=team_abbr,
        role=role,
        games_played=1,
        actual=True,
    )
    if role == "passer":
        # "C/ATT" arrives as "24/38"; _num takes the completions, so split it.
        raw = values[0] if values else ""
        if isinstance(raw, str) and "/" in raw:
            usage.pass_attempts_pg = _num(raw.split("/", 1)[1])
        usage.pass_yards_pg = stats.get("YDS")
        usage.pass_tds_pg = stats.get("TD")
    elif role == "rusher":
        usage.carries_pg = stats.get("CAR")
        usage.rush_yards_pg = stats.get("YDS")
        usage.rush_tds_pg = stats.get("TD")
    else:
        usage.receptions_pg = stats.get("REC")
        usage.rec_yards_pg = stats.get("YDS")
        usage.rec_tds_pg = stats.get("TD")
    return usage


def _parse_boxscore(data: dict, pool: "PlayerPool") -> list[PlayerUsage]:
    """
    Every player with a recorded stat in this game.

    Only populated once a game is under way. Pregame the box score is empty and
    the season `leaders` block is the only usable source, which is why both are
    parsed rather than one replacing the other.
    """
    out: list[PlayerUsage] = []
    for team_block in ((data.get("boxscore") or {}).get("players") or []):
        abbr = _team_abbr(team_block.get("team") or {})
        for group in team_block.get("statistics", []) or []:
            name = (group.get("name") or "").strip().lower()
            if name not in _BOX_GROUPS:
                continue
            keys = tuple(k.upper() for k in (group.get("keys") or group.get("labels") or ()))
            if not keys:
                keys = _BOX_GROUPS[name][1]
            for entry in group.get("athletes", []) or []:
                usage = _box_usage(entry, name, abbr, keys)
                if usage is not None:
                    out.append(usage)
    return out


def _team_abbr(team: dict) -> str:
    return str(team.get("abbreviation") or team.get("shortDisplayName") or "").strip()


def parse_pool(league: str, event_id: str, data: dict) -> PlayerPool:
    """Turn a summary payload into a player pool. Never raises."""
    pool = PlayerPool(league=league, event_id=event_id)
    try:
        competitors = ((data.get("header") or {}).get("competitions") or [{}])[0].get("competitors", [])
        for c in competitors:
            abbr = _team_abbr(c.get("team") or {})
            if (c.get("homeAway") or "") == "home":
                pool.home_abbr = abbr
            elif (c.get("homeAway") or "") == "away":
                pool.away_abbr = abbr

        seen: set[tuple[str, str]] = set()
        for team_block in data.get("leaders", []) or []:
            abbr = _team_abbr(team_block.get("team") or {})
            for cat in team_block.get("leaders", []) or []:
                category = (cat.get("name") or "").strip()
                for entry in cat.get("leaders", []) or []:
                    usage = _usage(entry, category, abbr)
                    if usage is None:
                        continue
                    key = (usage.athlete_id, usage.role)
                    if key in seen:
                        continue
                    seen.add(key)
                    pool.players.append(usage)

        # Actual box-score lines supersede season averages for the same player
        # and role: once a game starts, what happened beats what was expected.
        actual = _parse_boxscore(data, pool)
        if actual:
            by_key = {(p.athlete_id, p.role): p for p in pool.players}
            for player in actual:
                by_key[(player.athlete_id, player.role)] = player
            pool.players = list(by_key.values())
    except Exception as exc:            # a shape we don't know must not 500
        log.warning("player pool parse failed for %s %s: %s", league, event_id, exc)
        return PlayerPool(league=league, event_id=event_id, ok=False)
    return pool


async def fetch_player_pool(league: str, event_id: str) -> PlayerPool:
    """Season usage for the players in one game. Never raises."""
    league = league.lower()
    path = LEAGUE_PATHS.get(league)
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if path is None:
        return PlayerPool(league=league, event_id=event_id, ok=False, fetched_at=now_iso)

    key = f"{league}:{event_id}"
    cached = _cache.get(key)
    if cached and time.monotonic() - cached[0] < STATS_TTL_SECONDS:
        pool = cached[1]
        pool.fetched_at = now_iso
        return pool

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(f"{ESPN_BASE}/{path}/summary", params={"event": event_id})
            resp.raise_for_status()
            pool = parse_pool(league, event_id, resp.json())
        pool.fetched_at = now_iso
        if pool.ok:
            _cache[key] = (time.monotonic(), pool)
        return pool
    except Exception as exc:
        log.error("player pool fetch failed for %s %s: %s", league, event_id, exc)
        return PlayerPool(league=league, event_id=event_id, ok=False, fetched_at=now_iso)
