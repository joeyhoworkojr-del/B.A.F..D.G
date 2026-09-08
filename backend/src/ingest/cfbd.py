"""
College football team and player data via CollegeFootballData.com.

CFBD is free for non-commercial use but requires an API key (register at
https://collegefootballdata.com/key — it arrives by email, no card). Set
CFBD_API_KEY and this module turns on; leave it unset and every call returns
an explicit "not configured" result. It never guesses, and the absence of a key
is reported as a missing configuration rather than as missing data.

What is pulled, and why:
  /ratings/sp                — SP+, the closest thing college football has to a
                               public power rating; the single best prior.
  /stats/season/advanced     — success rate, explosiveness, EPA per play, on
                               offense and defense.
  /player/returning          — returning production, which carries most of the
                               early-season signal before any games are played.
  /games/players             — per-player game logs, for prop projections.

Season aggregates move once a week at most, so they are cached for hours. All
parsing is defensive: CFBD has changed field casing between API versions, so
each read tries the documented name and its camel/snake variant, and a field it
cannot find stays None instead of becoming zero.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from src.config import settings

log = logging.getLogger(__name__)

BASE_URL = "https://api.collegefootballdata.com"
TTL_SECONDS = 6 * 3600.0
PLAYER_TTL_SECONDS = 1800.0
REQUEST_TIMEOUT = 20.0

# Where the key comes from, reported verbatim when it is missing so the fix is
# unambiguous. The value itself is never read into any response.
KEY_ENV_VAR = "CFBD_API_KEY"
KEY_SIGNUP_URL = "https://collegefootballdata.com/key"


class Unconfigured(Exception):
    """Raised internally when the key is absent; never escapes this module."""


def api_key() -> str:
    return (getattr(settings, "cfbd_api_key", "") or "").strip()


def configured() -> bool:
    return bool(api_key())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def current_season(now: Optional[datetime] = None) -> int:
    """College seasons are labelled by the calendar year they kick off in."""
    now = now or datetime.now(timezone.utc)
    return now.year if now.month >= 2 else now.year - 1


def _pick(row: dict, *names: str) -> Any:
    """
    First present value among several spellings.

    CFBD returns camelCase on some routes and snake_case on others, and has
    switched between them across versions. Trying both is cheaper than pinning
    a version that may quietly change under a running deploy.
    """
    for name in names:
        if name in row and row[name] is not None:
            return row[name]
    return None


def _f(row: dict, *names: str) -> Optional[float]:
    val = _pick(row, *names)
    if val is None or isinstance(val, bool):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _nested(row: dict, section: str, *names: str) -> Optional[float]:
    """Advanced stats nest offense/defense blocks; missing blocks stay None."""
    block = row.get(section)
    return _f(block, *names) if isinstance(block, dict) else None


# ── data shapes ──────────────────────────────────────────────────────────────

@dataclass
class SpRating:
    team: str
    year: int
    rating: Optional[float] = None          # net points per game vs average
    offense: Optional[float] = None
    defense: Optional[float] = None
    special_teams: Optional[float] = None


@dataclass
class TeamAdvanced:
    team: str
    year: int
    off_ppa: Optional[float] = None          # predicted points added per play
    def_ppa: Optional[float] = None
    off_success_rate: Optional[float] = None
    def_success_rate: Optional[float] = None
    off_explosiveness: Optional[float] = None
    def_explosiveness: Optional[float] = None


@dataclass
class ReturningProduction:
    team: str
    year: int
    total_ppa: Optional[float] = None        # share of last year's production back
    passing_ppa: Optional[float] = None
    rushing_ppa: Optional[float] = None
    receiving_ppa: Optional[float] = None


@dataclass
class PlayerGame:
    """One player's line in one game, flattened from CFBD's category tree."""
    player_id: str
    name: str
    team: str
    position: str = ""
    passing_yards: Optional[float] = None
    passing_tds: Optional[float] = None
    completions: Optional[float] = None
    attempts: Optional[float] = None
    rushing_yards: Optional[float] = None
    rushing_tds: Optional[float] = None
    carries: Optional[float] = None
    receiving_yards: Optional[float] = None
    receiving_tds: Optional[float] = None
    receptions: Optional[float] = None


@dataclass
class CfbdResult:
    """Every public call returns this: data plus why it is or is not there."""
    ok: bool = False
    note: str = ""
    configured: bool = False
    fetched_at: str = ""
    rows: list = field(default_factory=list)


def _unconfigured(what: str) -> CfbdResult:
    return CfbdResult(
        ok=False,
        configured=False,
        note=f"{what} needs {KEY_ENV_VAR}; register free at {KEY_SIGNUP_URL}",
        fetched_at=_now(),
    )


# ── HTTP ─────────────────────────────────────────────────────────────────────

_cache: dict[str, tuple[float, list]] = {}
_locks: dict[str, asyncio.Lock] = {}
_last_error: str = ""
_last_success: str = ""


def _lock_for(key: str) -> asyncio.Lock:
    lock = _locks.get(key)
    if lock is None:
        lock = _locks[key] = asyncio.Lock()
    return lock


async def _get(path: str, params: dict[str, Any]) -> tuple[Optional[list], str]:
    """One CFBD request. Returns (rows, note); rows is None on any failure."""
    global _last_error, _last_success
    key = api_key()
    if not key:
        return None, "not configured"
    clean = {k: v for k, v in params.items() if v is not None}
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.get(
                f"{BASE_URL}{path}",
                params=clean,
                headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
            )
        if resp.status_code in (401, 403):
            _last_error = f"{KEY_ENV_VAR} rejected (HTTP {resp.status_code})"
            return None, _last_error
        if resp.status_code == 429:
            _last_error = "rate limited by CFBD"
            return None, _last_error
        if resp.status_code >= 400:
            _last_error = f"HTTP {resp.status_code}"
            return None, _last_error
        body = resp.json()
        if not isinstance(body, list):
            _last_error = "unexpected response shape"
            return None, _last_error
        _last_success = _now()
        return body, "ok"
    except httpx.HTTPError as exc:
        _last_error = f"request failed: {type(exc).__name__}"
        return None, _last_error
    except ValueError:
        _last_error = "response was not JSON"
        return None, _last_error
    except Exception as exc:                              # pragma: no cover
        log.warning("CFBD request to %s failed: %s", path, exc)
        _last_error = f"unexpected error: {type(exc).__name__}"
        return None, _last_error


async def _cached(cache_key: str, ttl: float, path: str, params: dict, parse) -> CfbdResult:
    if not configured():
        return _unconfigured(path.lstrip("/"))

    hit = _cache.get(cache_key)
    if hit and time.monotonic() - hit[0] < ttl:
        return CfbdResult(ok=True, configured=True, note="ok (cached)",
                          fetched_at=_now(), rows=hit[1])

    async with _lock_for(cache_key):
        hit = _cache.get(cache_key)
        if hit and time.monotonic() - hit[0] < ttl:
            return CfbdResult(ok=True, configured=True, note="ok (cached)",
                              fetched_at=_now(), rows=hit[1])

        body, note = await _get(path, params)
        if body is None:
            return CfbdResult(ok=False, configured=True, note=note, fetched_at=_now())
        rows = [r for r in (parse(item) for item in body if isinstance(item, dict)) if r]
        _cache[cache_key] = (time.monotonic(), rows)
        return CfbdResult(ok=True, configured=True, note="ok", fetched_at=_now(), rows=rows)


# ── public calls ─────────────────────────────────────────────────────────────

async def sp_ratings(year: Optional[int] = None) -> CfbdResult:
    year = year or current_season()

    def parse(row: dict) -> Optional[SpRating]:
        team = _pick(row, "team", "school")
        if not team:
            return None
        return SpRating(
            team=str(team),
            year=year,
            rating=_f(row, "rating"),
            offense=_nested(row, "offense", "rating") or _f(row, "offenseRating"),
            defense=_nested(row, "defense", "rating") or _f(row, "defenseRating"),
            special_teams=_nested(row, "specialTeams", "rating"),
        )

    return await _cached(f"sp:{year}", TTL_SECONDS, "/ratings/sp", {"year": year}, parse)


async def team_advanced(year: Optional[int] = None, team: Optional[str] = None) -> CfbdResult:
    year = year or current_season()

    def parse(row: dict) -> Optional[TeamAdvanced]:
        name = _pick(row, "team", "school")
        if not name:
            return None
        return TeamAdvanced(
            team=str(name),
            year=year,
            off_ppa=_nested(row, "offense", "ppa", "PPA"),
            def_ppa=_nested(row, "defense", "ppa", "PPA"),
            off_success_rate=_nested(row, "offense", "successRate", "success_rate"),
            def_success_rate=_nested(row, "defense", "successRate", "success_rate"),
            off_explosiveness=_nested(row, "offense", "explosiveness"),
            def_explosiveness=_nested(row, "defense", "explosiveness"),
        )

    key = f"adv:{year}:{team or 'all'}"
    return await _cached(key, TTL_SECONDS, "/stats/season/advanced",
                         {"year": year, "team": team}, parse)


async def returning_production(year: Optional[int] = None, team: Optional[str] = None) -> CfbdResult:
    year = year or current_season()

    def parse(row: dict) -> Optional[ReturningProduction]:
        name = _pick(row, "team", "school")
        if not name:
            return None
        return ReturningProduction(
            team=str(name),
            year=year,
            total_ppa=_f(row, "totalPPA", "total_ppa"),
            passing_ppa=_f(row, "passingPPA", "passing_ppa"),
            rushing_ppa=_f(row, "rushingPPA", "rushing_ppa"),
            receiving_ppa=_f(row, "receivingPPA", "receiving_ppa"),
        )

    key = f"ret:{year}:{team or 'all'}"
    return await _cached(key, TTL_SECONDS, "/player/returning",
                         {"year": year, "team": team}, parse)


# CFBD returns player game stats as a nested tree:
#   game → teams[] → categories[] → types[] → athletes[]
# with the stat name split across the category ("passing") and the type
# ("YDS"). This maps that pair onto the flat fields a projection needs.
_STAT_FIELDS: dict[tuple[str, str], str] = {
    ("passing", "YDS"): "passing_yards",
    ("passing", "TD"): "passing_tds",
    ("passing", "C/ATT"): "completions",       # handled specially below
    ("rushing", "YDS"): "rushing_yards",
    ("rushing", "TD"): "rushing_tds",
    ("rushing", "CAR"): "carries",
    ("receiving", "YDS"): "receiving_yards",
    ("receiving", "TD"): "receiving_tds",
    ("receiving", "REC"): "receptions",
}


def _as_float(raw: Any) -> Optional[float]:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def parse_player_games(body: list) -> list[PlayerGame]:
    """Flatten CFBD's game → team → category → type → athlete tree."""
    players: dict[str, PlayerGame] = {}
    for game in body:
        if not isinstance(game, dict):
            continue
        for team_block in game.get("teams") or []:
            if not isinstance(team_block, dict):
                continue
            team = str(_pick(team_block, "team", "school") or "")
            for cat in team_block.get("categories") or []:
                if not isinstance(cat, dict):
                    continue
                cat_name = str(cat.get("name") or "").lower()
                for stat_type in cat.get("types") or []:
                    if not isinstance(stat_type, dict):
                        continue
                    type_name = str(stat_type.get("name") or "").upper()
                    field_name = _STAT_FIELDS.get((cat_name, type_name))
                    if field_name is None:
                        continue
                    for athlete in stat_type.get("athletes") or []:
                        if not isinstance(athlete, dict):
                            continue
                        aid = str(_pick(athlete, "id", "athleteId") or "")
                        name = str(_pick(athlete, "name", "athlete") or "")
                        if not aid and not name:
                            continue
                        pkey = aid or f"{team}:{name}"
                        player = players.get(pkey)
                        if player is None:
                            player = players[pkey] = PlayerGame(
                                player_id=aid, name=name, team=team,
                            )
                        raw = athlete.get("stat")
                        # "18/27" carries completions and attempts together.
                        if type_name == "C/ATT" and isinstance(raw, str) and "/" in raw:
                            comp, _, att = raw.partition("/")
                            player.completions = _as_float(comp)
                            player.attempts = _as_float(att)
                            continue
                        value = _as_float(raw)
                        if value is not None:
                            setattr(player, field_name, value)
    return list(players.values())


async def player_games(
    year: Optional[int] = None,
    week: Optional[int] = None,
    team: Optional[str] = None,
) -> CfbdResult:
    """Per-player box scores. `team` or `week` is required by CFBD."""
    year = year or current_season()
    if not configured():
        return _unconfigured("player game logs")

    cache_key = f"pg:{year}:{week or 'all'}:{team or 'all'}"
    hit = _cache.get(cache_key)
    if hit and time.monotonic() - hit[0] < PLAYER_TTL_SECONDS:
        return CfbdResult(ok=True, configured=True, note="ok (cached)",
                          fetched_at=_now(), rows=hit[1])

    async with _lock_for(cache_key):
        hit = _cache.get(cache_key)
        if hit and time.monotonic() - hit[0] < PLAYER_TTL_SECONDS:
            return CfbdResult(ok=True, configured=True, note="ok (cached)",
                              fetched_at=_now(), rows=hit[1])

        body, note = await _get("/games/players",
                                {"year": year, "week": week, "team": team})
        if body is None:
            return CfbdResult(ok=False, configured=True, note=note, fetched_at=_now())
        rows = parse_player_games(body)
        _cache[cache_key] = (time.monotonic(), rows)
        return CfbdResult(ok=True, configured=True, note="ok", fetched_at=_now(), rows=rows)


def status() -> dict:
    """
    Provider health, with no credential material in it.

    `configured` says a key is present, not that it works — `last_success` is
    the only field that means data actually arrived.
    """
    return {
        "provider": "collegefootballdata.com",
        "requires_key": True,
        "key_env_var": KEY_ENV_VAR,
        "configured": configured(),
        "leagues": ["ncaaf"],
        "cached_datasets": len(_cache),
        "last_success": _last_success,
        "last_error": _last_error,
        "note": "" if configured()
                else f"set {KEY_ENV_VAR} (free, register at {KEY_SIGNUP_URL})",
    }


def reset_cache() -> None:
    global _last_error, _last_success
    _cache.clear()
    _last_error = ""
    _last_success = ""
