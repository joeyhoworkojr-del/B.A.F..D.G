"""
How far apart the model is willing to place two teams.

`margin = elo_diff * (off + def) / 2 + home field`. When that coefficient is
too small, team differences compress and the fixed ~2-point home bump decides
games it has no business deciding — the model ends up favouring the home side
far more often than either the market or reality does.

The numbers here were calibrated against 799 completed regular-season games
(2023-25, nflverse), checked against both the closing line and the result.
They are pinned because the failure they prevent is silent: nothing breaks, the
model just quietly starts picking home.
"""
from __future__ import annotations

import itertools
import statistics as st

import pytest

from src.data.nfl import NFL_TEAMS, _DEF_COEF, _OFF_COEF
from src.predict.gridiron import LEAGUE_PARAMS, predict_nfl_game


def _margin(home: str, away: str, home_elo: float, away_elo: float) -> float:
    p = predict_nfl_game(home, away, home_elo, away_elo, league="nfl")
    return p.home_expected_pts - p.away_expected_pts


def test_home_field_alone_is_worth_about_two_points():
    # Measured mean home margin over 2023-25 is +2.28, and the market prices
    # it at +1.63. Anything much above three would be its own bias.
    margin = _margin("KC", "KC", 1500.0, 1500.0)
    assert 1.5 <= margin <= 3.0, margin


def test_a_hundred_elo_points_outweighs_home_field():
    # The bug this guards: when a rating gap cannot outrun the home bump, the
    # home side is favourite almost everywhere.
    home_field = _margin("KC", "KC", 1500.0, 1500.0)
    gap = _margin("KC", "KC", 1500.0, 1600.0)   # home is the *weaker* side
    assert gap < 0, (
        f"a 100-Elo underdog at home is still favoured by {gap:+.2f}; "
        f"home field is worth {home_field:+.2f}"
    )


def test_the_rating_scale_stays_calibrated():
    # 0.05 points of margin per Elo point — the minimum-error setting of the
    # sweep, and the one that brings the model's spread of projected margins
    # into line with the market's.
    assert (_OFF_COEF + _DEF_COEF) / 2 == pytest.approx(0.05, abs=1e-9)


def test_the_model_does_not_favour_the_home_side_far_more_than_reality_does():
    """
    Across every ordered pairing of the league, using the shipped priors.

    Real home win rate over 2023-25 was 53.9%; the market made the home side
    favourite 59.7% of the time. At the previous coefficient this figure was
    68%, which is what a reader notices as "it always picks the home team".
    """
    margins = [
        _margin(h, a, NFL_TEAMS[h].elo, NFL_TEAMS[a].elo)
        for h, a in itertools.permutations(NFL_TEAMS, 2)
    ]
    home_favoured = sum(1 for m in margins if m > 0) / len(margins)
    assert home_favoured < 0.66, f"home favoured in {home_favoured:.1%} of matchups"


def test_projected_margins_are_as_spread_out_as_the_markets_are():
    # The market's spread of closing lines over the same games had sd 5.88.
    # Ours was 4.19 before this calibration — compressed, which is what let
    # home field dominate.
    margins = [
        _margin(h, a, NFL_TEAMS[h].elo, NFL_TEAMS[a].elo)
        for h, a in itertools.permutations(NFL_TEAMS, 2)
    ]
    assert st.pstdev(margins) > 5.0, st.pstdev(margins)


def test_a_neutral_site_removes_home_field_entirely():
    p = predict_nfl_game("KC", "KC", 1500.0, 1500.0, league="nfl", neutral_site=True)
    assert p.home_expected_pts == pytest.approx(p.away_expected_pts)


def test_every_league_prices_home_field_within_a_believable_range():
    # College home field is genuinely larger than the NFL's, but not by much,
    # and a number outside this range would be a typo rather than a finding.
    for league, params in LEAGUE_PARAMS.items():
        assert 1.5 <= params["hfa"] <= 3.5, (league, params["hfa"])
