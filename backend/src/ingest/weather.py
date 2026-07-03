"""
Live weather fetching via Open-Meteo (https://open-meteo.com).

Completely free, no API key required. Updates hourly.
Provides: temperature, precipitation probability, wind speed, weather condition.

Venue coordinates for all 2026 World Cup stadiums are pre-seeded.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx

log = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Fetch cache: (lat, lon) → (monotonic timestamp, report)
CACHE_TTL_SECONDS = 900.0
_weather_cache: dict[tuple[float, float], tuple[float, "WeatherReport"]] = {}

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

# NFL stadium coordinates by home-team code (indoor/fixed-roof teams flagged below)
NFL_STADIUM_COORDS: dict[str, tuple[float, float]] = {
    "BAL": (39.2780, -76.6227), "CIN": (39.0955, -84.5161),
    "CLE": (41.5061, -81.6995), "PIT": (40.4468, -80.0158),
    "HOU": (29.6847, -95.4107), "IND": (39.7601, -86.1639),
    "JAX": (30.3239, -81.6373), "TEN": (36.1665, -86.7713),
    "BUF": (42.7738, -78.7870), "MIA": (25.9580, -80.2389),
    "NE":  (42.0909, -71.2643), "NYJ": (40.8136, -74.0744),
    "KC":  (39.0489, -94.4839), "LAC": (33.9534, -118.3387),
    "LV":  (36.0909, -115.1833), "DEN": (39.7439, -105.0201),
    "CHI": (41.8623, -87.6167), "DET": (42.3400, -83.0456),
    "GB":  (44.5013, -88.0622), "MIN": (44.9738, -93.2575),
    "ATL": (33.7554, -84.4007), "CAR": (35.2258, -80.8528),
    "NO":  (29.9511, -90.0812), "TB":  (27.9759, -82.5033),
    "DAL": (32.7480, -97.0931), "NYG": (40.8136, -74.0744),
    "PHI": (39.9008, -75.1675), "WSH": (38.9077, -76.8645),
    "ARI": (33.5276, -112.2626), "LA": (33.9534, -118.3387),
    "SF":  (37.4032, -121.9698), "SEA": (47.5952, -122.3316),
}

# Teams that play in domes / fixed-roof stadiums — weather never applies
NFL_INDOOR_TEAMS: set[str] = {
    "ATL", "NO", "DET", "MIN", "LV", "LAC", "LA", "ARI", "HOU", "IND", "DAL",
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


async def fetch_weather_at(
    lat: float,
    lon: float,
    *,
    venue: str = "",
    is_indoor: bool = False,
) -> Optional[WeatherReport]:
    """Fetch current weather for arbitrary coordinates (15-min cache)."""
    now = time.monotonic()
    cached = _weather_cache.get((lat, lon))
    if cached and now - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

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

        report = WeatherReport(
            venue=venue,
            temperature_c=temp_c,
            temperature_f=temp_c * 9 / 5 + 32,
            precipitation_prob=precip,
            wind_speed_kmh=wind,
            condition=WMO_CODES.get(wmo, f"Code {wmo}"),
            wmo_code=wmo,
            is_indoor=is_indoor,
        )
        _weather_cache[(lat, lon)] = (now, report)
        return report
    except Exception as exc:  # weather is an enhancement — never break predictions
        log.error("Weather fetch failed for %r: %s", venue, exc)
        return None


async def fetch_weather(venue: str) -> Optional[WeatherReport]:
    """
    Fetch current weather for a named World Cup venue.
    Returns None if venue is unknown or request fails.
    """
    coords = VENUE_COORDS.get(venue)
    if coords is None:
        log.warning("No coordinates for venue: %r", venue)
        return None

    # Retractable roof / indoor venues don't need weather
    indoor_venues = {"BC Place, Vancouver", "NRG Stadium, Houston",
                     "State Farm Stadium, Glendale", "Mercedes-Benz Stadium, Atlanta"}
    lat, lon = coords
    return await fetch_weather_at(lat, lon, venue=venue, is_indoor=venue in indoor_venues)


async def fetch_nfl_weather(team_code: str) -> Optional[WeatherReport]:
    """Fetch current weather at an NFL team's home stadium."""
    code = team_code.upper()
    coords = NFL_STADIUM_COORDS.get(code)
    if coords is None:
        log.warning("No stadium coordinates for NFL team: %r", code)
        return None
    lat, lon = coords
    return await fetch_weather_at(
        lat, lon,
        venue=f"{code} home stadium",
        is_indoor=code in NFL_INDOOR_TEAMS,
    )


async def fetch_all_venue_weather() -> dict[str, Optional[WeatherReport]]:
    """Fetch weather for all WC venues concurrently."""
    tasks = {v: fetch_weather(v) for v in VENUE_COORDS}
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    return {
        venue: (r if isinstance(r, WeatherReport) else None)
        for venue, r in zip(tasks.keys(), results)
    }
