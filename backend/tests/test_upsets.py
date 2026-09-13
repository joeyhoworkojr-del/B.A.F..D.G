"""
When the board is allowed to call an upset.

The risk here is volume, not accuracy: a board that flags every disagreement
with the market flags a fifth of all games and means nothing. The threshold is
fitted so it speaks up about one game in ten.
"""
from __future__ import annotations

from src.api.routes.predictions import (
    UPSET_MIN_DOG_PROB, _upset_read,
)
from src.ingest.espn import LiveGame


def game(spread=None, home_ml=None, away_ml=None):
    return LiveGame(
        league="nfl", event_id="1", home="Chiefs", away="Ravens",
        home_abbr="KC", away_abbr="BAL", home_score=None, away_score=None,
        state="pre", detail="", kickoff="2026-09-16T21:20:00Z",
        market_spread=spread, market_home_ml=home_ml, market_away_ml=away_ml,
    )


def test_agreeing_with_the_market_is_not_an_upset():
    # Market likes the home side; so does the model. Nothing to say.
    assert _upset_read(game(spread=-7.0), home_win_raw=0.80) is None


def test_a_confident_disagreement_is_called():
    # Market has the home side favoured by a touchdown; the model likes the
    # visitor, and by a clear margin.
    read = _upset_read(game(spread=-7.0), home_win_raw=0.25)
    assert read is not None
    assert read["side"] == "away"
    assert read["team"] == "BAL"
    assert read["model_prob"] >= UPSET_MIN_DOG_PROB


def test_a_coin_flip_disagreement_is_not_worth_saying():
    # The model prefers the underdog, but barely. Flagging this is the
    # behaviour that fills a board with noise.
    read = _upset_read(game(spread=-7.0), home_win_raw=0.47)
    assert read is None


def test_the_underdog_can_be_the_home_side():
    read = _upset_read(game(spread=+7.0), home_win_raw=0.75)
    assert read is not None
    assert read["side"] == "home"
    assert read["team"] == "KC"


def test_a_pick_em_has_no_underdog_to_be_wrong_about():
    assert _upset_read(game(spread=0.0), home_win_raw=0.75) is None


def test_no_posted_line_means_no_claim():
    # Without a market there is nothing to disagree with.
    assert _upset_read(game(), home_win_raw=0.95) is None


def test_the_historical_rate_is_reported_apart_from_this_game_s_probability():
    read = _upset_read(game(spread=-7.0), home_win_raw=0.20)
    assert read is not None
    # Two different numbers that must never be conflated: what the model says
    # about this game, and how the rule has done across many.
    assert read["model_prob"] != read["rule_hit_rate"]
    assert read["rule_base_rate"] < read["rule_hit_rate"]


def test_the_threshold_stays_where_it_was_fitted():
    # Measured over 799 games: 0.58 flags ~10% of the slate at a 47% hit rate
    # against a 31.8% base. Loosening it is what makes the board cry upset.
    assert UPSET_MIN_DOG_PROB >= 0.55


# ─── The parlay builds from the week, not from today ──────────────────────────

def test_a_parlay_still_has_legs_once_todays_games_have_kicked_off():
    """
    Saturday evening: today's board is all "in" or "post", and the parlay page
    went blank — even though Sunday's slate was right there. The board had
    already moved to showing a week; this was still reading a day.
    """
    import asyncio
    from unittest.mock import patch

    from src.api.routes import predictions as pred
    from src.ingest.espn import LiveGame, Scoreboard

    def game(i, state, kickoff):
        return LiveGame(
            league="nfl", event_id=f"g{i}", home="Chiefs", away="Ravens",
            home_abbr="KC", away_abbr="BAL",
            home_score=21 if state != "pre" else None,
            away_score=17 if state != "pre" else None,
            state=state, detail="", kickoff=kickoff,
            market_spread=-3.5, market_over_under=47.5,
            market_home_ml=-180, market_away_ml=150,
        )

    async def played_out(league, *_a, **_k):
        return Scoreboard(
            league=league,
            games=[game(i, "post", "2026-09-13T20:00:00Z") for i in range(3)],
            fetched_at="now", ok=True,
        )

    async def week_ahead(league, days=7, *_a, **_k):
        return Scoreboard(
            league=league,
            games=[game(10 + i, "pre", "2026-09-14T20:00:00Z") for i in range(3)],
            fetched_at="now", ok=True,
        )

    async def no_markets(_league, *_a, **_k):
        return []

    async def no_qb(_h, _a):
        return None, None

    with patch.object(pred, "fetch_scoreboard", played_out), \
         patch.object(pred, "fetch_upcoming", week_ahead), \
         patch.object(pred, "fetch_league_markets", no_markets), \
         patch.object(pred.qb_model, "changes_for", no_qb):
        legs = asyncio.run(pred._scan_parlay_legs())

    assert legs, "no legs from a full slate tomorrow"
    # And nothing already played is ever a leg.
    assert all(leg.fixture_id.split(":")[1].startswith("g1") for leg in legs)


def test_a_game_on_both_feeds_is_only_one_leg():
    import asyncio
    from unittest.mock import patch

    from src.api.routes import predictions as pred
    from src.ingest.espn import LiveGame, Scoreboard

    same = LiveGame(
        league="nfl", event_id="dup", home="Chiefs", away="Ravens",
        home_abbr="KC", away_abbr="BAL", home_score=None, away_score=None,
        state="pre", detail="", kickoff="2026-09-14T20:00:00Z",
        market_spread=-3.5, market_over_under=47.5,
        market_home_ml=-180, market_away_ml=150,
    )

    async def both(league, *_a, **_k):
        return Scoreboard(league=league, games=[same], fetched_at="now", ok=True)

    async def no_markets(_league, *_a, **_k):
        return []

    async def no_qb(_h, _a):
        return None, None

    with patch.object(pred, "fetch_scoreboard", both), \
         patch.object(pred, "fetch_upcoming", both), \
         patch.object(pred, "fetch_league_markets", no_markets), \
         patch.object(pred.qb_model, "changes_for", no_qb):
        legs = asyncio.run(pred._scan_parlay_legs())

    assert len(legs) <= 1, "the same game was offered twice"
