"""pytest configuration — adds src/ to sys.path and isolates live caches."""
import sys
import os
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Isolate the prediction ledger from any real ledger.db
os.environ.setdefault(
    "LEDGER_PATH", os.path.join(tempfile.mkdtemp(prefix="ledger-test-"), "ledger.db"),
)

# The app's background snapshot loop must never run during tests — it would
# reach for the live ESPN feed and write to the ledger mid-assertion.
os.environ["SNAPSHOTS_ENABLED"] = "0"


@pytest.fixture(autouse=True)
def _clear_live_caches():
    """
    Weather/scoreboard responses are cached in-process. On runners with real
    network access an earlier test can populate the cache with live data and
    starve later mocked tests — clear between tests for determinism.
    """
    from src.ingest import espn, polymarket, weather

    from src.track import ledger, ratings

    weather._weather_cache.clear()
    espn._cache.clear()
    polymarket._cache.clear()
    ledger.reset()
    ratings.reset()
    yield
    weather._weather_cache.clear()
    espn._cache.clear()
    polymarket._cache.clear()
