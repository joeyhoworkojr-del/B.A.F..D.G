"""NFL expected-points engine tests — margin/total distributions and markets."""
from __future__ import annotations

from src.predict.gridiron import (
    HFA_POINTS,
    cover_probability,
    expected_points,
    predict_nfl_game,
    total_over_probability,
    win_probability,
)
from src.predict.adjustments import Adjustment


def test_win_prob_zero_margin_is_coinflip() -> None:
    assert abs(win_probability(0.0) - 0.5) < 1e-9


def test_win_prob_monotone_in_margin() -> None:
    assert win_probability(7.0) > win_probability(3.0) > win_probability(0.0)


def test_home_field_boosts_expected_points() -> None:
    h_home, a_home = expected_points("KC", "SF", neutral_site=False)
    h_neutral, a_neutral = expected_points("KC", "SF", neutral_site=True)
    assert h_home - a_home > h_neutral - a_neutral
    assert abs((h_home - a_home) - (h_neutral - a_neutral) - HFA_POINTS) < 1e-9


def test_over_under_complement() -> None:
    over = total_over_probability(46.0, 44.5)
    under = 1 - over
    assert over > 0.5           # expectation above the line
    assert abs(over + under - 1.0) < 1e-12


def test_cover_prob_at_model_line_is_half() -> None:
    # Betting the model's own spread should be a coin flip
    assert abs(cover_probability(6.0, -6.0) - 0.5) < 1e-9


def test_predict_game_basic_sanity() -> None:
    p = predict_nfl_game("KC", "CAR", 1720, 1430)
    assert p.home_win_prob > 0.70          # big favourite at home
    assert p.home_win_prob + p.away_win_prob == 1.0
    assert p.predicted_spread > 3
    assert 30 < p.total_points_estimate < 60
    assert abs(p.over_prob + p.under_prob - 1.0) < 1e-9
    assert p.fair_odds["home_ml"] < p.fair_odds["away_ml"]


def test_quoted_total_line_used() -> None:
    p = predict_nfl_game("KC", "SF", 1720, 1680, total_line=99.5)
    assert p.total_line == 99.5
    assert p.over_prob < 0.01      # absurdly high line → basically never over


def test_qb_out_adjustment_moves_probability_and_total() -> None:
    base = predict_nfl_game("KC", "SF", 1720, 1680)
    qb_out = predict_nfl_game(
        "KC", "SF", 1720, 1680,
        adjustments=[Adjustment(
            label="QB out", detail="", source="lineup", home_pts_delta=-6.0,
        )],
    )
    assert qb_out.home_win_prob < base.home_win_prob - 0.10
    assert qb_out.total_points_estimate < base.total_points_estimate - 5
    # Baseline (pre-conditions) preserved for the UI
    assert abs(qb_out.base_home_win_prob - base.home_win_prob) < 1e-9


def test_over_by_line_curve_is_decreasing() -> None:
    p = predict_nfl_game("DET", "GB", 1650, 1590)
    lines = sorted(float(k) for k in p.over_by_line)
    probs = [p.over_by_line[f"{line}"] for line in lines]
    assert all(a >= b for a, b in zip(probs, probs[1:]))
