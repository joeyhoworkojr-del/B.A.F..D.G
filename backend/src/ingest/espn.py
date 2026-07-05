"""
Live scoreboards via ESPN's public (keyless) site API.

Replaces the football-data.org integration that silently returned nothing
without an API key — this source needs no credentials, so live scores work
out of the box in production. Responses are cached for 60 seconds.

Leagues:
  wc  → soccer/fifa.world   (2026 World Cup)
  nfl → football/nfl
  cfl → football/cfl
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

import httpx

log = logging.getLogger(__name__)

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports"

# The North American sports day is anchored to US/Eastern: a 10 PM PT game is
# still "tonight" in ET, and ESPN's own boards roll over on ET midnight.
_ET = ZoneInfo("America/New_York")

LEAGUE_PATHS: dict[str, str] = {
    "wc": "soccer/fifa.world",
    "nfl": "football/nfl",
    "cfl": "football/cfl",
    "mlb": "baseball/mlb",
}

CACHE_TTL_SECONDS = 60.0
_cache: dict[str, tuple[float, list["LiveGame"]]] = {}


@dataclass
class LiveGame:
    league: str
    event_id: str
    home: str              # display name
    away: str
    home_abbr: str
    away_abbr: str
    home_score: Optional[int]
    away_score: Optional[int]
    state: str             # "pre" | "in" | "post"
    detail: str            # e.g. "45' +2", "Q3 5:21", "Sat 8:00 PM", "Final"
    kickoff: str = ""      # ISO timestamp
    # Live market (sportsbook odds embedded in the ESPN feed) — what the
    # public's money is doing right now
    market_spread: Optional[float] = None      # home-based, e.g. -3.5
    market_over_under: Optional[float] = None  # e.g. 47.5
    market_home_ml: Optional[float] = None     # American odds
    market_away_ml: Optional[float] = None
    market_details: str = ""                   # e.g. "KC -3.5"
    market_provider: str = ""                  # e.g. "ESPN BET"


@dataclass
class Scoreboard:
    league: str
    games: list[LiveGame] = field(default_factory=list)
    fetched_at: str = ""   # ISO timestamp — freshness stamp for the UI
    source: str = "ESPN"
    ok: bool = True


def _parse_event(league: str, ev: dict) -> Optional[LiveGame]:
    try:
        comp = ev["competitions"][0]
        status = ev.get("status", {})
        stype = status.get("type", {})
        home = away = None
        for c in comp.get("competitors", []):
            if c.get("homeAway") == "home":
                home = c
            elif c.get("homeAway") == "away":
                away = c
        if home is None or away is None:
            return None

        def score(c: dict) -> Optional[int]:
            s = c.get("score")
            try:
                return int(float(s)) if s not in (None, "") else None
            except (TypeError, ValueError):
                return None

        # Sportsbook odds ride along in the feed (provider varies by league)
        spread = over_under = home_ml = away_ml = None
        details = provider = ""
        for odds in comp.get("odds", []) or []:
            try:
                if odds.get("spread") is not None:
                    spread = float(odds["spread"])
                if odds.get("overUnder") is not None:
                    over_under = float(odds["overUnder"])
                h = (odds.get("homeTeamOdds") or {}).get("moneyLine")
                a = (odds.get("awayTeamOdds") or {}).get("moneyLine")
                home_ml = float(h) if h is not None else home_ml
                away_ml = float(a) if a is not None else away_ml
                details = odds.get("details", "") or details
                provider = (odds.get("provider") or {}).get("name", "") or provider
            except (TypeError, ValueError):
                continue
            if spread is not None or over_under is not None or home_ml is not None:
                break   # first usable book wins

        return LiveGame(
            league=league,
            event_id=str(ev.get("id", "")),
            home=home.get("team", {}).get("displayName", "?"),
            away=away.get("team", {}).get("displayName", "?"),
            home_abbr=home.get("team", {}).get("abbreviation", ""),
            away_abbr=away.get("team", {}).get("abbreviation", ""),
            home_score=score(home),
            away_score=score(away),
            state=stype.get("state", "pre"),
            detail=stype.get("shortDetail", stype.get("detail", "")),
            kickoff=ev.get("date", ""),
            market_spread=spread,
            market_over_under=over_under,
            market_home_ml=home_ml,
            market_away_ml=away_ml,
            market_details=details,
            market_provider=provider,
        )
    except Exception:  # one malformed event must not sink the board
        return None


def _dates_window() -> str:
    """Explicit yesterday→tomorrow (ET) range for the scoreboard request.

    Without a `dates` param ESPN returns the whole *current week* for
    football leagues, so a Saturday CFL board would still be full of
    Thursday's finals presented as if they were current.
    """
    today = datetime.now(_ET).date()
    return f"{today - timedelta(days=1):%Y%m%d}-{today + timedelta(days=1):%Y%m%d}"


def is_current(game: "LiveGame", now: Optional[datetime] = None) -> bool:
    """Whether a game belongs on 'today's board': in progress, finished on
    today's ET sports day, or scheduled within the next 48 hours."""
    if game.state == "in":
        return True
    try:
        kickoff = datetime.fromisoformat(game.kickoff.replace("Z", "+00:00"))
    except ValueError:
        return True   # unparseable kickoff — keep rather than silently hide
    now = now or datetime.now(timezone.utc)
    if game.state == "post":
        return kickoff.astimezone(_ET).date() >= now.astimezone(_ET).date()
    return kickoff - now <= timedelta(hours=48)


async def fetch_scoreboard(league: str) -> Scoreboard:
    """Fetch today's games for a league. Never raises — ok=False on failure."""
    league = league.lower()
    path = LEAGUE_PATHS.get(league)
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if path is None:
        return Scoreboard(league=league, ok=False, fetched_at=now_iso,
                          source=f"unknown league {league!r}")

    cached = _cache.get(league)
    if cached and time.monotonic() - cached[0] < CACHE_TTL_SECONDS:
        return Scoreboard(league=league, games=cached[1], fetched_at=now_iso)

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                f"{ESPN_BASE}/{path}/scoreboard",
                params={"dates": _dates_window()},
            )
            resp.raise_for_status()
            data = resp.json()
        games = [g for g in (_parse_event(league, ev) for ev in data.get("events", [])) if g]
        _cache[league] = (time.monotonic(), games)
        return Scoreboard(league=league, games=games, fetched_at=now_iso)
    except Exception as exc:
        log.error("ESPN scoreboard fetch failed for %s: %s", league, exc)
        return Scoreboard(league=league, ok=False, fetched_at=now_iso,
                          source="ESPN (temporarily unreachable)")


async def fetch_all_scoreboards() -> dict[str, Scoreboard]:
    leagues = list(LEAGUE_PATHS)
    boards = await asyncio.gather(*(fetch_scoreboard(lg) for lg in leagues))
    return dict(zip(leagues, boards))
