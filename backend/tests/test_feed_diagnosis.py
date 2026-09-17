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


def _client_by_dates(answers: dict[str, list]):
    """A patched client that answers each `dates=` value differently."""
    calls: list[str] = []

    async def get(url, params=None, **kw):
        dates = (params or {}).get("dates", "")
        calls.append(dates)
        response = MagicMock()
        response.json.return_value = {"events": answers.get(dates, [])}
        response.raise_for_status.return_value = None
        return response

    ctx = patch("httpx.AsyncClient")
    started = ctx.start()
    client = AsyncMock()
    client.get.side_effect = get
    started.return_value.__aenter__.return_value = client
    return ctx, calls


@pytest.mark.asyncio
async def test_an_empty_date_range_is_re_asked_one_day_at_a_time():
    """
    The bug this exists for: a ranged `dates=` query is the cheap way to ask,
    but the range form is not honoured identically across ESPN's leagues, and
    when it is not the answer is an empty list — indistinguishable from a week
    with no football in it. A board went blank in mid-September this way.

    A single-day `dates=` is the form the API supports everywhere, so an empty
    range is re-asked day by day before we tell anyone the schedule is empty.
    """
    today = espn.datetime.now(espn._ET).date()
    sunday = today + espn.timedelta(days=3)
    ctx, calls = _client_by_dates({f"{sunday:%Y%m%d}": [_one_event()]})
    try:
        board = await espn.fetch_upcoming("nfl", days=8)
    finally:
        ctx.stop()

    # The range was tried first and came back empty...
    assert calls[0] == f"{today:%Y%m%d}-{today + espn.timedelta(days=8):%Y%m%d}"
    # ...so every day in it was asked individually, and Sunday had a game.
    assert len(board.games) == 1
    report = espn.fetch_report()["upcoming:nfl"]
    assert report["query"] == "day-by-day"
    assert report["games_parsed"] == 1


@pytest.mark.asyncio
async def test_a_range_that_answers_is_not_re_asked_day_by_day():
    # The fallback is for the failure, not the normal path: one request must
    # stay one request when the range works.
    today = espn.datetime.now(espn._ET).date()
    span = f"{today:%Y%m%d}-{today + espn.timedelta(days=8):%Y%m%d}"
    ctx, calls = _client_by_dates({span: [_one_event()]})
    try:
        board = await espn.fetch_upcoming("nfl", days=8)
    finally:
        ctx.stop()

    assert len(board.games) == 1
    assert calls == [span]
    assert espn.fetch_report()["upcoming:nfl"]["query"] == "range"


@pytest.mark.asyncio
async def test_the_day_sweep_does_not_list_a_game_twice():
    """A game appearing in more than one day's answer is still one game."""
    everywhere = _one_event()
    calls: list[str] = []

    async def get(url, params=None, **kw):
        dates = (params or {}).get("dates", "")
        calls.append(dates)
        response = MagicMock()
        # The range answers with nothing; every single day answers with the
        # same game, which is what the sweep has to survive.
        response.json.return_value = {
            "events": [] if "-" in dates else [everywhere]
        }
        response.raise_for_status.return_value = None
        return response

    with patch("httpx.AsyncClient") as cls:
        client = AsyncMock()
        client.get.side_effect = get
        cls.return_value.__aenter__.return_value = client
        board = await espn.fetch_upcoming("ncaaf", days=8)

    assert len(calls) == 1 + 9        # the range, then each of nine days
    assert len(board.games) == 1      # deduplicated by event id


def _tiered_client(answer):
    """A client whose response depends on the `dates` value it was asked for.

    `answer(dates)` returns a list of events, or raises to simulate an HTTP
    error for that particular query shape. `dates` is "" for the undated tier.
    """
    calls: list[str] = []

    async def get(url, params=None, **kw):
        dates = (params or {}).get("dates", "")
        calls.append(dates)
        events = answer(dates)          # may raise
        response = MagicMock()
        response.json.return_value = {"events": events}
        response.raise_for_status.return_value = None
        return response

    cls = patch("httpx.AsyncClient")
    started = cls.start()
    client = AsyncMock()
    client.get.side_effect = get
    started.return_value.__aenter__.return_value = client
    return cls, calls


def _http_400(url: str) -> Exception:
    import httpx
    return httpx.HTTPStatusError(
        f"Client error '400 Bad Request' for url '{url}'",
        request=httpx.Request("GET", url),
        response=httpx.Response(400, request=httpx.Request("GET", url)),
    )


@pytest.mark.asyncio
async def test_a_400_on_the_range_falls_through_to_single_days():
    """
    What actually took the board down, from the deploy report:

        HTTPStatusError: Client error '400 Bad Request' for url
        '.../nfl/scoreboard?dates=20260917-20260925'

    The range is not answered with an empty list — it is rejected outright. A
    fallback that only runs on an empty answer never runs at all, so every
    schedule call failed while news from the same host kept working.
    """
    today = espn.datetime.now(espn._ET).date()
    sunday = today + espn.timedelta(days=3)

    def answer(dates):
        if "-" in dates:
            raise _http_400(f"scoreboard?dates={dates}")
        return [_one_event()] if dates == f"{sunday:%Y%m%d}" else []

    cls, calls = _tiered_client(answer)
    try:
        board = await espn.fetch_upcoming("nfl", days=8)
    finally:
        cls.stop()

    assert board.ok
    assert len(board.games) == 1
    assert espn.fetch_report()["upcoming:nfl"]["query"] == "day-by-day"
    assert len(calls) == 1 + 9          # the rejected range, then each day


@pytest.mark.asyncio
async def test_every_dated_query_failing_falls_through_to_no_date_filter():
    """Last resort: ask for whatever the feed considers current."""
    def answer(dates):
        if dates:
            raise _http_400(f"scoreboard?dates={dates}")
        return [_one_event()]

    cls, calls = _tiered_client(answer)
    try:
        board = await espn.fetch_upcoming("nfl", days=8)
    finally:
        cls.stop()

    assert board.ok
    assert len(board.games) == 1
    assert espn.fetch_report()["upcoming:nfl"]["query"] == "undated"
    assert calls[-1] == ""              # the undated request came last


@pytest.mark.asyncio
async def test_a_feed_that_rejects_everything_is_reported_as_down_not_empty():
    """
    The distinction the whole change exists for. If every way of asking fails,
    we do not know what is scheduled, and "no games this week" would be a
    false claim rather than a cautious one.
    """
    def answer(dates):
        raise _http_400(f"scoreboard?dates={dates}")

    cls, _ = _tiered_client(answer)
    try:
        board = await espn.fetch_upcoming("ncaaf", days=8)
    finally:
        cls.stop()

    assert board.ok is False
    report = espn.fetch_report()["upcoming:ncaaf"]
    assert report["ok"] is False
    assert "400" in report["error"]


@pytest.mark.asyncio
async def test_days_that_all_answer_empty_are_believed():
    """Nine days that each answer "nothing" is a real answer about a quiet
    week, and must not escalate to an undated request that would drag in
    games from outside the window."""
    def answer(dates):
        if "-" in dates:
            raise _http_400(f"scoreboard?dates={dates}")
        return []

    cls, calls = _tiered_client(answer)
    try:
        board = await espn.fetch_upcoming("nfl", days=8)
    finally:
        cls.stop()

    assert board.ok and board.games == []
    assert "" not in calls              # no undated request was made
    assert espn.fetch_report()["upcoming:nfl"]["query"] == "day-by-day"
