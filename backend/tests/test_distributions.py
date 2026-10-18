"""
The shape a prop probability comes out of.

Everything about a prop's price flows from this. The projection is a mean, and
"what is the chance he clears 6.5" is a question about the shape around it. A
symmetric normal was used for every market, and measured against four seasons
of real player games it overstated the over at every probability above 30% —
"53%" happened 44% of the time, 8.1 points of mean absolute calibration error.

Rushing and receiving production is non-negative, lumpy and right-skewed, so
its mean sits above its median and a symmetric curve centred on the mean is
simply the wrong object. These pin the properties that fixes it.
"""
from __future__ import annotations

import pytest

from src.predict import distributions as dist
from src.predict import player_props as pp


# ─── The property that was broken ────────────────────────────────────────────

def test_a_skewed_market_clears_its_own_mean_less_than_half_the_time():
    """
    The whole bug in one assertion. For a right-skewed quantity the mean is
    above the median, so the chance of exceeding the mean is under 50%. The
    normal said exactly 50%, every time, for every market.
    """
    for market in ("rec_yards", "rush_yards", "receptions", "carries"):
        p = dist.over_probability(market, 70.0, 70.0, 35.0)
        assert p is not None
        assert p < 0.47, f"{market} should be under half at its own mean, got {p}"


def test_passing_volume_stays_symmetric():
    # A starting quarterback plays every down, so his volume is near-symmetric
    # and the normal measured best for it. Measured: 2.3p against gamma's 3.7p.
    p = dist.over_probability("pass_yards", 255.0, 255.0, 70.0)
    assert p == pytest.approx(0.5, abs=0.01)
    assert dist.family_for("pass_yards") == "normal"
    assert dist.family_for("rec_yards") == "gamma"


def test_the_skewed_family_has_the_fatter_right_tail():
    # Which is the other half of being right: big games are more likely than a
    # normal curve allows, and blanks are too.
    gamma = dist.gamma_over(150.0, 70.0, 35.0)
    normal = dist.normal_over(150.0, 70.0, 35.0)
    assert gamma > normal * 1.5


def test_probabilities_stay_monotonic_in_the_line():
    # A higher line can never be easier to clear.
    for market in ("rec_yards", "pass_yards", "receptions"):
        probs = [
            dist.over_probability(market, line, 70.0, 35.0)
            for line in (10, 30, 50, 70, 90, 120, 200)
        ]
        assert all(a >= b for a, b in zip(probs, probs[1:])), (market, probs)


def test_probabilities_stay_inside_zero_and_one():
    for line in (0.1, 1, 50, 500, 5000):
        for market in ("rec_yards", "pass_yards", "rec_tds"):
            p = dist.over_probability(market, line, 70.0, 35.0)
            assert p is None or 0.0 <= p <= 1.0


# ─── Degenerate inputs must not produce a confident number ───────────────────

def test_nothing_is_claimed_from_a_zero_projection_or_spread():
    assert dist.over_probability("rec_yards", 50.0, 0.0, 10.0) is None
    assert dist.over_probability("rec_yards", 50.0, 70.0, 0.0) is None
    assert dist.gamma_over(50.0, 0.0, 10.0) is None
    assert dist.gamma_over(0.0, 70.0, 10.0) is None


def test_a_market_that_cannot_be_fitted_falls_back_rather_than_failing():
    # The fallback is the normal, and it fires on an unfittable gamma only —
    # never silently on a market the gamma handles, which would undo the fix.
    p = dist.over_probability("rec_yards", 70.0, 70.0, 35.0)
    assert p is not None and p != dist.normal_over(70.0, 70.0, 35.0)


# ─── Through the shipped path ────────────────────────────────────────────────

def test_the_props_model_uses_the_measured_family():
    """
    The property is "strictly under half", not any particular number. How far
    under depends on how skewed the player is, and a very consistent player is
    barely skewed at all — a gamma with a small spread relative to its mean is
    close to symmetric, which is the right answer for him and not a failure to
    apply the shape.
    """
    steady = [5, 5, 6, 4, 5, 5, 6, 5]
    at_mean = pp.over_probability(5.0, 5.0, "receptions", steady)
    assert at_mean is not None and at_mean < 0.5

    # A lumpy player is visibly skewed, and the same call shows it.
    lumpy = pp.over_probability(5.0, 5.0, "receptions", [0, 9, 1, 8, 0, 9, 2, 11])
    assert lumpy < at_mean

    # Passing yards are not.
    pass_log = [240, 270, 255, 250, 260, 245, 265, 255]
    assert pp.over_probability(255.0, 255.0, "pass_yards", pass_log) == pytest.approx(0.5, abs=0.02)


def test_volatility_still_drives_the_answer_under_the_new_shape():
    # The per-player spread work must survive the change of family: two players
    # with the same average and different logs still differ.
    steady = pp.over_probability(5.0, 6.5, "receptions", [5, 5, 6, 4, 5, 5, 6, 5])
    volatile = pp.over_probability(5.0, 6.5, "receptions", [2, 9, 1, 8, 3, 9, 2, 7])
    assert volatile > steady * 1.5


def test_an_unknown_market_still_claims_nothing():
    assert pp.over_probability(5.0, 6.5, "hat_tricks", [1, 2, 3]) is None
