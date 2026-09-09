"""
Which markets the Edges board is allowed to pick from.

Taking a game's two highest edges overall meant one market could crowd the
others out: a game whose loudest disagreements were both totals never surfaced
its moneyline, however good that was. Someone shopping a spread wants the
spread pick, not whichever market happened to disagree hardest.
"""
from __future__ import annotations

from src.api.routes.predictions import MARKET_KINDS, _best_per_market, _market_kind


def _edge(market: str, selection: str, rating: str, edge_pp: float) -> dict:
    return {"market": market, "selection": selection,
            "rating": rating, "edge_pp": edge_pp}


def test_each_bettable_market_is_recognised_from_its_label():
    assert _market_kind("Moneyline (live)") == "moneyline"
    assert _market_kind("Spread -3.5 (−110 assumed)") == "spread"
    assert _market_kind("Total 52.5 (−110 assumed)") == "total"


def test_a_crowd_signal_is_not_offered_as_a_bet():
    # Polymarket is a comparison, not a market you can take a price in at a
    # sportsbook. It used to outrank real markets purely on edge size.
    assert _market_kind("Polymarket crowd") not in MARKET_KINDS


def test_a_loud_total_no_longer_crowds_out_the_moneyline_and_spread():
    edges = [
        _edge("Polymarket crowd", "FSU vs crowd", "A", 20.0),
        _edge("Total 52.5", "Over 52.5", "A", 9.0),
        _edge("Spread -3.5", "FSU -3.5", "A", 6.0),
        _edge("Moneyline (live)", "FSU ML", "B", 4.0),
    ]
    picked = _best_per_market(edges)

    assert [p["selection"] for p in picked] == ["FSU ML", "FSU -3.5", "Over 52.5"]
    assert {_market_kind(p["market"]) for p in picked} == set(MARKET_KINDS)


def test_only_the_strongest_selection_in_a_market_is_taken():
    # Both sides of a market can qualify; offering both would be offering a
    # bet and its opposite in the same breath.
    edges = [
        _edge("Total 52.5", "Over 52.5", "A", 9.0),
        _edge("Total 52.5", "Under 52.5", "B", 4.0),
    ]
    picked = _best_per_market(edges)

    assert len(picked) == 1
    assert picked[0]["selection"] == "Over 52.5"


def test_a_market_with_nothing_worth_saying_is_simply_absent():
    edges = [
        _edge("Moneyline (live)", "FSU ML", "C", 2.0),   # below the A/B bar
        _edge("Spread -3.5", "FSU -3.5", "-", 0.2),
        _edge("Total 52.5", "Over 52.5", "A", 7.0),
    ]
    picked = _best_per_market(edges)

    assert [p["selection"] for p in picked] == ["Over 52.5"]


def test_no_qualifying_edge_produces_no_picks_rather_than_a_filler_one():
    edges = [_edge("Moneyline (live)", "FSU ML", "C", 2.0)]
    assert _best_per_market(edges) == []
