"""
Opening a game from the board.

The homepage lists a week across both leagues. The game endpoint only ever
searched today's scoreboard, so every game beyond today answered "no game on
the current board" — for a game the reader was looking at on the board when
they tapped it.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.ingest.espn import LiveGame, Scoreboard

client = TestClient(app)

FUTURE_GAME = LiveGame(
    league="nfl", event_id="401872657",
    home="Seattle Seahawks", away="New England Patriots",
    home_abbr="SEA", away_abbr="NE",
    home_score=None, away_score=None,
    state="pre", detail="Wed 5:20 PM", kickoff="2026-09-16T21:20:00Z",
)

TODAY_GAME = LiveGame(
    league="nfl", event_id="401800000",
    home="Kansas City Chiefs", away="Baltimore Ravens",
    home_abbr="KC", away_abbr="BAL",
    home_score=14, away_score=10,
    state="in", detail="Q3 6:59", kickoff="2026-09-09T00:20:00Z",
)


def _board(games, ok=True):
    async def fetch(league, *_a, **_k):
        return Scoreboard(league=league, games=list(games),
                          fetched_at="2026-09-09T00:00:00Z", source="ESPN", ok=ok)
    return fetch


async def _no_markets(_league, *_a, **_k):
    return []


@pytest.fixture
def feeds():
    """Today has one live game; the week ahead has a different one."""
    with patch("src.api.routes.predictions.fetch_scoreboard", _board([TODAY_GAME])), \
         patch("src.api.routes.predictions.fetch_upcoming", _board([FUTURE_GAME])), \
         patch("src.api.routes.predictions.fetch_league_markets", _no_markets):
        yield


def test_a_game_later_in_the_week_opens_from_the_board(feeds):
    response = client.get("/api/v1/game/nfl/401872657")
    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["game"]["home_abbr"] == "SEA"
    assert body["game"]["away_abbr"] == "NE"


def test_todays_game_is_still_found_first(feeds):
    # The today feed carries score, clock and possession that the schedule
    # does not, so it has to stay the first place looked.
    response = client.get("/api/v1/game/nfl/401800000")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "in"
    assert body["game"]["home_score"] == 14


def test_props_for_a_game_later_in_the_week_also_resolve(feeds):
    response = client.get("/api/v1/props/nfl/401872657")
    assert response.status_code == 200, response.json()
    assert response.json()["event_id"] == "401872657"


def test_a_game_that_is_genuinely_not_scheduled_still_says_so(feeds):
    response = client.get("/api/v1/game/nfl/000000000")
    assert response.status_code == 404
    detail = response.json()["detail"]
    # And says what was actually searched, rather than "the current board",
    # which described a window the reader had no way to know about.
    assert "scheduled in the next" in detail


def test_a_dead_feed_is_reported_as_a_feed_problem_not_a_missing_game(feeds):
    with patch("src.api.routes.predictions.fetch_scoreboard", _board([], ok=False)), \
         patch("src.api.routes.predictions.fetch_upcoming", _board([])):
        response = client.get("/api/v1/game/nfl/401872657")
    assert response.status_code == 404
    assert "temporarily unreachable" in response.json()["detail"]
