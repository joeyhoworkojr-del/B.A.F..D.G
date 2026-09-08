"""Response compression and cache policy.

These are the cheapest performance wins available and they are easy to lose in
a refactor, so they are pinned down here.
"""
from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.main import app
from src.ingest.espn import Scoreboard, _parse_event
from tests.test_ncaaf import CFB_EVENT

client = TestClient(app)


def _board():
    return Scoreboard(league="ncaaf", games=[_parse_event("ncaaf", CFB_EVENT)], fetched_at="x")


def _patched():
    async def fetch(league):
        return _board() if league == "ncaaf" else Scoreboard(league=league, games=[], fetched_at="x")
    return (
        patch("src.api.routes.predictions.fetch_scoreboard", side_effect=fetch),
        patch("src.api.routes.predictions.fetch_league_markets", return_value=[]),
    )


def test_live_endpoints_are_briefly_cacheable() -> None:
    a, b = _patched()
    with a, b:
        r = client.get("/api/v1/game/ncaaf/401752")
    assert r.status_code == 200
    cc = r.headers["cache-control"]
    # Short and without stale-while-revalidate: a CDN allowed to serve a
    # frozen score while revalidating is what left a live clock stuck.
    assert "public" in cc and "max-age=5" in cc
    assert "stale-while-revalidate" not in cc


def test_reference_data_is_cached_longer_than_live_data() -> None:
    ref = client.get("/api/v1/teams/ncaaf").headers["cache-control"]
    assert "max-age=300" in ref


def test_errors_are_never_cached() -> None:
    a, b = _patched()
    with a, b:
        r = client.get("/api/v1/game/ncaaf/nope")
    assert r.status_code == 404
    assert "cache-control" not in r.headers


def test_mutating_requests_are_never_cached() -> None:
    r = client.post("/api/v1/predict/ncaaf", json={"home": "OSU", "away": "HAW", "apply_weather": False})
    assert r.status_code == 200
    assert "cache-control" not in r.headers


def test_large_responses_are_compressed() -> None:
    r = client.get("/api/v1/teams/ncaaf", headers={"Accept-Encoding": "gzip"})
    assert r.status_code == 200
    assert r.headers.get("content-encoding") == "gzip"


def test_small_responses_skip_compression() -> None:
    r = client.get("/health", headers={"Accept-Encoding": "gzip"})
    assert r.headers.get("content-encoding") != "gzip"
