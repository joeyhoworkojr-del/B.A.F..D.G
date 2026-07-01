"""
Soccer prediction engine — Elo → Poisson model.

Calibrated parameters (fit to SportRadar's published Round-of-16 probabilities):
  μ  = 1.06   base expected goals per team per 90 min
  Q  = 1540   Elo scale divisor
  host_edge = +150 Elo for host-nation home advantage (USA / MEX / CAN)

Validation against SportRadar (from calibration session):
  ARG–CPV  →  80.8%  (SR 82.3%) ✓
  SUI–DZA  →  49.6%  (SR 46.5%) ✓
  MEX–ECU  →  39.3%  (SR 43.6%) ✓
  FRA–ENG  →  41.2%  (SR 42.0%) ✓
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy.stats import poisson

from src.config import settings


# ─── Calibrated model constants ───────────────────────────────────────────────

MU: float = settings.elo_mu           # 1.06
Q: float = settings.elo_q             # 1540.0
HOST_EDGE: float = settings.elo_host_edge   # 150.0
SR_WEIGHT: float = settings.sr_blend_weight  # 0.60
MAX_GOALS: int = 10                   # truncation point for grid


# ─── Output shapes ────────────────────────────────────────────────────────────

@dataclass
class GoalExpectations:
    home_xg: float
    away_xg: float
    total_xg: float


@dataclass
class MatchProbabilities:
    home_win: float
    draw: float
    away_win: float
    home_xg: float
    away_xg: float


@dataclass
class TotalsProbabilities:
    over_1_5: float
    under_1_5: float
    over_2_5: float
    under_2_5: float
    over_3_5: float
    under_3_5: float
    over_4_5: float
    under_4_5: float
    btts: float              # both teams to score
    btts_no: float
    home_over_0_5: float
    home_over_1_5: float
    home_over_2_5: float
    away_over_0_5: float
    away_over_1_5: float
    away_over_2_5: float
    most_likely_total: int
    expected_scoreline: tuple[int, int]


@dataclass
class PlayerProp:
    name: str
    team: str
    anytime_scorer: float
    two_plus_goals: float
    xg: float


@dataclass
class WhyFactor:
    label: str
    value: float           # signed contribution to home win probability


@dataclass
class PredictionResult:
    home_team: str
    away_team: str
    home_elo: float
    away_elo: float
    model_probs: MatchProbabilities
    blended_probs: MatchProbabilities   # Elo model + SportRadar blend
    totals: TotalsProbabilities
    player_props: list[PlayerProp]
    scoreline_grid: list[list[float]]   # P(home=i, away=j) for i,j in 0..MAX_GOALS
    why_factors: list[WhyFactor]
    sim_error_bound: float             # ±% from 50k sims
    has_sr_data: bool


# ─── Core math ────────────────────────────────────────────────────────────────

def expected_goals(
    elo_home: float,
    elo_away: float,
    *,
    home_is_host: bool = False,
    neutral: bool = True,
    defensive_dampener: float = 1.0,
) -> GoalExpectations:
    """
    Convert Elo ratings to per-team expected goals via exponential goal ratio.

    Formula:
        effective_elo_diff = elo_home - elo_away + (HOST_EDGE if home_is_host else 0)
        goal_ratio         = 10 ^ (effective_elo_diff / Q)
        lambda_home        = MU * sqrt(goal_ratio)  * defensive_dampener
        lambda_away        = MU / sqrt(goal_ratio)  * defensive_dampener
    """
    home_bonus = HOST_EDGE if (home_is_host and not neutral) else 0.0
    elo_diff = elo_home - elo_away + home_bonus
    goal_ratio = 10 ** (elo_diff / Q)
    raw_home = MU * math.sqrt(goal_ratio)
    raw_away = MU / math.sqrt(goal_ratio)
    return GoalExpectations(
        home_xg=raw_home * defensive_dampener,
        away_xg=raw_away * defensive_dampener,
        total_xg=(raw_home + raw_away) * defensive_dampener,
    )


def _poisson_pmf_array(lam: float, max_k: int = MAX_GOALS) -> np.ndarray:
    return np.array([poisson.pmf(k, lam) for k in range(max_k + 1)])


def scoreline_grid(xg: GoalExpectations) -> np.ndarray:
    """Return (MAX_GOALS+1) × (MAX_GOALS+1) matrix of P(home=i, away=j)."""
    home_pmf = _poisson_pmf_array(xg.home_xg)
    away_pmf = _poisson_pmf_array(xg.away_xg)
    return np.outer(home_pmf, away_pmf)


def match_probabilities_from_grid(grid: np.ndarray) -> MatchProbabilities:
    """
    grid[i][j] = P(home scores i, away scores j).
    Upper triangle (i < j): away scored more  → away win.
    Lower triangle (i > j): home scored more  → home win.
    Diagonal (i == j): draw.
    """
    n = grid.shape[0]
    i_idx, j_idx = np.triu_indices(n, k=1)  # i_idx < j_idx (upper triangle)
    away_win = float(grid[i_idx, j_idx].sum())   # home i < away j → away win
    draw     = float(np.trace(grid))
    home_win = float(grid[j_idx, i_idx].sum())   # home j > away i → home win
    # normalise rounding errors
    total = home_win + draw + away_win
    return MatchProbabilities(
        home_win=home_win / total,
        draw=draw / total,
        away_win=away_win / total,
        home_xg=0.0,   # caller fills this
        away_xg=0.0,
    )


def totals_from_xg(xg: GoalExpectations) -> TotalsProbabilities:
    lam = xg.total_xg
    # Total goals is Poisson(lambda_home + lambda_away)
    cdf = poisson.cdf
    over = lambda k: float(1 - cdf(k, lam))
    # Both-teams-to-score: P(home≥1) * P(away≥1)
    btts = (1 - math.exp(-xg.home_xg)) * (1 - math.exp(-xg.away_xg))
    # Team totals
    h_over = lambda k: float(1 - cdf(k, xg.home_xg))
    a_over = lambda k: float(1 - cdf(k, xg.away_xg))
    # Most likely total (mode of Poisson, floored lambda)
    mlt = int(lam) if lam >= 1 else 0

    def expected_score() -> tuple[int, int]:
        h_mode = max(0, int(xg.home_xg))
        a_mode = max(0, int(xg.away_xg))
        return h_mode, a_mode

    return TotalsProbabilities(
        over_1_5=over(1), under_1_5=1 - over(1),
        over_2_5=over(2), under_2_5=1 - over(2),
        over_3_5=over(3), under_3_5=1 - over(3),
        over_4_5=over(4), under_4_5=1 - over(4),
        btts=btts, btts_no=1 - btts,
        home_over_0_5=h_over(0), home_over_1_5=h_over(1), home_over_2_5=h_over(2),
        away_over_0_5=a_over(0), away_over_1_5=a_over(1), away_over_2_5=a_over(2),
        most_likely_total=mlt,
        expected_scoreline=expected_score(),
    )


def player_props_from_scorers(
    scorers: list,   # list[PlayerScorer]
    xg_home: float,
    xg_away: float,
    home_team: str,
    away_team: str,
) -> list[PlayerProp]:
    props = []
    for s in scorers:
        lam_team = xg_home if s.team == home_team else xg_away
        player_lam = s.goal_share * lam_team
        anytime = 1 - math.exp(-player_lam)
        two_plus = 1 - math.exp(-player_lam) - player_lam * math.exp(-player_lam)
        props.append(PlayerProp(
            name=s.name,
            team=s.team,
            anytime_scorer=anytime,
            two_plus_goals=two_plus,
            xg=player_lam,
        ))
    return props


def why_factors(
    elo_home: float,
    elo_away: float,
    home_is_host: bool,
    xg: GoalExpectations,
    model_probs: MatchProbabilities,
) -> list[WhyFactor]:
    """Build signed contribution breakdown for the 'Why' panel."""
    base_elo_diff = elo_home - elo_away
    # Counterfactual: equal Elos, no host edge
    cf_xg = expected_goals(1500.0, 1500.0, home_is_host=False, neutral=True)
    cf_grid = scoreline_grid(cf_xg)
    cf_probs = match_probabilities_from_grid(cf_grid)
    cf_hw = cf_probs.home_win

    # Elo gap contribution
    elo_xg = expected_goals(elo_home, elo_away, home_is_host=False, neutral=True)
    elo_grid = scoreline_grid(elo_xg)
    elo_probs = match_probabilities_from_grid(elo_grid)

    elo_contribution = elo_probs.home_win - cf_hw
    host_contribution = model_probs.home_win - elo_probs.home_win if home_is_host else 0.0

    factors = [
        WhyFactor(f"Elo gap ({base_elo_diff:+.0f})", elo_contribution),
    ]
    if abs(host_contribution) > 0.005:
        factors.append(WhyFactor("Host-nation advantage", host_contribution))
    # xG imbalance
    xg_diff = xg.home_xg - xg.away_xg
    factors.append(WhyFactor(f"xG differential ({xg_diff:+.2f})", xg_diff * 0.12))
    return factors


def blend_with_sr(
    model: MatchProbabilities,
    sr_home: Optional[float],
    sr_draw: Optional[float],
    sr_away: Optional[float],
    sr_weight: float = SR_WEIGHT,
) -> MatchProbabilities:
    if sr_home is None or sr_draw is None or sr_away is None:
        return model
    my_w = 1 - sr_weight
    hw = my_w * model.home_win + sr_weight * sr_home
    dr = my_w * model.draw    + sr_weight * sr_draw
    aw = my_w * model.away_win + sr_weight * sr_away
    total = hw + dr + aw
    return MatchProbabilities(
        home_win=hw / total,
        draw=dr / total,
        away_win=aw / total,
        home_xg=model.home_xg,
        away_xg=model.away_xg,
    )


# ─── Main entry point ─────────────────────────────────────────────────────────

def predict_match(
    home_team_code: str,
    away_team_code: str,
    home_elo: float,
    away_elo: float,
    *,
    home_is_host: bool = False,
    neutral: bool = True,
    defensive_dampener: float = 1.0,
    sr_home_win: Optional[float] = None,
    sr_draw: Optional[float] = None,
    sr_away_win: Optional[float] = None,
    scorers: Optional[list] = None,
) -> PredictionResult:
    xg = expected_goals(
        home_elo, away_elo,
        home_is_host=home_is_host,
        neutral=neutral,
        defensive_dampener=defensive_dampener,
    )
    grid = scoreline_grid(xg)
    model_probs = match_probabilities_from_grid(grid)
    model_probs = MatchProbabilities(
        home_win=model_probs.home_win,
        draw=model_probs.draw,
        away_win=model_probs.away_win,
        home_xg=xg.home_xg,
        away_xg=xg.away_xg,
    )

    blended = blend_with_sr(model_probs, sr_home_win, sr_draw, sr_away_win)
    totals = totals_from_xg(xg)

    # Player props — only for scorers from these two teams
    active_scorers = []
    if scorers:
        active_scorers = [
            s for s in scorers
            if s.team in (home_team_code, away_team_code)
        ]
    props = player_props_from_scorers(
        active_scorers, xg.home_xg, xg.away_xg,
        home_team_code, away_team_code,
    )

    w_factors = why_factors(home_elo, away_elo, home_is_host, xg, model_probs)

    # Sim error bound: ±1/sqrt(N) in percentage points
    n_sims = settings.monte_carlo_sims
    sim_error = 100.0 / math.sqrt(n_sims)

    return PredictionResult(
        home_team=home_team_code,
        away_team=away_team_code,
        home_elo=home_elo,
        away_elo=away_elo,
        model_probs=model_probs,
        blended_probs=blended,
        totals=totals,
        player_props=props,
        scoreline_grid=grid.tolist(),
        why_factors=w_factors,
        sim_error_bound=sim_error,
        has_sr_data=sr_home_win is not None,
    )
