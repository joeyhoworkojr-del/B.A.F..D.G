"""
The merged board.

One list across both leagues, grouped by the day a game is actually played.
The behaviour worth protecting is what happens when today is empty — a
Wednesday in September has no college football, and an empty page is almost
never the truth. It just is not true *today*.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes import predictions as pred
from src.ingest.espn import LiveGame, Scoreboard

client = TestClient(app)


def game(event_id, league="nfl", state="pre", hours=3, home="BUF", away="KC"):
    return LiveGame(
        league=league, event_id=event_id, home=home, away=away,
        home_abbr=home, away_abbr=away, home_score=None, away_score=None,
        state=state, detail="", kickoff=(
            datetime.now(timezone.utc) + timedelta(hours=hours)
        ).isoformat(),
    )


def board_with(today_games, upcoming_games):
    """Patch both feeds so the board sees exactly these games."""
    async def fake_scoreboard(league):
        return Scoreboard(league=league, games=today_games.get(league, []),
                          fetched_at="now", ok=True)

    async def fake_upcoming(league, days=7):
        return Scoreboard(league=league, games=upcoming_games.get(league, []),
                          fetched_at="now", ok=True)

    async def fake_markets(league):
        return []

    async def fake_entry(league, g, poly, **kw):
        return {"game": {"event_id": g.event_id, "state": g.state,
                         "home_abbr": g.home_abbr, "away_abbr": g.away_abbr,
                         "kickoff": g.kickoff},
                "mapped": True, "model": None, "edges": [], "polymarket": None}

    return patch.multiple(
        pred,
        fetch_scoreboard=fake_scoreboard,
        fetch_upcoming=fake_upcoming,
        fetch_league_markets=fake_markets,
        _slate_entry=fake_entry,
    )


def get_board():
    return client.get("/api/v1/board").json()


def test_both_leagues_land_on_one_board():
    with board_with({"nfl": [game("1", "nfl")], "ncaaf": [game("2", "ncaaf")]}, {}):
        data = get_board()
    leagues = {g["league"] for d in data["days"] for g in d["games"]}
    assert leagues == {"nfl", "ncaaf"}
    assert data["total_games"] == 2


def test_an_empty_today_rolls_forward_instead_of_showing_nothing():
    """
    The Wednesday problem. No college games and one NFL game should not read as
    "nothing on" — it should show the NFL game, then the days that follow.
    """
    later = game("99", "ncaaf", hours=48)
    with board_with({"nfl": [game("1", "nfl")], "ncaaf": []}, {"ncaaf": [later]}):
        data = get_board()

    assert data["total_games"] == 2
    assert len(data["days"]) >= 1
    # Nothing is claimed to be missing, because nothing is.
    assert data["note"] == ""


def test_a_completely_empty_board_says_so_rather_than_rendering_blank():
    with board_with({}, {}):
        data = get_board()
    assert data["days"] == []
    assert "No games scheduled" in data["note"]


def test_live_games_sort_above_everything_else_that_day():
    soon = game("1", "nfl", state="pre", hours=1)
    playing = game("2", "nfl", state="in", hours=-1)
    with board_with({"nfl": [soon, playing]}, {}):
        data = get_board()

    first_day = data["days"][0]["games"]
    assert first_day[0]["game"]["event_id"] == "2"     # the live one
    assert data["live_count"] == 1


def test_games_are_grouped_by_the_day_they_are_played():
    tonight = game("1", "nfl", hours=2)
    in_two_days = game("2", "nfl", hours=50)
    with board_with({"nfl": [tonight]}, {"nfl": [in_two_days]}):
        data = get_board()

    assert len(data["days"]) == 2
    assert data["days"][0]["date"] < data["days"][1]["date"]


def test_the_first_day_is_labelled_in_words_not_a_date():
    with board_with({"nfl": [game("1", "nfl", hours=2)]}, {}):
        data = get_board()
    assert data["days"][0]["label"] in ("Today", "Tomorrow")


def test_a_game_listed_by_both_feeds_appears_once():
    """
    Today's board and the schedule endpoint overlap. The scoreboard entry wins
    because it carries the score and clock the schedule does not.
    """
    same = game("1", "nfl")
    with board_with({"nfl": [same]}, {"nfl": [same]}):
        data = get_board()
    assert data["total_games"] == 1


def test_finished_games_from_earlier_days_do_not_clutter_the_board():
    old = game("1", "nfl", state="post", hours=-72)
    with board_with({"nfl": [old, game("2", "nfl")]}, {}):
        data = get_board()
    ids = {g["game"]["event_id"] for d in data["days"] for g in d["games"]}
    assert ids == {"2"}


def test_each_day_reports_how_many_games_each_league_has():
    with board_with({"nfl": [game("1", "nfl")],
                     "ncaaf": [game("2", "ncaaf"), game("3", "ncaaf")]}, {}):
        data = get_board()
    counts = data["days"][0]["by_league"]
    assert counts["nfl"] == 1
    assert counts["ncaaf"] == 2


def test_beyond_the_projection_cap_games_are_still_listed():
    """A schedule that silently stops is not a schedule."""
    many = [game(str(i), "ncaaf", hours=5) for i in range(pred.BOARD_MAX_PREDICTED + 12)]
    with board_with({"ncaaf": many}, {}):
        data = get_board()

    assert data["total_games"] == len(many)
    assert data["predicted"] == pred.BOARD_MAX_PREDICTED
    unprojected = [g for d in data["days"] for g in d["games"] if not g["projected"]]
    assert len(unprojected) == 12
