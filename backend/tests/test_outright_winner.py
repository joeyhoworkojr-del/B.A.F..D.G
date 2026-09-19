"""
Who wins the game, as distinct from who covers.

The board answered the spread and the total and left the plainest question
unanswered. The two are genuinely different questions and they disagree often:
a nine-point favourite the model makes seven still wins the game, while the
spread pick is the underdog. Naming only the cover leaves that unsaid.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes import predictions as pred
from src.ingest.espn import LiveGame

client = TestClient(app)


def game(**kw) -> LiveGame:
    base = dict(
        league="nfl", event_id="1", home="Chiefs", away="Ravens",
        home_abbr="KC", away_abbr="BAL", home_score=None, away_score=None,
        state="pre", detail="", kickoff="2026-09-20T17:00Z",
    )
    base.update(kw)
    return LiveGame(**base)


def test_it_names_the_team_not_a_side():
    """"home" is an implementation detail; a reader wants a team."""
    w = pred._winner_read(game(), 0.63, model_home_prob=0.66)
    assert w["team"] == "Chiefs"
    assert w["opponent"] == "Ravens"
    assert w["abbr"] == "KC"
    assert w["side"] == "home"


def test_the_underdog_can_be_the_outright_pick():
    w = pred._winner_read(game(), 0.42, model_home_prob=0.40)
    assert w["team"] == "Ravens"
    assert w["win_prob"] == 0.58


def test_the_probability_belongs_to_the_named_team():
    # Not the home team's probability with a different name attached to it.
    home = pred._winner_read(game(), 0.71, model_home_prob=0.71)
    away = pred._winner_read(game(), 0.29, model_home_prob=0.29)
    assert home["win_prob"] == 0.71
    assert away["win_prob"] == 0.71
    assert home["team"] != away["team"]


def test_it_says_when_the_market_has_the_other_team():
    """
    The case worth showing. The market makes the home side a nine-point
    favourite; the model still takes the road team to win the game. Saying so
    is the whole point of the field.
    """
    w = pred._winner_read(game(market_spread=-9.0), 0.44, model_home_prob=0.41)
    assert w["team"] == "Ravens"
    assert w["market_agrees"] is False
    # Converted from the spread, not a price anyone quoted — and flagged.
    assert w["market_prob_is_implied"] is True


def test_a_quoted_moneyline_is_not_labelled_as_implied():
    w = pred._winner_read(
        game(market_home_ml=-180, market_away_ml=155), 0.66, model_home_prob=0.70,
    )
    assert w["market_prob_is_implied"] is False
    assert w["price_american"] == -180
    assert w["market_agrees"] is True


def test_the_price_shown_is_the_price_for_the_team_named():
    w = pred._winner_read(
        game(market_home_ml=-180, market_away_ml=155), 0.38, model_home_prob=0.35,
    )
    assert w["team"] == "Ravens"
    assert w["price_american"] == 155      # the away price, not the home one


def test_no_market_at_all_is_not_an_agreement():
    w = pred._winner_read(game(), 0.61, model_home_prob=0.61)
    assert w["market_agrees"] is None
    assert w["market_prob"] is None
    assert w["price_american"] is None


def test_a_finished_game_gets_no_projected_winner():
    """
    By full time the winner is a fact. Presenting one as a projection would be
    manufacturing a track record out of a result already on the scoreboard.
    """
    assert pred._winner_read(game(state="post", home_score=27, away_score=20), 0.9) is None


def test_a_coin_flip_is_called_a_coin_flip():
    assert pred._winner_read(game(), 0.51)["band"] == "toss-up"
    assert pred._winner_read(game(), 0.58)["band"] == "lean"
    assert pred._winner_read(game(), 0.66)["band"] == "clear"
    assert pred._winner_read(game(), 0.88)["band"] == "strong"


def test_a_live_call_is_marked_live_and_ungraded():
    w = pred._winner_read(
        game(state="in", home_score=21, away_score=3), 0.87, live=True,
    )
    assert w["live"] is True
    # Live probabilities are recalculated from the score and clock, never
    # snapshotted. They are no part of the record and must not look like it.
    assert w["graded"] is False
    assert w["model_prob"] is None


def test_a_pregame_call_keeps_the_raw_model_beside_the_anchored_one():
    w = pred._winner_read(game(), 0.63, model_home_prob=0.70)
    assert w["win_prob"] == 0.63     # market-anchored, as the headline
    assert w["model_prob"] == 0.70   # the model on its own


# ─── End to end, on the board the page actually reads ────────────────────────

def test_the_board_carries_a_winner_for_every_projected_game():
    """
    Runs the real model, not a stub: the board fixture in test_board patches
    `_slate_entry` out, which is exactly the thing under test here.
    """
    from datetime import datetime, timedelta, timezone
    from unittest.mock import patch

    from src.ingest.espn import Scoreboard

    kick = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
    slate = [
        game(event_id="1", home_abbr="KC", away_abbr="BAL", kickoff=kick,
             market_home_ml=-180, market_away_ml=155, market_spread=-3.5),
        game(event_id="2", home="49ers", away="Seahawks",
             home_abbr="SF", away_abbr="SEA", kickoff=kick, market_spread=-9.0),
    ]

    async def scoreboard(league):
        return Scoreboard(league=league, games=[], fetched_at="now", ok=True)

    async def upcoming(league, days=7):
        return Scoreboard(league=league, games=slate if league == "nfl" else [],
                          fetched_at="now", ok=True)

    async def markets(league):
        return []

    with patch.multiple(pred, fetch_scoreboard=scoreboard, fetch_upcoming=upcoming,
                        fetch_league_markets=markets):
        data = client.get("/api/v1/board?days=3").json()

    projected = [
        e for d in data["days"] for e in d["games"] if e.get("projected")
    ]
    assert len(projected) == 2, data

    for entry in projected:
        winner = (entry["model"] or {}).get("winner")
        assert winner, f"no outright winner on {entry['game']['event_id']}"
        # The named team is one of the two playing, and the probability is the
        # one belonging to it.
        assert winner["team"] in (entry["game"]["home"], entry["game"]["away"])
        assert winner["opponent"] in (entry["game"]["home"], entry["game"]["away"])
        assert winner["team"] != winner["opponent"]
        assert 0.5 <= winner["win_prob"] <= 1.0


def test_the_outright_call_is_not_just_the_spread_pick_renamed():
    """
    The two answer different questions, so the field earns its place only if it
    can differ. With a big spread and a model that shades the favourite, the
    cover and the outright winner come apart.
    """
    g = game(market_spread=-9.0, market_home_ml=-400, market_away_ml=320)
    # Model has the home side winning the game, but not by nine.
    winner = pred._winner_read(g, 0.68, model_home_prob=0.68)
    assert winner["team"] == "Chiefs"

    # And the reverse: a game the model expects the road team to win outright
    # while the market lays points on the home side.
    upset = pred._winner_read(g, 0.46, model_home_prob=0.44)
    assert upset["team"] == "Ravens"
    assert upset["market_agrees"] is False
