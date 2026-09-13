"""
Live picks, and the stale-line trap they are built around.

A sportsbook feed does not necessarily reprice in play. If the posted moneyline
is still the pre-game one while a team is three scores down, comparing a live
model against it manufactures an enormous edge out of nothing but an old
number — and it would look like the best pick on the board.

So an edge is only claimed when the book has demonstrably followed the game.
Everything else here is about refusing to claim one.
"""
from __future__ import annotations

from src.api.routes.predictions import (
    LIVE_MIN_EDGE_PP, LIVE_PICKS_GRADED, _live_read,
)
from src.ingest.espn import LiveGame

# Pre-game: the book and the model both had the home side at 64%.
PREGAME = {"book_home_prob": 0.64, "model_home_prob": 0.64}


def game(home_ml=None, away_ml=None, spread=None, home_score=7, away_score=28):
    return LiveGame(
        league="nfl", event_id="1", home="Chiefs", away="Ravens",
        home_abbr="KC", away_abbr="BAL",
        home_score=home_score, away_score=away_score,
        state="in", detail="Q3 6:59", kickoff="2026-09-13T17:00:00Z",
        market_home_ml=home_ml, market_away_ml=away_ml, market_spread=spread,
    )


def test_a_stale_pre_game_line_is_not_treated_as_a_live_market():
    """
    The one that matters. The home side is down three scores and the feed is
    still publishing -180. Reading that as a fifty-point edge would put a
    fabricated pick at the top of the board.
    """
    read = _live_read(game(-180, 150), live_home_win=0.12, snapshot=PREGAME)

    assert read["market_repriced"] is False
    assert read["actionable"] is False
    assert "has barely moved since kickoff" in read["note"]


def test_a_book_that_followed_the_game_counts_as_live():
    read = _live_read(game(600, -900), live_home_win=0.12, snapshot=PREGAME)

    assert read["market_repriced"] is True
    # Both numbers are published so the claim can be checked rather than
    # taken on trust.
    assert read["model_move_pp"] > 40
    assert read["market_move_pp"] > 40


def test_a_repriced_book_the_model_agrees_with_is_not_a_pick():
    read = _live_read(game(600, -900), live_home_win=0.12, snapshot=PREGAME)
    assert read["edge_pp"] < LIVE_MIN_EDGE_PP
    assert read["actionable"] is False


def test_a_live_market_the_model_disagrees_with_is_a_pick():
    """
    The book has swung hard to the away side after a score; the model has moved
    too, but nothing like as far, and still rates the home side a coin flip.
    That gap is the pick — and it only counts because the book demonstrably
    moved with the game.
    """
    # Home priced around 24% by the book; the model still has it at 50%.
    read = _live_read(game(300, -400), live_home_win=0.50, snapshot=PREGAME)

    assert read["market_repriced"] is True
    assert read["side"] == "home"
    assert read["edge_pp"] >= LIVE_MIN_EDGE_PP
    assert read["actionable"] is True


def test_no_pre_game_snapshot_means_no_claim():
    # Without a frozen pre-game price there is nothing to establish whether the
    # book has repriced. Unknown is not "yes".
    read = _live_read(game(-180, 150), live_home_win=0.12, snapshot=None)
    assert read["market_repriced"] is False
    assert read["actionable"] is False


def test_no_posted_price_at_all_produces_nothing():
    assert _live_read(game(), live_home_win=0.12, snapshot=PREGAME) is None


def test_a_game_that_has_barely_moved_claims_nothing():
    # Early on, nothing has happened for the book to have followed.
    read = _live_read(
        game(-180, 150, home_score=0, away_score=0), live_home_win=0.63,
        snapshot=PREGAME,
    )
    assert read["market_repriced"] is False


def test_every_live_read_says_it_is_not_graded():
    """
    In-game probabilities are recalculated from the score and clock. They are
    never snapshotted and never graded, so they are no part of the track
    record — and a section of live picks must not be read as if they were.
    """
    read = _live_read(game(600, -900), live_home_win=0.12, snapshot=PREGAME)
    assert read["graded"] is LIVE_PICKS_GRADED is False


def test_the_side_named_is_the_side_the_model_favours():
    read = _live_read(game(600, -900), live_home_win=0.12, snapshot=PREGAME)
    assert read["side"] == "away" and read["team"] == "BAL"

    read = _live_read(game(-900, 600), live_home_win=0.88, snapshot=PREGAME)
    assert read["side"] == "home" and read["team"] == "KC"
