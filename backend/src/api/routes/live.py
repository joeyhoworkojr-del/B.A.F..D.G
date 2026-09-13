"""Live data API routes — weather, scores, and lineup availability."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from datetime import datetime, timezone

from src.api.schemas import (
    AllScoreboardsOut,
    KeyPlayerOut,
    LiveGameOut,
    NewsFeedOut,
    NewsItemOut,
    PlayByPlayOut,
    PlayOut,
    ScoreboardOut,
    SetPlayerStatusRequest,
)
from src.data import lineups
from src.ingest.news import fetch_news, fetch_news_multi
from src.ingest.espn import (
    LEAGUE_PATHS,
    fetch_playbyplay,
    fetch_scoreboard,
)
from src.ingest import cfbd, nflverse
from src.predict import priors
from src.track import ledger, store, win_history
import asyncio
from src.ingest.weather import (
    CFL_INDOOR_TEAMS,
    CFL_STADIUM_COORDS,
    MLB_INDOOR_TEAMS,
    MLB_STADIUM_COORDS,
    NFL_INDOOR_TEAMS,
    NFL_STADIUM_COORDS,
    VENUE_COORDS,
    fetch_all_venue_weather,
    fetch_gridiron_weather,
    fetch_weather,
)

router = APIRouter()

VALID_SPORTS = ("soccer", "nfl", "cfl", "mlb")

# The product is focused on American football.
FOOTBALL_LEAGUES = ("nfl", "ncaaf")


class WeatherOut(BaseModel):
    venue: str
    temperature_c: float
    temperature_f: float
    precipitation_prob: int
    wind_speed_kmh: float
    condition: str
    wmo_code: int
    is_indoor: bool
    source: str


def _board_out(board) -> ScoreboardOut:
    return ScoreboardOut(
        league=board.league,
        games=[LiveGameOut(**g.__dict__) for g in board.games],
        fetched_at=board.fetched_at,
        source=board.source,
        ok=board.ok,
    )


@router.get("/weather/{venue_key}", response_model=WeatherOut, tags=["Live"])
async def get_venue_weather(venue_key: str) -> WeatherOut:
    """
    Get current weather for a World Cup venue.

    Venue keys (URL-encode spaces or use underscores):
    AT&T Stadium, Dallas | MetLife Stadium, NJ | Estadio Azteca, CDMX | etc.

    Powered by Open-Meteo — free, no API key, updates hourly.
    """
    # Normalise underscores → spaces for convenience
    venue = venue_key.replace("_", " ")

    if venue not in VENUE_COORDS:
        available = list(VENUE_COORDS.keys())
        raise HTTPException(
            status_code=404,
            detail={"error": f"Unknown venue: {venue!r}", "available": available},
        )

    report = await fetch_weather(venue)
    if report is None:
        raise HTTPException(status_code=503, detail="Weather service temporarily unavailable")

    return WeatherOut(
        venue=report.venue,
        temperature_c=report.temperature_c,
        temperature_f=report.temperature_f,
        precipitation_prob=report.precipitation_prob,
        wind_speed_kmh=report.wind_speed_kmh,
        condition=report.condition,
        wmo_code=report.wmo_code,
        is_indoor=report.is_indoor,
        source=report.source,
    )


@router.get("/weather", tags=["Live"])
async def get_all_venue_weather() -> dict:
    """Get current weather for all World Cup venues concurrently."""
    all_weather = await fetch_all_venue_weather()
    return {
        venue: (
            {
                "temperature_c": r.temperature_c,
                "temperature_f": r.temperature_f,
                "precipitation_prob": r.precipitation_prob,
                "wind_speed_kmh": r.wind_speed_kmh,
                "condition": r.condition,
                "is_indoor": r.is_indoor,
            }
            if r
            else None
        )
        for venue, r in all_weather.items()
    }


@router.get("/live/scores", response_model=AllScoreboardsOut, tags=["Live"])
async def get_live_scores() -> AllScoreboardsOut:
    """
    Live and scheduled NFL + NCAA football games. Keyless ESPN source,
    cached 60s — genuinely live, no API key required.
    """
    boards = await asyncio.gather(*(fetch_scoreboard(lg) for lg in FOOTBALL_LEAGUES))
    for b in boards:
        ledger.grade_board(b.league, b.games)   # finals settle pending picks live
    return AllScoreboardsOut(
        boards={b.league: _board_out(b) for b in boards},
        fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


@router.get("/live/scores/{league}", response_model=ScoreboardOut, tags=["Live"])
async def get_league_scores(league: str) -> ScoreboardOut:
    """Live scoreboard for one league: nfl | ncaaf."""
    if league.lower() not in LEAGUE_PATHS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown league {league!r}; expected one of {sorted(LEAGUE_PATHS)}",
        )
    board = await fetch_scoreboard(league)
    ledger.grade_board(league.lower(), board.games)
    return _board_out(board)


@router.get("/live/pbp/{league}/{event_id}", response_model=PlayByPlayOut, tags=["Live"])
async def get_play_by_play(league: str, event_id: str) -> PlayByPlayOut:
    """Recent play-by-play for one game (keyless ESPN summary, cached ~20s)."""
    if league.lower() not in LEAGUE_PATHS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown league {league!r}; expected one of {sorted(LEAGUE_PATHS)}",
        )
    feed = await fetch_playbyplay(league, event_id)
    return PlayByPlayOut(
        league=feed.league, event_id=feed.event_id, ok=feed.ok,
        plays=[PlayOut(**p.__dict__) for p in feed.plays],
        fetched_at=feed.fetched_at,
    )


@router.get("/news", response_model=NewsFeedOut, tags=["News"])
async def get_news(league: str = "all", limit: int = 30) -> NewsFeedOut:
    """
    Latest NFL / college-football headlines from ESPN's keyless news feed.

    Only the headline, ESPN's own summary line, the byline and a link back to
    the article are returned — full article bodies are never reproduced. The
    model does not read these stories, so every item carries
    `reflected_in_projection=False`; the UI must say so rather than implying a
    projection moved because of a headline.
    """
    limit = max(1, min(limit, 50))
    key = league.lower()
    if key in ("all", "football"):
        feed = await fetch_news_multi(FOOTBALL_LEAGUES, limit=limit)
    elif key in FOOTBALL_LEAGUES:
        feed = await fetch_news(key, limit=limit)
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown league {league!r}; expected 'all' or one of {list(FOOTBALL_LEAGUES)}",
        )
    return NewsFeedOut(
        league=feed.league,
        items=[NewsItemOut(**item.__dict__) for item in feed.items],
        fetched_at=feed.fetched_at,
        ok=feed.ok,
        source=feed.source,
    )


@router.get("/venues", tags=["Live"])
async def list_venues() -> list[str]:
    """List all known venue names for weather queries."""
    return sorted(VENUE_COORDS.keys())


_STADIUMS = {
    "nfl": (NFL_STADIUM_COORDS, NFL_INDOOR_TEAMS),
    "cfl": (CFL_STADIUM_COORDS, CFL_INDOOR_TEAMS),
    "mlb": (MLB_STADIUM_COORDS, MLB_INDOOR_TEAMS),
}


async def _stadium_weather(league: str, team_code: str) -> dict:
    code = team_code.upper()
    coords, indoor = _STADIUMS[league]
    if code not in coords:
        raise HTTPException(status_code=404, detail=f"Unknown {league.upper()} team: {code!r}")
    report = await fetch_gridiron_weather(league, code)
    if report is None:
        raise HTTPException(status_code=503, detail="Weather service temporarily unavailable")
    return {
        "team": code,
        "is_indoor": code in indoor,
        "temperature_c": report.temperature_c,
        "temperature_f": report.temperature_f,
        "precipitation_prob": report.precipitation_prob,
        "wind_speed_kmh": report.wind_speed_kmh,
        "condition": report.condition,
        "source": report.source,
    }


@router.get("/weather/nfl/{team_code}", tags=["Live"])
async def get_nfl_stadium_weather(team_code: str) -> dict:
    """Current weather at an NFL team's home stadium (dome teams flagged)."""
    return await _stadium_weather("nfl", team_code)


@router.get("/weather/cfl/{team_code}", tags=["Live"])
async def get_cfl_stadium_weather(team_code: str) -> dict:
    """Current weather at a CFL team's home stadium (BC Place is a dome)."""
    return await _stadium_weather("cfl", team_code)


@router.get("/weather/mlb/{team_code}", tags=["Live"])
async def get_mlb_stadium_weather(team_code: str) -> dict:
    """Current weather at an MLB ballpark (domes/roofs flagged)."""
    return await _stadium_weather("mlb", team_code)


# ─── Lineup availability (live-mutable) ──────────────────────────────────────

def _player_out(sport: str, team: str, p: lineups.KeyPlayer) -> KeyPlayerOut:
    return KeyPlayerOut(
        name=p.name, team=p.team, sport=p.sport, position=p.position,
        importance=p.importance, status=lineups.get_status(sport, team, p.name),
    )


@router.get("/lineups/{sport}/{team_code}", response_model=list[KeyPlayerOut], tags=["Lineups"])
def get_team_lineup(sport: str, team_code: str) -> list[KeyPlayerOut]:
    """Key players for a team with current availability status."""
    if sport not in VALID_SPORTS:
        raise HTTPException(status_code=404, detail=f"Unknown sport: {sport!r}")
    players = lineups.get_key_players(sport, team_code)
    return [_player_out(sport, team_code, p) for p in players]


@router.post("/lineups/{sport}/{team_code}", response_model=KeyPlayerOut, tags=["Lineups"])
def set_player_status(sport: str, team_code: str, req: SetPlayerStatusRequest) -> KeyPlayerOut:
    """
    Mark a key player fit/doubtful/out. Takes effect immediately on every
    subsequent prediction involving this team.
    """
    if sport not in VALID_SPORTS:
        raise HTTPException(status_code=404, detail=f"Unknown sport: {sport!r}")
    try:
        player = lineups.set_status(sport, team_code, req.player, req.status)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _player_out(sport, team_code, player)


@router.delete("/lineups/{sport}/{team_code}", tags=["Lineups"])
def reset_team_lineup(sport: str, team_code: str) -> dict:
    """Reset all availability overrides for a team back to fit."""
    lineups.reset_team(sport, team_code)
    return {"status": "reset", "team": team_code.upper(), "sport": sport}


@router.get("/data/sources", tags=["Data"])
async def data_sources() -> dict:
    """
    Which upstream feeds are configured, and which have actually returned data.

    Public on purpose: the site claims to be model-driven, and this is the
    receipt. It reports provider names, configuration presence and the time of
    the last successful fetch — never a key, and never "configured" dressed up
    as "working". A provider with a key set but no successful call reads as
    exactly that.
    """
    return {
        "providers": [
            {
                "provider": "ESPN site API",
                "requires_key": False,
                "configured": True,
                "leagues": ["nfl", "ncaaf"],
                "used_for": "live scores, clock, play-by-play, box scores, news",
            },
            {**nflverse.status(), "used_for": "NFL team EPA priors and player form"},
            {**cfbd.status(), "used_for": "NCAAF SP+/PPA priors and player game logs"},
            {
                "provider": "Open-Meteo",
                "requires_key": False,
                "configured": True,
                "leagues": ["nfl"],
                "used_for": "stadium weather adjustments",
            },
        ],
        "model_priors": priors.status(),
        # Where state actually lives. This decides whether the API can run on
        # more than one machine: sessions and the graded ledger sit in this
        # store, so a per-machine SQLite file would log people out at random
        # and split the track record in two.
        "storage": {
            "backend": ledger.storage_backend(),
            "durable": ledger.storage_durable(),
            "shared_across_machines": ledger.storage_backend() in ("redis", "postgres"),
            "config": store.config_report(),
        },
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/live/win-history/{league}/{event_id}", tags=["Live"])
async def win_probability_history(league: str, event_id: str) -> dict:
    """
    Every live win-probability reading recorded for one game, oldest first.

    Empty is a valid answer, not an error: a game that has not kicked off, or
    one the server has not polled since a restart, genuinely has no timeline.
    The response says which of those it is rather than implying a flat line.
    """
    league = league.lower()
    if league not in FOOTBALL_LEAGUES:
        raise HTTPException(status_code=404, detail=f"Unknown league: {league!r}")
    points = win_history.series(league, event_id)
    return {
        "league": league,
        "event_id": event_id,
        "points": points,
        "swing": win_history.swing(league, event_id),
        "note": "" if points else "No readings recorded for this game yet.",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
