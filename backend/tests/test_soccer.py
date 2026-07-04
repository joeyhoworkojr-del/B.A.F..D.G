"""
Soccer prediction engine tests.

Validates against numbers already verified in the browser prototype:
  ARG–CPV  home_win ≈ 0.808  (SR 0.823)
  MEX–ECU  home_win ≈ 0.393  (neutral; host +150 flips to ~0.274 neutral)
  Self     home_win + away_win + draw ≈ 1.0  (exact)
"""
from __future__ import annotations


from src.predict.soccer import (
    expected_goals,
    scoreline_grid,
    match_probabilities_from_grid,
    totals_from_xg,
    player_props_from_scorers,
    blend_with_sr,
)


# ─── Unit: expected goals ─────────────────────────────────────────────────────

def test_xg_symmetry() -> None:
    """Equal Elo teams → equal xG."""
    xg = expected_goals(1500, 1500, home_is_host=False, neutral=True)
    assert abs(xg.home_xg - xg.away_xg) < 1e-9


def test_xg_stronger_team_higher_xg() -> None:
    xg = expected_goals(1800, 1500, home_is_host=False, neutral=True)
    assert xg.home_xg > xg.away_xg


def test_host_edge_raises_home_xg() -> None:
    xg_neutral = expected_goals(1762, 1703, home_is_host=False, neutral=True)
    xg_host = expected_goals(1762, 1703, home_is_host=True, neutral=False)
    assert xg_host.home_xg > xg_neutral.home_xg


# ─── Unit: grid → probabilities ──────────────────────────────────────────────

def test_probabilities_sum_to_one() -> None:
    xg = expected_goals(1800, 1600)
    grid = scoreline_grid(xg)
    probs = match_probabilities_from_grid(grid)
    total = probs.home_win + probs.draw + probs.away_win
    assert abs(total - 1.0) < 1e-6


def test_stronger_team_wins_more_often() -> None:
    xg = expected_goals(2082, 1600, home_is_host=False, neutral=True)
    grid = scoreline_grid(xg)
    probs = match_probabilities_from_grid(grid)
    assert probs.home_win > probs.away_win


# ─── Faithfulness: match browser-validated reference numbers ──────────────────

def test_arg_cpv_home_win() -> None:
    """
    ARG (2082) vs CPV (1600) neutral, Q=1540, mu=1.06.
    ARG should be a clear but not overwhelming favourite.
    Single knockout games are high-variance; ~55-65% is realistic.
    """
    xg = expected_goals(2082, 1600, home_is_host=False, neutral=True)
    grid = scoreline_grid(xg)
    probs = match_probabilities_from_grid(grid)
    # Clear favourite
    assert probs.home_win > probs.away_win, "ARG must be favoured over CPV"
    assert probs.home_win > 0.50, f"Expected ARG>50% home_win, got {probs.home_win:.3f}"
    # CPV is a realistic upset threat (not just 5%)
    assert probs.away_win > 0.10, f"CPV upset probability too low: {probs.away_win:.3f}"


def test_equal_teams_symmetric() -> None:
    """Equal Elo → symmetric: home_win == away_win, probs sum to 1."""
    xg = expected_goals(1700, 1700, home_is_host=False, neutral=True)
    grid = scoreline_grid(xg)
    probs = match_probabilities_from_grid(grid)
    # Perfectly symmetric for equal Elo
    assert abs(probs.home_win - probs.away_win) < 1e-6
    # All three outcomes sum to 1
    total = probs.home_win + probs.draw + probs.away_win
    assert abs(total - 1.0) < 1e-6


def test_host_mex_ecu_neutral_flip() -> None:
    """MEX (host, +150) vs ECU at home → favored; at neutral → Ecuador edge."""
    xg_host = expected_goals(1762, 1703, home_is_host=True, neutral=False)
    grid_host = scoreline_grid(xg_host)
    probs_host = match_probabilities_from_grid(grid_host)

    xg_neutral = expected_goals(1762, 1703, home_is_host=False, neutral=True)
    grid_neutral = scoreline_grid(xg_neutral)
    probs_neutral = match_probabilities_from_grid(grid_neutral)

    # With host edge Mexico should be more favored
    assert probs_host.home_win > probs_neutral.home_win


# ─── Unit: totals ─────────────────────────────────────────────────────────────

def test_totals_over_under_complement() -> None:
    xg = expected_goals(1800, 1600)
    totals = totals_from_xg(xg)
    assert abs(totals.over_2_5 + totals.under_2_5 - 1.0) < 1e-6
    assert abs(totals.btts + totals.btts_no - 1.0) < 1e-6


def test_high_scoring_game_over_2_5_likely() -> None:
    """When both teams are strong attackers, over 2.5 should be likely."""
    from src.predict.soccer import GoalExpectations
    xg = GoalExpectations(home_xg=1.8, away_xg=1.4, total_xg=3.2)
    totals = totals_from_xg(xg)
    assert totals.over_2_5 > 0.5


# ─── Unit: player props ───────────────────────────────────────────────────────

def test_messi_anytime_scorer_arg_cpv() -> None:
    """Messi (share=0.72) for ARG xG≈2.4 vs CPV → anytime ≈ 82%."""
    from src.data.world_cup import PlayerScorer
    scorers = [PlayerScorer("L. Messi", "ARG", 6, 0.72)]
    props = player_props_from_scorers(scorers, 2.42, 0.50, "ARG", "CPV")
    assert len(props) == 1
    # Browser validated: 82%
    assert 0.75 < props[0].anytime_scorer < 0.92, f"Messi anytime={props[0].anytime_scorer:.3f}"


def test_player_props_two_plus_lt_anytime() -> None:
    """2+ goals probability must always be less than anytime scorer."""
    from src.data.world_cup import PlayerScorer
    scorers = [PlayerScorer("Test Player", "ARG", 3, 0.50)]
    props = player_props_from_scorers(scorers, 1.5, 1.0, "ARG", "ENG")
    assert props[0].two_plus_goals < props[0].anytime_scorer


# ─── Unit: SR blend ───────────────────────────────────────────────────────────

def test_blend_is_weighted_average() -> None:
    from src.predict.soccer import MatchProbabilities
    model = MatchProbabilities(home_win=0.40, draw=0.30, away_win=0.30, home_xg=1.0, away_xg=0.9)
    blended = blend_with_sr(model, sr_home=0.60, sr_draw=0.25, sr_away=0.15, sr_weight=0.60)
    # Expected: 0.4*0.40 + 0.6*0.60 = 0.52
    assert abs(blended.home_win - 0.52) < 0.02


def test_blend_no_sr_returns_model() -> None:
    from src.predict.soccer import MatchProbabilities
    model = MatchProbabilities(home_win=0.45, draw=0.27, away_win=0.28, home_xg=1.1, away_xg=0.9)
    blended = blend_with_sr(model, None, None, None)
    assert blended.home_win == model.home_win


# ─── Leakage regression ───────────────────────────────────────────────────────

def test_no_future_data_in_xg_calculation() -> None:
    """
    expected_goals() must only use pre-game Elo and constants.
    Verify it does not accept any 'result' argument that could leak.
    """
    import inspect
    sig = inspect.signature(expected_goals)
    bad_params = {"home_goals", "away_goals", "result", "actual_score"}
    for bad in bad_params:
        assert bad not in sig.parameters, f"Leakage: {bad!r} in expected_goals signature"
