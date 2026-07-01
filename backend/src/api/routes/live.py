"""Live data API routes — weather and scores."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.ingest.weather import fetch_weather, fetch_all_venue_weather, VENUE_COORDS
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
