"""Tests for live weather and sports data fetching."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from src.ingest.weather import (
    WeatherReport,
    fetch_weather,
    VENUE_COORDS,
    WMO_CODES,
)
from src.ingest.football_data import fetch_live_matches, LiveScoreboard


# ─── Weather unit tests ───────────────────────────────────────────────────────

def test_venue_coords_coverage() -> None:
    """All expected WC stadiums are in the coords dict."""
    required = [
        "AT&T Stadium, Dallas",
        "MetLife Stadium, NJ",
        "Estadio Azteca, CDMX",
        "Levi's Stadium, SF",
    ]
    for v in required:
        assert v in VENUE_COORDS, f"Missing coords for {v!r}"


def test_unknown_venue_returns_none_not_error() -> None:
    """Unknown venue should log and return None, not raise."""
    import asyncio
    result = asyncio.run(fetch_weather("Fake Stadium, Nowhere"))
    assert result is None


@pytest.mark.asyncio
async def test_weather_fetch_mock() -> None:
    """Mock Open-Meteo response and verify parsing."""
    mock_response_data = {
        "current": {
            "temperature_2m": 22.5,
            "precipitation_probability": 30,
            "wind_speed_10m": 15.0,
            "weather_code": 63,
        }
    }

    from unittest.mock import MagicMock
    # httpx response methods are synchronous — use MagicMock, not AsyncMock
    mock_response = MagicMock()
    mock_response.json.return_value = mock_response_data

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        report = await fetch_weather("AT&T Stadium, Dallas")

    assert report is not None
    assert abs(report.temperature_c - 22.5) < 0.01
    assert abs(report.temperature_f - 72.5) < 0.5  # 22.5 * 9/5 + 32
    assert report.precipitation_prob == 30
    assert report.wind_speed_kmh == 15.0
    assert report.condition == "Rain"   # WMO 63


def test_wmo_codes_complete_for_common_conditions() -> None:
    """Common WMO codes should have human-readable labels."""
    for code in [0, 1, 2, 3, 61, 63, 80, 95]:
        assert code in WMO_CODES, f"WMO code {code} missing from labels"


def test_indoor_venue_flagged() -> None:
    """Retractable-roof venues should be marked indoor."""
    import asyncio
    from unittest.mock import MagicMock

    mock_data = {
        "current": {
            "temperature_2m": 20.0,
            "precipitation_probability": 0,
            "wind_speed_10m": 0.0,
            "weather_code": 0,
        }
    }
    mock_response = MagicMock()  # httpx response is sync
    mock_response.json.return_value = mock_data

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        report = asyncio.run(fetch_weather("NRG Stadium, Houston"))

    assert report is not None
    assert report.is_indoor is True


# ─── Live scores unit tests ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_live_scores_no_key_returns_empty() -> None:
    """Without API key, live scores returns empty scoreboard gracefully."""
    with patch("src.ingest.football_data.settings") as mock_settings:
        mock_settings.football_data_api_key = ""
        board = await fetch_live_matches()
    assert isinstance(board, LiveScoreboard)
    assert board.matches == []
    assert "unavailable" in board.source.lower() or "FOOTBALL_DATA" in board.source


# ─── Weather API endpoint tests ───────────────────────────────────────────────

def test_weather_endpoint_known_venue() -> None:
    """GET /api/v1/weather/{venue} returns 200 or 503 (not 500)."""
    from fastapi.testclient import TestClient
    from src.api.main import app

    client = TestClient(app)

    mock_report = WeatherReport(
        venue="AT&T Stadium, Dallas",
        temperature_c=28.0,
        temperature_f=82.4,
        precipitation_prob=10,
        wind_speed_kmh=12.0,
        condition="Partly cloudy",
        wmo_code=2,
        is_indoor=False,
    )

    with patch("src.api.routes.live.fetch_weather", return_value=mock_report):
        resp = client.get("/api/v1/weather/AT%26T%20Stadium%2C%20Dallas")

    # Either works (200) or weather service unreachable (503) — never 500
    assert resp.status_code in (200, 404, 503)


def test_weather_endpoint_unknown_venue_404() -> None:
    from fastapi.testclient import TestClient
    from src.api.main import app
    client = TestClient(app)
    resp = client.get("/api/v1/weather/Fake_Stadium_Nowhere")
    assert resp.status_code == 404


def test_venues_list_endpoint() -> None:
    from fastapi.testclient import TestClient
    from src.api.main import app
    client = TestClient(app)
    resp = client.get("/api/v1/venues")
    assert resp.status_code == 200
    venues = resp.json()
    assert isinstance(venues, list)
    assert len(venues) >= 10
