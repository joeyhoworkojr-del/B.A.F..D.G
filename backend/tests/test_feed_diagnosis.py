"""
Telling apart the reasons a board comes back empty.

From outside the machine, "the schedule really is empty", "the feed refused
us" and "the feed answered and we could not read any of it" all look the same:
zero games. They need completely different responses, so the ingest layer
records the raw event count beside the parsed count, and whether the call
failed at all. Without that, diagnosing an empty board in production is
guesswork — which is exactly what it was.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ingest import espn


def _client_returning(payload):
    """A patched httpx.AsyncClient whose single GET returns this JSON."""
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None

    ctx = patch("httpx.AsyncClient")
    started = ctx.start()
    client = AsyncMock()
    client.get.return_value = response
    started.return_value.__aenter__.return_value = client
    return ctx


def _one_event():
    """A minimally well-formed ESPN event the parser can read."""
    def team(abbr, side):
        return {
            "homeAway": side,
            "score": "0",
            "team": {"id": abbr, "abbreviation": abbr,
                     "displayName": abbr, "logo": ""},
        }
    return {
        "id": "1",
        "date": "2026-09-20T17:00Z",
        "status": {"type": {"state": "pre", "shortDetail": "Sun 1:00 PM"}},
        "competitions": [{"competitors": [team("BUF", "home"), team("KC", "away")]}],
    }


@pytest.mark.asyncio
async def test_a_readable_feed_reports_what_it_returned_and_what_we_kept():
    ctx = _client_returning({"events": [_one_event()]})
    try:
        board = await espn.fetch_upcoming("nfl", days=8)
    finally:
        ctx.stop()

    assert board.ok
    assert len(board.games) == 1
    report = espn.fetch_report()["upcoming:nfl"]
    assert report["ok"] is True
    assert report["events_returned"] == 1
    assert report["games_parsed"] == 1
    assert report["error"] == ""


@pytest.mark.asyncio
async def test_a_feed_we_can_no_longer_read_does_not_look_like_an_empty_week():
    """
    The failure that would be invisible: ESPN changes shape, every event is
    swallowed by the parser's per-event guard, and the board reports a quiet
    week in the middle of the season. The counts are what expose it.
    """
    ctx = _client_returning({"events": [{"nothing": "we recognise"} for _ in range(12)]})
    try:
        board = await espn.fetch_upcoming("ncaaf", days=8)
    finally:
        ctx.stop()

    assert board.games == []
    report = espn.fetch_report()["upcoming:ncaaf"]
    assert report["events_returned"] == 12
    assert report["games_parsed"] == 0


@pytest.mark.asyncio
async def test_a_genuinely_quiet_week_is_recorded_as_a_quiet_week():
    ctx = _client_returning({"events": []})
    try:
        board = await espn.fetch_upcoming("nfl", days=8)
    finally:
        ctx.stop()

    assert board.ok and board.games == []
    report = espn.fetch_report()["upcoming:nfl"]
    assert report["events_returned"] == 0
    assert report["games_parsed"] == 0


@pytest.mark.asyncio
async def test_an_unreachable_feed_records_the_error_rather_than_a_count():
    class Boom:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, *a, **k): raise OSError("connection refused")

    with patch("httpx.AsyncClient", lambda **k: Boom()):
        board = await espn.fetch_scoreboard("nfl")

    assert board.ok is False
    report = espn.fetch_report()["scoreboard:nfl"]
    assert report["ok"] is False
    assert "OSError" in report["error"]
    assert report["games_parsed"] == 0


def test_the_public_data_sources_page_carries_the_diagnosis():
    from fastapi.testclient import TestClient
    from src.api.main import app

    body = TestClient(app).get("/api/v1/data/sources").json()
    espn_entry = next(
        p for p in body["providers"] if p["provider"] == "ESPN site API"
    )
    assert "last_fetch" in espn_entry
