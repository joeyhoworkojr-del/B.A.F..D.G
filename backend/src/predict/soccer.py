"""
Soccer prediction engine — Elo → team-style xG → Dixon-Coles Poisson model.

Pipeline:
  1. Elo difference sets the goal *ratio* between the sides.
  2. Team attack/defense style multipliers set the goal *level* — so a match
     between two defensive sides projects a genuinely lower total than one
     between open sides (critical for over/under markets).
  3. Live conditions (weather, lineup absences) scale each side's xG.
  4. A Dixon-Coles low-score correlation correction fixes the known bias of
     independent Poisson models (too few draws / low-scoring results), which
     directly improves draw and under-2.5 calibration.

Calibrated parameters:
  μ  = 1.35   base expected goals per team per 90 min (matches real ~2.7 totals)
  Q  = 1200   Elo scale divisor (favourite separation)
  host_edge = +150 Elo for host-nation home advantage (USA / MEX / CAN)
  ρ  = -0.13  Dixon-Coles low-score correlation
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy.stats import poisson

from src.config import settings
from src.data.world_cup import get_style


# ─── Calibrated model constants ───────────────────────────────────────────────

MU: float = settings.elo_mu           # 1.06
Q: float = settings.elo_q             # 1540.0
HOST_EDGE: float = settings.elo_host_edge   # 150.0
SR_WEIGHT: float = settings.sr_blend_weight  # 0.60
MAX_GOALS: int = 10                   # truncation point for grid
DC_RHO: float = -0.13                 # Dixon-Coles low-score correlation

TOTAL_LINES: tuple[float, ...] = (0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5)


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
    over_by_line: dict[str, float] = field(default_factory=dict)  # "2.5" → P(over)


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
    base_probs: Optional[MatchProbabilities] = None  # before live conditions
    conditions: list = field(default_factory=list)   # applied Adjustments
    fair_odds: dict[str, float] = field(default_factory=dict)


# ─── Core math ────────────────────────────────────────────────────────────────

def expected_goals(
    elo_home: float,
    elo_away: float,
    *,
    home_is_host: bool = False,
    neutral: bool = True,
    defensive_dampener: float = 1.0,
    home_attack: float = 1.0,
    home_defense: float = 1.0,
    away_attack: float = 1.0,
    away_defense: float = 1.0,
) -> GoalExpectations:
    """
    Convert Elo ratings to per-team expected goals via exponential goal ratio,
    then scale by team playing styles.

    Formula:
        effective_elo_diff = elo_home - elo_away + (HOST_EDGE if home_is_host else 0)
        goal_ratio         = 10 ^ (effective_elo_diff / Q)
        lambda_home        = MU * sqrt(goal_ratio) * home_attack * away_defense
        lambda_away        = MU / sqrt(goal_ratio) * away_attack * home_defense
    """
    home_bonus = HOST_EDGE if (home_is_host and not neutral) else 0.0
    elo_diff = elo_home - elo_away + home_bonus
    goal_ratio = 10 ** (elo_diff / Q)
    raw_home = MU * math.sqrt(goal_ratio) * home_attack * away_defense
    raw_away = MU / math.sqrt(goal_ratio) * away_attack * home_defense
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


def dixon_coles_adjust(
    grid: np.ndarray,
    home_xg: float,
    away_xg: float,
    rho: float = DC_RHO,
) -> np.ndarray:
    """
    Apply the Dixon-Coles (1997) low-score correlation correction.

    Independent Poisson models under-predict 0-0 and 1-1 and over-predict
    1-0 / 0-1 relative to real match data. With ρ < 0 the correction inflates
    the draw-ish low scores:

        τ(0,0) = 1 − λμρ     τ(0,1) = 1 + λρ
        τ(1,0) = 1 + μρ      τ(1,1) = 1 − ρ
    """
    adj = grid.copy()
    lam, mu = home_xg, away_xg
    adj[0, 0] *= max(1.0 - lam * mu * rho, 1e-12)
    adj[0, 1] *= max(1.0 + lam * rho, 1e-12)
    adj[1, 0] *= max(1.0 + mu * rho, 1e-12)
    adj[1, 1] *= max(1.0 - rho, 1e-12)
    return adj / adj.sum()


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


def totals_from_grid(grid: np.ndarray) -> TotalsProbabilities:
    """
    All totals markets computed directly from the (DC-adjusted) scoreline
    grid, so correlation corrections flow through to over/under numbers.
    """
    n = grid.shape[0]
    totals_dist = np.zeros(2 * n - 1)
    for t in range(2 * n - 1):
        for i in range(max(0, t - n + 1), min(t, n - 1) + 1):
            totals_dist[t] += grid[i, t - i]
    cum = np.cumsum(totals_dist)

    def over(line: float) -> float:
        # P(total > line) for a half line k.5 == P(total >= k+1)
        k = int(math.floor(line))
        return float(1.0 - cum[k]) if k < len(cum) else 0.0

    home_marginal = grid.sum(axis=1)
    away_marginal = grid.sum(axis=0)

    def h_over(k: int) -> float:
        return float(home_marginal[k + 1:].sum())

    def a_over(k: int) -> float:
        return float(away_marginal[k + 1:].sum())

    btts = float(grid[1:, 1:].sum())
    i_star, j_star = np.unravel_index(int(grid.argmax()), grid.shape)

    return TotalsProbabilities(
        over_1_5=over(1.5), under_1_5=1 - over(1.5),
        over_2_5=over(2.5), under_2_5=1 - over(2.5),
        over_3_5=over(3.5), under_3_5=1 - over(3.5),
        over_4_5=over(4.5), under_4_5=1 - over(4.5),
        btts=btts, btts_no=1 - btts,
        home_over_0_5=h_over(0), home_over_1_5=h_over(1), home_over_2_5=h_over(2),
        away_over_0_5=a_over(0), away_over_1_5=a_over(1), away_over_2_5=a_over(2),
        most_likely_total=int(np.argmax(totals_dist)),
        expected_scoreline=(int(i_star), int(j_star)),
        over_by_line={f"{line}": over(line) for line in TOTAL_LINES},
    )


def totals_from_xg(xg: GoalExpectations) -> TotalsProbabilities:
    """Independent-Poisson totals straight from xG (kept for compatibility)."""
    lam = xg.total_xg
    # Total goals is Poisson(lambda_home + lambda_away)
    cdf = poisson.cdf

    def over(k: int) -> float:
        return float(1 - cdf(k, lam))

    # Both-teams-to-score: P(home≥1) * P(away≥1)
    btts = (1 - math.exp(-xg.home_xg)) * (1 - math.exp(-xg.away_xg))

    # Team totals
    def h_over(k: int) -> float:
        return float(1 - cdf(k, xg.home_xg))

    def a_over(k: int) -> float:
        return float(1 - cdf(k, xg.away_xg))
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
        over_by_line={f"{k + 0.5}": over(k) for k in range(7)},
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


def _probs_for(xg: GoalExpectations, rho: float = DC_RHO) -> MatchProbabilities:
    grid = dixon_coles_adjust(scoreline_grid(xg), xg.home_xg, xg.away_xg, rho)
    return match_probabilities_from_grid(grid)


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
    use_styles: bool = True,
    adjustments: Optional[list] = None,   # list[Adjustment] from live conditions
) -> PredictionResult:
    h_att, h_def = get_style(home_team_code) if use_styles else (1.0, 1.0)
    a_att, a_def = get_style(away_team_code) if use_styles else (1.0, 1.0)

    style_kwargs = dict(
        home_is_host=home_is_host,
        neutral=neutral,
        defensive_dampener=defensive_dampener,
    )
    xg_elo_only = expected_goals(home_elo, away_elo, **style_kwargs)
    xg_styled = expected_goals(
        home_elo, away_elo,
        home_attack=h_att, home_defense=h_def,
        away_attack=a_att, away_defense=a_def,
        **style_kwargs,
    )

    # Live conditions: weather + lineup multipliers on each side's xG
    conditions = list(adjustments or [])
    home_mult = away_mult = 1.0
    for adj in conditions:
        home_mult *= adj.home_xg_mult
        away_mult *= adj.away_xg_mult
    xg = GoalExpectations(
        home_xg=xg_styled.home_xg * home_mult,
        away_xg=xg_styled.away_xg * away_mult,
        total_xg=xg_styled.home_xg * home_mult + xg_styled.away_xg * away_mult,
    )

    grid = dixon_coles_adjust(scoreline_grid(xg), xg.home_xg, xg.away_xg)
    grid_probs = match_probabilities_from_grid(grid)
    model_probs = MatchProbabilities(
        home_win=grid_probs.home_win,
        draw=grid_probs.draw,
        away_win=grid_probs.away_win,
        home_xg=xg.home_xg,
        away_xg=xg.away_xg,
    )

    # Pre-conditions baseline so the UI can show how live data moved the line
    styled_probs = _probs_for(xg_styled)
    base_probs = MatchProbabilities(
        home_win=styled_probs.home_win,
        draw=styled_probs.draw,
        away_win=styled_probs.away_win,
        home_xg=xg_styled.home_xg,
        away_xg=xg_styled.away_xg,
    )

    blended = blend_with_sr(model_probs, sr_home_win, sr_draw, sr_away_win)
    totals = totals_from_grid(grid)

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

    # Why factors: decompose home-win probability into signed contributions
    cf_probs = _probs_for(expected_goals(1500.0, 1500.0))
    elo_probs = _probs_for(
        expected_goals(home_elo, away_elo, home_is_host=False, neutral=True)
    )
    w_factors = [
        WhyFactor(
            f"Elo gap ({home_elo - away_elo:+.0f})",
            elo_probs.home_win - cf_probs.home_win,
        ),
    ]
    if home_is_host and not neutral:
        host_probs = _probs_for(
            expected_goals(home_elo, away_elo, home_is_host=True, neutral=False)
        )
        w_factors.append(WhyFactor("Host-nation advantage", host_probs.home_win - elo_probs.home_win))
    if use_styles:
        style_delta = styled_probs.home_win - _probs_for(xg_elo_only).home_win
        if abs(style_delta) > 0.002:
            w_factors.append(WhyFactor("Playing styles (att/def)", style_delta))
    if conditions:
        cond_delta = model_probs.home_win - styled_probs.home_win
        w_factors.append(WhyFactor("Live conditions", cond_delta))

    # Fair (no-vig break-even) odds from the final numbers
    def _fair(p: float) -> float:
        return round(1.0 / max(p, 1e-6), 2)

    fair_odds = {
        "home": _fair(blended.home_win),
        "draw": _fair(blended.draw),
        "away": _fair(blended.away_win),
        "over_2_5": _fair(totals.over_2_5),
        "under_2_5": _fair(totals.under_2_5),
        "btts": _fair(totals.btts),
    }

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
        base_probs=base_probs,
        conditions=conditions,
        fair_odds=fair_odds,
    )
