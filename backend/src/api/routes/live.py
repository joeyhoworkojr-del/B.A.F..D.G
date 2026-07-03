"""Live data API routes — weather, scores, and lineup availability."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.api.schemas import KeyPlayerOut, SetPlayerStatusRequest
from src.data import lineups
from src.ingest.weather import (
    NFL_INDOOR_TEAMS,
    NFL_STADIUM_COORDS,
    VENUE_COORDS,
    fetch_all_venue_weather,
    fetch_nfl_weather,
    fetch_weather,
)
from src.ingest.football_data import fetch_live_matches

router = APIRouter()


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


class LiveMatchOut(BaseModel):
    id: int
    home: str
    away: str
    home_score: Optional[int]
    away_score: Optional[int]
    status: str
    minute: Optional[int]
    stage: str


class LiveScoreboardOut(BaseModel):
    matches: list[LiveMatchOut]
    source: str


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


@router.get("/live/scores", response_model=LiveScoreboardOut, tags=["Live"])
async def get_live_scores() -> LiveScoreboardOut:
    """
    Get live and today's scheduled World Cup scores.
    Requires FOOTBALL_DATA_API_KEY in environment (free tier available).
    """
    board = await fetch_live_matches()
    return LiveScoreboardOut(
        matches=[LiveMatchOut(**m.__dict__) for m in board.matches],
        source=board.source,
    )


@router.get("/venues", tags=["Live"])
async def list_venues() -> list[str]:
    """List all known venue names for weather queries."""
    return sorted(VENUE_COORDS.keys())


@router.get("/weather/nfl/{team_code}", tags=["Live"])
async def get_nfl_stadium_weather(team_code: str) -> dict:
    """Current weather at an NFL team's home stadium (dome teams flagged)."""
    code = team_code.upper()
    if code not in NFL_STADIUM_COORDS:
        raise HTTPException(status_code=404, detail=f"Unknown NFL team: {code!r}")
    report = await fetch_nfl_weather(code)
    if report is None:
        raise HTTPException(status_code=503, detail="Weather service temporarily unavailable")
    return {
        "team": code,
        "is_indoor": code in NFL_INDOOR_TEAMS,
        "temperature_c": report.temperature_c,
        "temperature_f": report.temperature_f,
        "precipitation_prob": report.precipitation_prob,
        "wind_speed_kmh": report.wind_speed_kmh,
        "condition": report.condition,
        "source": report.source,
    }


# ─── Lineup availability (live-mutable) ──────────────────────────────────────

def _player_out(sport: str, team: str, p: lineups.KeyPlayer) -> KeyPlayerOut:
    return KeyPlayerOut(
        name=p.name, team=p.team, sport=p.sport, position=p.position,
        importance=p.importance, status=lineups.get_status(sport, team, p.name),
    )


@router.get("/lineups/{sport}/{team_code}", response_model=list[KeyPlayerOut], tags=["Lineups"])
def get_team_lineup(sport: str, team_code: str) -> list[KeyPlayerOut]:
    """Key players for a team with current availability status."""
    if sport not in ("soccer", "nfl"):
        raise HTTPException(status_code=404, detail=f"Unknown sport: {sport!r}")
    players = lineups.get_key_players(sport, team_code)
    return [_player_out(sport, team_code, p) for p in players]


@router.post("/lineups/{sport}/{team_code}", response_model=KeyPlayerOut, tags=["Lineups"])
def set_player_status(sport: str, team_code: str, req: SetPlayerStatusRequest) -> KeyPlayerOut:
    """
    Mark a key player fit/doubtful/out. Takes effect immediately on every
    subsequent prediction involving this team.
    """
    if sport not in ("soccer", "nfl"):
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
