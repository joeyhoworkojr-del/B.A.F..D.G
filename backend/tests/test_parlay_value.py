"""
Parlay construction.

The ticket was built from the legs with the biggest probability gap, which
ignores what each leg pays. For independent legs the ticket's return is the
product of each leg's price times its probability, so the highest-EV legs give
the highest-EV ticket — arithmetic, not taste. Ranking by the gap could and did
put a negative-EV leg above a positive-EV one.
"""
from __future__ import annotations

import pytest

from src.api.routes.predictions import _price_ticket, PARLAY_LEG_COUNTS
from src.api.schemas import ParlayLeg


def leg(name, model_prob, market_prob, decimal):
    return ParlayLeg(
        fixture_id=f"nfl:{name}", league="nfl", kickoff="2026-10-05T17:00Z",
        home="H", away="A", market="NFL · Spread", selection=name,
        model_prob=model_prob, market_prob=market_prob, decimal_odds=decimal,
        edge_pp=round((model_prob - market_prob) * 100, 1), rating="A",
        ev_per_unit=round(model_prob * decimal - 1.0, 4),
        break_even_prob=round(1.0 / decimal, 4),
    )


def test_the_two_rankings_genuinely_disagree():
    """
    The case the change exists for. A wide gap at a terrible price is worse
    than a narrow gap at a fair one, and sorting by the gap gets it backwards.
    """
    wide_gap_bad_price = leg("A", 0.80, 0.70, 1.20)
    narrow_gap_fair_price = leg("B", 0.55, 0.52, 1.95)

    assert wide_gap_bad_price.edge_pp > narrow_gap_fair_price.edge_pp
    assert wide_gap_bad_price.ev_per_unit < 0 < narrow_gap_fair_price.ev_per_unit


def test_a_leg_carries_its_own_ev_and_break_even():
    one = leg("A", 0.585, 0.50, 1.909)
    assert one.ev_per_unit == pytest.approx(0.117, abs=0.001)
    assert one.break_even_prob == pytest.approx(0.524, abs=0.001)


# ─── Pricing a ticket ────────────────────────────────────────────────────────

def minus_110(name, model_prob):
    """A -110 side: 1.909 to win, 0.50 once the vig is removed."""
    return leg(name, model_prob, 0.50, 1.909)


def test_the_combined_price_and_probability_are_the_products():
    legs = [minus_110("A", 0.60), minus_110("B", 0.55)]
    t = _price_ticket(legs)
    assert t.decimal_odds == pytest.approx(1.909 * 1.909, abs=0.01)
    assert t.model_prob == pytest.approx(0.60 * 0.55, abs=0.001)
    assert t.implied_prob == pytest.approx(1 / (1.909 ** 2), abs=0.001)


def test_the_book_hold_compounds_with_every_leg_added():
    """
    The most important thing about the format, and the thing a parlay page
    usually hides inside a big American number.
    """
    legs = [minus_110(n, 0.57) for n in "ABCD"]
    holds = [_price_ticket(legs[:n]).vig_pct for n in (1, 2, 3, 4)]

    assert holds == sorted(holds), holds
    assert holds[0] == pytest.approx(4.5, abs=0.2)
    assert holds[3] > 15.0, "four -110 legs keep well over four times one leg"


def test_each_ticket_shows_the_fair_price_its_own_legs_imply():
    t = _price_ticket([minus_110("A", 0.57), minus_110("B", 0.57)])
    # Two 50% legs are fairly priced at 4.0; the book offers less.
    assert t.fair_decimal_odds == pytest.approx(4.0, abs=0.01)
    assert t.decimal_odds < t.fair_decimal_odds


def test_a_ticket_of_positive_ev_legs_is_positive_ev():
    legs = [minus_110("A", 0.585), minus_110("B", 0.57)]
    assert all(l.ev_per_unit > 0 for l in legs)
    assert _price_ticket(legs).ev_per_unit > 0


def test_adding_a_leg_buys_price_and_costs_probability():
    legs = [minus_110(n, 0.57) for n in "ABCD"]
    two, four = _price_ticket(legs[:2]), _price_ticket(legs[:4])
    assert four.decimal_odds > two.decimal_odds
    assert four.model_prob < two.model_prob
    assert four.payout_per_unit > two.payout_per_unit


def test_a_leg_with_no_fair_price_does_not_break_the_hold_figure():
    # market_prob of 0 would divide by zero; it has to be survivable.
    odd = leg("A", 0.6, 0.0, 1.9)
    t = _price_ticket([odd, minus_110("B", 0.57)])
    assert t.vig_pct >= 0.0
    assert t.decimal_odds > 1.0


def test_the_offered_leg_counts_are_sane():
    assert PARLAY_LEG_COUNTS == (2, 3, 4)
