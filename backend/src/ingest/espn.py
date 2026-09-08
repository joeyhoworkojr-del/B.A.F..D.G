"""
Live scoreboards via ESPN's public (keyless) site API.

Replaces the football-data.org integration that silently returned nothing
without an API key — this source needs no credentials, so live scores work
out of the box in production. Responses are cached for 60 seconds.

Leagues:
  nfl   → football/nfl
  ncaaf → football/college-football   (FBS, group 80)
  cfl   → football/cfl
  mlb   → baseball/mlb
  wc    → soccer/fifa.world   (2026 World Cup)
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
    "nfl": "football/nfl",
    "ncaaf": "football/college-football",
    "cfl": "football/cfl",
    "mlb": "baseball/mlb",
    "wc": "soccer/fifa.world",
}

# Extra scoreboard query params per league. College football's board otherwise
# returns every FBS+FCS game (hundreds); group 80 = FBS, and the wide limit
# keeps a full Saturday slate.
LEAGUE_PARAMS: dict[str, dict[str, str]] = {
    "ncaaf": {"groups": "80", "limit": "200"},
}

# A board with a game in progress carries a running clock, so it has to be
# refetched at something close to the rate that clock changes. A quiet board
# does not, and caching it longer keeps load off the upstream feed on the six
# days a week when nothing is playing.
CACHE_TTL_SECONDS = 60.0        # no game in progress
LIVE_CACHE_TTL_SECONDS = 10.0   # at least one game in progress

_cache: dict[str, tuple[float, list["LiveGame"]]] = {}


def _board_ttl(games: list["LiveGame"]) -> float:
    return LIVE_CACHE_TTL_SECONDS if any(g.state == "in" for g in games) else CACHE_TTL_SECONDS


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
    # Live game clock / situation — drives the sportsbook-style live card
    period: Optional[int] = None               # quarter/period number
    clock: str = ""                            # "04:52"
    down_distance: str = ""                    # "1st & 10 at HAW 42"
    possession_abbr: str = ""                  # team abbr with the ball
    is_red_zone: bool = False
    # Ball position as yards from the possessing team's own goal line: 25 means
    # their own 25, 75 means the opponent's 25. None when the feed does not
    # publish it — the field view then says so instead of drawing a guess.
    yard_line: Optional[int] = None
    down: Optional[int] = None
    distance: Optional[int] = None
    last_play: str = ""                        # most recent play text
    home_logo: str = ""                        # team logo URL
    away_logo: str = ""
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


def _as_int(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _own_yard_line(
    possession_text: str, possession_abbr: str, raw_yard_line=None,
) -> Optional[int]:
    """
    Ball position as yards gained from the possessing team's own goal line.

    ESPN gives field position as text — "OSU 42" — which is ambiguous on its
    own: the 42 is a spot on somebody's half, and which half decides whether
    the offence has 58 yards to go or 42. Pairing it with the team that has the
    ball resolves it: their own side counts up from zero, the opponent's side
    counts down from a hundred.

    `situation.yardLine` is used only as a fallback, because ESPN measures it
    from a fixed end of the field rather than from the offence, and reading it
    as though it were possession-relative would draw the ball on the wrong half
    for one team every drive.
    """
    text = (possession_text or "").strip()
    abbr = (possession_abbr or "").strip().upper()
    if text and abbr:
        side, _, spot = text.rpartition(" ")
        yards = _as_int(spot)
        side = side.strip().upper()
        if yards is not None and 0 <= yards <= 50:
            if not side:
                # ESPN writes midfield as a bare "50", which needs no side to
                # place. Any other bare number is genuinely ambiguous, and
                # picking a half would put the ball in the wrong place half the
                # time — better to draw nothing.
                return 50 if yards == 50 else None
            return max(0, min(100, yards if side == abbr else 100 - yards))
    fallback = _as_int(raw_yard_line)
    if fallback is not None and 0 <= fallback <= 100:
        return fallback
    return None


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

        # Live situation: down/distance, possession, last play (football, in-game)
        sit = comp.get("situation", {}) or {}
        poss_id = sit.get("possession")
        poss_abbr = ""
        if poss_id is not None:
            for c in (home, away):
                if str(c.get("team", {}).get("id", "")) == str(poss_id):
                    poss_abbr = c.get("team", {}).get("abbreviation", "")
        down_distance = sit.get("downDistanceText", "") or ""
        possession_txt = sit.get("possessionText", "")
        if down_distance and possession_txt:
            down_distance = f"{down_distance} at {possession_txt}"
        last_play = (sit.get("lastPlay") or {}).get("text", "") or ""
        yard_line = _own_yard_line(possession_txt, poss_abbr, sit.get("yardLine"))

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
            period=status.get("period"),
            clock=status.get("displayClock", "") or "",
            down_distance=down_distance,
            possession_abbr=poss_abbr,
            is_red_zone=bool(sit.get("isRedZone", False)),
            yard_line=yard_line,
            down=_as_int(sit.get("down")),
            distance=_as_int(sit.get("distance")),
            last_play=last_play,
            home_logo=home.get("team", {}).get("logo", "") or "",
            away_logo=away.get("team", {}).get("logo", "") or "",
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
    if cached and time.monotonic() - cached[0] < _board_ttl(cached[1]):
        return Scoreboard(league=league, games=cached[1], fetched_at=now_iso)

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                f"{ESPN_BASE}/{path}/scoreboard",
                params={"dates": _dates_window(), **LEAGUE_PARAMS.get(league, {})},
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


# The week-ahead board is a different question from "what is on today", so it
# gets its own cache: a schedule days out does not change minute to minute, and
# refetching a full college slate on every page load would be wasteful.
UPCOMING_TTL_SECONDS = 300.0
MAX_UPCOMING_DAYS = 14

_upcoming_cache: dict[str, tuple[float, list["LiveGame"]]] = {}


def _upcoming_window(days: int) -> str:
    """Today through `days` ahead, in ET, as ESPN's date-range parameter."""
    today = datetime.now(_ET).date()
    return f"{today:%Y%m%d}-{today + timedelta(days=days):%Y%m%d}"


async def fetch_upcoming(league: str, days: int = 7) -> Scoreboard:
    """
    Games scheduled over the next `days`, kickoff order.

    Finished and in-progress games are dropped: this board answers "what is
    coming", and a result already on today's board would only confuse it.
    Never raises — an unreachable feed comes back as ok=False with no games.
    """
    league = league.lower()
    days = max(1, min(int(days), MAX_UPCOMING_DAYS))
    path = LEAGUE_PATHS.get(league)
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if path is None:
        return Scoreboard(league=league, ok=False, fetched_at=now_iso,
                          source=f"unknown league {league!r}")

    key = f"{league}:{days}"
    cached = _upcoming_cache.get(key)
    if cached and time.monotonic() - cached[0] < UPCOMING_TTL_SECONDS:
        return Scoreboard(league=league, games=cached[1], fetched_at=now_iso)

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(
                f"{ESPN_BASE}/{path}/scoreboard",
                params={"dates": _upcoming_window(days), **LEAGUE_PARAMS.get(league, {})},
            )
            resp.raise_for_status()
            data = resp.json()
        games = [g for g in (_parse_event(league, ev) for ev in data.get("events", [])) if g]
        games = sorted(
            (g for g in games if g.state == "pre"),
            key=lambda g: g.kickoff or "",
        )
        _upcoming_cache[key] = (time.monotonic(), games)
        return Scoreboard(league=league, games=games, fetched_at=now_iso)
    except Exception as exc:
        log.error("ESPN upcoming fetch failed for %s: %s", league, exc)
        return Scoreboard(league=league, ok=False, fetched_at=now_iso,
                          source="ESPN (temporarily unreachable)")


async def fetch_all_scoreboards() -> dict[str, Scoreboard]:
    leagues = list(LEAGUE_PATHS)
    boards = await asyncio.gather(*(fetch_scoreboard(lg) for lg in leagues))
    return dict(zip(leagues, boards))


# ─── Play-by-play (game summary) ──────────────────────────────────────────────

@dataclass
class PlayItem:
    period: Optional[int]
    clock: str
    text: str
    team_abbr: str = ""       # team that ran the play (drive team)
    scoring: bool = False
    home_score: Optional[int] = None
    away_score: Optional[int] = None


@dataclass
class GameFeed:
    league: str
    event_id: str
    ok: bool = True
    plays: list[PlayItem] = field(default_factory=list)   # newest first
    fetched_at: str = ""


_feed_cache: dict[str, tuple[float, list[PlayItem]]] = {}
# Plays land on ESPN's feed within a couple of seconds of the whistle. An 8s
# cache put us a whole play behind on a hurry-up drive, so this is tightened to
# roughly the source's own publish granularity. It still collapses a burst of
# viewers on the same game into one upstream fetch.
_FEED_TTL = 2.5


def _play_item(p: dict, team_abbr: str = "") -> PlayItem:
    return PlayItem(
        period=(p.get("period") or {}).get("number"),
        clock=(p.get("clock") or {}).get("displayValue", "") or "",
        text=p.get("text", "") or "",
        team_abbr=team_abbr,
        scoring=bool(p.get("scoringPlay", False)),
        home_score=p.get("homeScore"),
        away_score=p.get("awayScore"),
    )


def _parse_plays(data: dict) -> list[PlayItem]:
    """Newest-first play list from an ESPN summary.

    Prefer the per-drive plays (they carry the offense's team abbreviation),
    and fall back to the summary's flat ``plays`` array when drives are empty —
    some live college games only populate one or the other.
    """
    drives = data.get("drives", {}) or {}
    raw_drives: list[dict] = list(drives.get("previous", []) or [])
    if drives.get("current"):
        raw_drives.append(drives["current"])

    items: list[PlayItem] = []
    for dr in raw_drives:
        team_abbr = (dr.get("team") or {}).get("abbreviation", "") or ""
        for p in dr.get("plays", []) or []:
            items.append(_play_item(p, team_abbr))

    # Fallback: a flat top-level plays array (chronological) if drives were empty.
    if not items:
        for p in data.get("plays", []) or []:
            items.append(_play_item(p))

    items.reverse()   # newest first
    return items


async def fetch_playbyplay(league: str, event_id: str, limit: int = 40) -> GameFeed:
    """Recent play-by-play for one game via ESPN's keyless summary endpoint."""
    league = league.lower()
    path = LEAGUE_PATHS.get(league)
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if path is None:
        return GameFeed(league=league, event_id=event_id, ok=False, fetched_at=now_iso)

    key = f"{league}:{event_id}"
    cached = _feed_cache.get(key)
    if cached and time.monotonic() - cached[0] < _FEED_TTL:
        return GameFeed(league=league, event_id=event_id,
                        plays=cached[1][:limit], fetched_at=now_iso)
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                f"{ESPN_BASE}/{path}/summary", params={"event": event_id},
            )
            resp.raise_for_status()
            plays = _parse_plays(resp.json())
        _feed_cache[key] = (time.monotonic(), plays)
        return GameFeed(league=league, event_id=event_id,
                        plays=plays[:limit], fetched_at=now_iso)
    except Exception as exc:
        log.error("ESPN summary fetch failed for %s %s: %s", league, event_id, exc)
        return GameFeed(league=league, event_id=event_id, ok=False, fetched_at=now_iso)
