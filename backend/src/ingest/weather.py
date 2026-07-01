"""
Live weather fetching via Open-Meteo (https://open-meteo.com).

Completely free, no API key required. Updates hourly.
Provides: temperature, precipitation probability, wind speed, weather condition.

Venue coordinates for all 2026 World Cup stadiums are pre-seeded.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import httpx

log = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather code → human label (subset)
WMO_CODES: dict[int, str] = {
    0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Icy fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow",
    80: "Light showers", 81: "Showers", 82: "Heavy showers",
    95: "Thunderstorm", 96: "Thunderstorm + hail",
}

# All 2026 World Cup venue coordinates
VENUE_COORDS: dict[str, tuple[float, float]] = {
    "AT&T Stadium, Dallas":            (32.7480,  -97.0931),
    "MetLife Stadium, NJ":             (40.8136,  -74.0744),
    "SoFi Stadium, LA":                (33.9534, -118.3387),
    "Rose Bowl, Pasadena":             (34.1614, -118.1676),
    "Estadio Azteca, CDMX":            (19.3029,  -99.1505),
    "Levi's Stadium, SF":              (37.4032, -121.9698),
    "Hard Rock Stadium, Miami":        (25.9580,  -80.2389),
    "BC Place, Vancouver":             (49.2768, -123.1116),
    "BMO Field, Toronto":              (43.6332,  -79.4179),
    "NRG Stadium, Houston":            (29.6847,  -95.4107),
    "Gillette Stadium, Boston":        (42.0909,  -71.2643),
    "Lincoln Financial Field, Philly": (39.9008,  -75.1675),
    "Mercedes-Benz Stadium, Atlanta":  (33.7554,  -84.4007),
    "State Farm Stadium, Glendale":    (33.5276, -112.2626),
}


@dataclass
class WeatherReport:
    venue: str
    temperature_c: float
    temperature_f: float
    precipitation_prob: int    # 0-100 %
    wind_speed_kmh: float
    condition: str             # human-readable
    wmo_code: int
    is_indoor: bool = False
    source: str = "Open-Meteo"


async def fetch_weather(venue: str) -> Optional[WeatherReport]:
    """
    Fetch current weather for a venue.
    Returns None if venue is unknown or request fails.
    """
    coords = VENUE_COORDS.get(venue)
    if coords is None:
        log.warning("No coordinates for venue: %r", venue)
        return None

    lat, lon = coords

    # Retractable roof / indoor venues don't need weather
    indoor_venues = {"BC Place, Vancouver", "NRG Stadium, Houston",
                     "State Farm Stadium, Glendale", "Mercedes-Benz Stadium, Atlanta"}
    is_indoor = venue in indoor_venues

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,precipitation_probability,wind_speed_10m,weather_code",
        "wind_speed_unit": "kmh",
        "timezone": "auto",
    }

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(OPEN_METEO_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        current = data["current"]
        temp_c = float(current["temperature_2m"])
        precip = int(current.get("precipitation_probability", 0) or 0)
        wind = float(current.get("wind_speed_10m", 0))
        wmo = int(current.get("weather_code", 0))

        return WeatherReport(
            venue=venue,
            temperature_c=temp_c,
            temperature_f=temp_c * 9 / 5 + 32,
            precipitation_prob=precip,
            wind_speed_kmh=wind,
            condition=WMO_CODES.get(wmo, f"Code {wmo}"),
            wmo_code=wmo,
            is_indoor=is_indoor,
        )
    except httpx.HTTPError as exc:
        log.error("Weather fetch failed for %r: %s", venue, exc)
        return None


async def fetch_all_venue_weather() -> dict[str, Optional[WeatherReport]]:
    """Fetch weather for all WC venues concurrently."""
    tasks = {v: fetch_weather(v) for v in VENUE_COORDS}
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    return {
        venue: (r if isinstance(r, WeatherReport) else None)
        for venue, r in zip(tasks.keys(), results)
    }
