"""
The fair line, the value on it, and the reasons behind it.

The product's whole claim is "the market is wrong here, by this much". That
needs three numbers side by side — what StatEdge thinks the line should be,
what the book is offering, and the gap — and it needs the gap to be signed the
right way round, because the model and a sportsbook quote the same fact with
opposite signs. Getting that wrong inverts every recommendation on the board.
"""
from __future__ import annotations

import asyncio

import pytest

from src.api.routes import predictions as pred
from src.ingest.espn import LiveGame
from src.predict import priors


def game(**kw) -> LiveGame:
    base = dict(
        league="nfl", event_id="1", home="Buffalo Bills", away="Miami Dolphins",
        home_abbr="BUF", away_abbr="MIA", home_score=None, away_score=None,
        state="pre", detail="", kickoff="2026-10-04T17:00Z",
    )
    base.update(kw)
    return LiveGame(**base)


class FakePred:
    """Only the fields the fair-line read actually looks at."""
    def __init__(self, margin, total):
        self.predicted_spread = margin      # positive = home favoured
        self.total_points_estimate = total
        self.conditions = []


# ─── The sign convention, which is the whole risk here ───────────────────────

def test_a_model_margin_becomes_a_sportsbook_line():
    """
    The model says "home by 4.8". A book says "home -4.8". Same fact, opposite
    sign, and conflating them would publish every line backwards.
    """
    read = pred._spread_read(game(market_spread=-3.5), FakePred(4.8, 46.5), "BUF", "MIA")
    assert read["fair"] == -4.8
    assert read["fair_label"] == "BUF -4.8"


def test_value_on_the_favourite_is_reported_as_such():
    # Market lays 3.5, StatEdge would lay 4.8 → the favourite is underpriced.
    read = pred._spread_read(game(market_spread=-3.5), FakePred(4.8, 46.5), "BUF", "MIA")
    assert read["edge_points"] == 1.3
    assert read["side"] == "home"
    assert read["side_abbr"] == "BUF"
    assert read["points"] == 1.3


def test_value_on_the_underdog_is_reported_as_such():
    # Market lays 6, StatEdge would only lay 4.8 → the dog is getting too many.
    read = pred._spread_read(game(market_spread=-6.0), FakePred(4.8, 46.5), "BUF", "MIA")
    assert read["edge_points"] == -1.2
    assert read["side"] == "away"
    assert read["side_abbr"] == "MIA"
    assert read["points"] == 1.2


def test_an_away_favourite_is_labelled_with_the_away_team():
    read = pred._spread_read(game(market_spread=3.0), FakePred(-2.5, 44.0), "BUF", "MIA")
    assert read["fair_label"] == "MIA -2.5"
    assert read["market_label"] == "MIA -3.0"


def test_agreement_is_not_dressed_up_as_an_edge():
    read = pred._spread_read(game(market_spread=-4.8), FakePred(4.8, 46.5), "BUF", "MIA")
    assert read["edge_points"] == 0.0
    assert read["side"] is None
    assert read["points"] is None


def test_no_published_line_means_no_edge_rather_than_a_guess():
    read = pred._spread_read(game(), FakePred(4.8, 46.5), "BUF", "MIA")
    assert read["market"] is None
    assert read["edge_points"] is None
    assert read["side"] is None


def test_the_total_sign_is_the_plain_one():
    over = pred._total_read(game(market_over_under=46.5), FakePred(4.8, 48.3))
    assert over["edge_points"] == 1.8 and over["side"] == "over"

    under = pred._total_read(game(market_over_under=46.5), FakePred(4.8, 43.9))
    assert under["edge_points"] == -2.6 and under["side"] == "under"


# ─── Probability, break-even, EV and confidence are four things ──────────────

def test_break_even_is_a_property_of_the_price_not_the_model():
    # -110 needs 52.4% to break even whatever the model thinks.
    a = pred._selection(label="x", side="home", model_prob=0.90, model_prob_raw=0.90,
                        book_prob=0.5, price_american=-110)
    b = pred._selection(label="x", side="home", model_prob=0.10, model_prob_raw=0.10,
                        book_prob=0.5, price_american=-110)
    assert a["break_even_prob"] == b["break_even_prob"]
    assert round(a["break_even_prob"], 3) == 0.524


def test_a_model_probability_above_break_even_is_positive_ev():
    sel = pred._selection(label="x", side="home", model_prob=0.568, model_prob_raw=0.568,
                          book_prob=0.524, price_american=-110)
    assert sel["break_even_prob"] < sel["model_prob"]
    assert sel["ev_per_unit"] > 0


def test_a_model_probability_below_break_even_is_negative_ev():
    sel = pred._selection(label="x", side="home", model_prob=0.50, model_prob_raw=0.50,
                          book_prob=0.524, price_american=-110)
    assert sel["ev_per_unit"] < 0


def test_confidence_measures_inputs_not_likelihood():
    """
    The single most misleading thing this page could do is let "high
    confidence" read as "high chance of winning". Confidence here is input
    coverage, so two games with wildly different probabilities and identical
    inputs must come out the same.
    """
    priors.reset()
    lopsided = asyncio.run(pred._slate_entry("nfl", game(
        market_spread=-14.0, market_over_under=46.5,
        market_home_ml=-800, market_away_ml=550, market_provider="ESPN BET",
    ), []))
    coinflip = asyncio.run(pred._slate_entry("nfl", game(
        market_spread=-1.0, market_over_under=46.5,
        market_home_ml=-110, market_away_ml=-110, market_provider="ESPN BET",
    ), []))

    assert (lopsided["value"]["confidence"]["level"]
            == coinflip["value"]["confidence"]["level"])
    assert "Not the chance a bet wins" in lopsided["value"]["confidence"]["means"]


def test_every_confidence_input_is_named_and_auditable():
    priors.reset()
    entry = asyncio.run(pred._slate_entry("nfl", game(market_spread=-3.5), []))
    conf = entry["value"]["confidence"]
    assert conf["inputs"], "a bare level with nothing behind it is not auditable"
    for item in conf["inputs"]:
        assert item["name"] and isinstance(item["present"], bool) and item["note"]


# ─── Why, and the refusal to invent a reason ─────────────────────────────────

def seed_priors():
    priors._priors["nfl"] = priors.LeaguePriors(
        league="nfl", ok=True, source="nflverse-epa", fetched_at="now",
        teams={
            c: priors.TeamPrior(code=c, points=p, games=5, source="nflverse-epa")
            for c, p in (("BUF", 6.1), ("MIA", -2.3), ("KC", 5.0), ("NE", -4.0))
        },
    )


def test_the_reasons_are_the_inputs_the_model_actually_read():
    seed_priors()
    entry = asyncio.run(pred._slate_entry("nfl", game(
        market_spread=-3.5, market_over_under=46.5,
    ), []))
    labels = [r["label"] for r in entry["why"]["reasons"]]
    # Of BUF 6.1, KC 5.0, MIA -2.3, NE -4.0 — so MIA is third, not last.
    assert any("BUF rated 1st of 4" in l for l in labels)
    assert any("MIA rated 3rd of 4" in l for l in labels)
    assert any("toward the market price" in l for l in labels)
    # The rank has to carry its own evidence, not just an ordinal.
    ratings = [r for r in entry["why"]["reasons"] if r["source"] == "ratings"]
    assert all("points per game" in r["detail"] for r in ratings)
    assert all("nflverse-epa" in r["detail"] for r in ratings)


def test_a_missing_feed_is_listed_as_missing_not_left_out():
    """
    A short, honest list beats a plausible fabrication. Dropping the row
    entirely would let a reader assume ratings were considered.
    """
    priors.reset()
    entry = asyncio.run(pred._slate_entry("ncaaf", game(
        league="ncaaf", home="Alabama Crimson Tide", away="Auburn Tigers",
        home_abbr="ALA", away_abbr="AUB", market_spread=-7.0,
    ), []))
    reasons = entry["why"]["reasons"]
    missing = [r for r in reasons if r["source"] == "missing"]
    assert missing, [r["label"] for r in reasons]
    assert "CFBD_API_KEY" in missing[0]["detail"]


def test_a_surviving_edge_and_a_vanished_one_read_differently():
    survived = pred._line_state(-2.5, {"market": -3.5, "edge_points": 1.3, "side_abbr": "BUF"})
    assert survived["state"] == "value"
    assert survived["moved_points"] == -1.0
    assert "StatEdge still has 1.3 points on BUF" in survived["note"]

    gone = pred._line_state(-2.5, {"market": -4.6, "edge_points": 0.2, "side_abbr": "BUF"})
    assert gone["state"] == "gone"
    assert "caught up" in gone["note"]


def test_no_line_at_all_is_not_called_an_edge_or_a_loss_of_one():
    nothing = pred._line_state(None, {"market": None, "edge_points": None})
    assert nothing["state"] == "unknown"
    assert "nothing to compare" in nothing["note"]
