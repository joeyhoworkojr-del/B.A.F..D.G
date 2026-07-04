"""Live data API routes — weather, scores, and lineup availability."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from datetime import datetime, timezone

from src.api.schemas import (
    AllScoreboardsOut,
    KeyPlayerOut,
    LiveGameOut,
    ScoreboardOut,
    SetPlayerStatusRequest,
)
from src.data import lineups
from src.ingest.espn import LEAGUE_PATHS, fetch_all_scoreboards, fetch_scoreboard
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
    Live and scheduled games for all covered leagues (World Cup, NFL, CFL).
    Keyless ESPN source, cached 60s — genuinely live, no API key required.
    """
    boards = await fetch_all_scoreboards()
    return AllScoreboardsOut(
        boards={lg: _board_out(b) for lg, b in boards.items()},
        fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


@router.get("/live/scores/{league}", response_model=ScoreboardOut, tags=["Live"])
async def get_league_scores(league: str) -> ScoreboardOut:
    """Live scoreboard for one league: wc | nfl | cfl."""
    if league.lower() not in LEAGUE_PATHS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown league {league!r}; expected one of {sorted(LEAGUE_PATHS)}",
        )
    return _board_out(await fetch_scoreboard(league))


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
