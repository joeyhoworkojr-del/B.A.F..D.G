"""pytest configuration — adds src/ to sys.path and isolates live caches."""
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(autouse=True)
def _clear_live_caches():
    """
    Weather/scoreboard responses are cached in-process. On runners with real
    network access an earlier test can populate the cache with live data and
    starve later mocked tests — clear between tests for determinism.
    """
    from src.ingest import espn, polymarket, weather

    weather._weather_cache.clear()
    espn._cache.clear()
    polymarket._cache.clear()
    yield
    weather._weather_cache.clear()
    espn._cache.clear()
    polymarket._cache.clear()
