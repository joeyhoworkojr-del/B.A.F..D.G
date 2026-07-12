"""Value engine tests — odds conversion, vig removal, EV, Kelly."""
from __future__ import annotations

import pytest

from src.value.edge import (
    american_to_decimal,
    decimal_to_american,
    edge_rating,
    evaluate_market,
    expected_value,
    implied_probability,
    kelly_fraction,
    overround,
    remove_vig,
)


def test_american_decimal_roundtrip() -> None:
    assert abs(american_to_decimal(+150) - 2.50) < 1e-9
    assert abs(american_to_decimal(-200) - 1.50) < 1e-9
    assert abs(decimal_to_american(2.50) - 150) < 1e-9
    assert abs(decimal_to_american(1.50) - (-200)) < 1e-9


def test_implied_probability() -> None:
    assert abs(implied_probability(2.0) - 0.5) < 1e-12
    assert abs(implied_probability(4.0) - 0.25) < 1e-12


def test_remove_vig_sums_to_one() -> None:
    fair = remove_vig([0.55, 0.30, 0.20])   # 5% overround book
    assert abs(sum(fair) - 1.0) < 1e-12
    assert fair[0] > fair[1] > fair[2]      # order preserved


def test_overround_typical_book() -> None:
    assert abs(overround([0.55, 0.50]) - 0.05) < 1e-12


def test_expected_value_signs() -> None:
    # True prob 55% at even money → positive EV
    assert expected_value(0.55, 2.0) > 0
    # True prob 45% at even money → negative EV
    assert expected_value(0.45, 2.0) < 0


def test_kelly_never_negative() -> None:
    assert kelly_fraction(0.30, 2.0) == 0.0
    assert kelly_fraction(0.60, 2.0) > 0.0


def test_kelly_quarter_scaling() -> None:
    full = kelly_fraction(0.60, 2.0, fraction=1.0)
    quarter = kelly_fraction(0.60, 2.0, fraction=0.25)
    assert abs(quarter - full / 4) < 1e-12


def test_edge_rating_buckets() -> None:
    assert edge_rating(7.0) == "A"
    assert edge_rating(4.0) == "B"
    assert edge_rating(2.0) == "C"
    assert edge_rating(0.5) == "-"


def test_evaluate_market_finds_the_value_side() -> None:
    # Model: 60/40. Book prices both at 1.95 (even-ish with vig).
    edges = evaluate_market(
        "Total 2.5",
        [("Over 2.5", 0.60, 1.95), ("Under 2.5", 0.40, 1.95)],
    )
    assert edges[0].selection == "Over 2.5"
    assert edges[0].edge_pp > 5
    assert edges[0].ev_per_unit > 0
    assert edges[0].kelly_stake > 0
    assert edges[1].ev_per_unit < 0


def test_evaluate_market_skips_unpriced() -> None:
    edges = evaluate_market("1X2", [("Home", 0.5, None), ("Draw", 0.3, None), ("Away", 0.2, None)])
    assert edges == []


def test_invalid_odds_raise() -> None:
    with pytest.raises(ValueError):
        implied_probability(0.9)
    with pytest.raises(ValueError):
        american_to_decimal(0)


def test_debias_shrinks_overconfidence_toward_coinflip() -> None:
    """Edge detection must not fade the crowd off raw over-confidence: shrinking
    toward 50% keeps direction, halves-ish marginal edges, keeps strong ones."""
    from src.api.routes.predictions import _debias, EDGE_CONFIDENCE_SHRINK

    assert _debias(0.5) == 0.5                       # a coin flip stays a coin flip
    assert abs(_debias(0.70) - (0.5 + EDGE_CONFIDENCE_SHRINK * 0.20)) < 1e-9
    # Always pulled toward 50%, never past it, direction preserved.
    for p in (0.55, 0.62, 0.80, 0.95):
        assert 0.5 < _debias(p) < p
        assert abs(_debias(1 - p) - (1 - _debias(p))) < 1e-12   # symmetric
    # A marginal 3pp raw lean vs the market shrinks below the C bar (1.5pp);
    # a strong 12pp raw lean still clears the A bar (6pp) — still "gets upset."
    market = 0.55
    assert (_debias(0.58) - market) * 100 < 1.5
    assert (_debias(0.67) - market) * 100 >= 6.0
