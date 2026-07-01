"""
Vectorised Monte Carlo simulation engine.

Uses NumPy Poisson sampling — 50k simulations runs in < 100 ms.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from src.config import settings


N_SIMS: int = settings.monte_carlo_sims   # 50_000


@dataclass
class SimResult:
    home_wins: float       # fraction [0,1]
    draws: float
    away_wins: float
    home_advance: float    # knockout — includes ET + penalty tiebreak
    away_advance: float
    home_score_dist: dict[int, float]   # marginal P(home scores k)
    away_score_dist: dict[int, float]
    total_score_dist: dict[int, float]
    expected_home_goals: float
    expected_away_goals: float
    std_error: float       # 1/sqrt(N) in pp


def simulate_soccer(
    home_xg: float,
    away_xg: float,
    *,
    knockout: bool = False,
    n_sims: int = N_SIMS,
    rng: np.random.Generator | None = None,
) -> SimResult:
    """
    Simulate `n_sims` matches using Poisson sampling.

    In knockout mode:
      - If drawn after 90 min → simulate 30 min extra time (λ × 1/3)
      - If still drawn → 50/50 penalty shootout
    """
    if rng is None:
        rng = np.random.default_rng()

    # 90-minute scores
    home_90 = rng.poisson(home_xg, size=n_sims)
    away_90 = rng.poisson(away_xg, size=n_sims)

    home_goals = home_90.copy()
    away_goals = away_90.copy()

    if knockout:
        draws_90 = home_90 == away_90
        n_et = int(draws_90.sum())
        if n_et > 0:
            et_home = rng.poisson(home_xg / 3, size=n_et)
            et_away = rng.poisson(away_xg / 3, size=n_et)
            home_goals[draws_90] += et_home
            away_goals[draws_90] += et_away
            # Penalty shootout for those still level after ET
            still_level = home_goals[draws_90] == away_goals[draws_90]
            pen_idx = np.where(draws_90)[0][still_level]
            penalties = rng.integers(0, 2, size=len(pen_idx))  # 0=away, 1=home
            home_goals[pen_idx] += penalties
            away_goals[pen_idx] += (1 - penalties)

    home_wins = float((home_goals > away_goals).sum()) / n_sims
    draws_frac = float((home_goals == away_goals).sum()) / n_sims if not knockout else 0.0
    away_wins = 1.0 - home_wins - draws_frac

    if knockout:
        home_adv = home_wins
        away_adv = away_wins
    else:
        home_adv = home_wins + draws_frac * 0.5   # notional
        away_adv = away_wins + draws_frac * 0.5

    def _dist(arr: np.ndarray, max_k: int = 9) -> dict[int, float]:
        return {k: float((arr == k).sum()) / n_sims for k in range(max_k + 1)}

    return SimResult(
        home_wins=home_wins,
        draws=draws_frac,
        away_wins=away_wins,
        home_advance=home_adv,
        away_advance=away_adv,
        home_score_dist=_dist(home_goals),
        away_score_dist=_dist(away_goals),
        total_score_dist=_dist(home_goals + away_goals),
        expected_home_goals=float(home_goals.mean()),
        expected_away_goals=float(away_goals.mean()),
        std_error=100.0 / math.sqrt(n_sims),
    )


def simulate_tournament(
    fixtures: list[tuple[str, str, float, float]],
    n_sims: int = N_SIMS,
) -> dict[str, float]:
    """
    Simulate a round of fixtures, returning {team_code: advance_probability}.

    Each fixture is (home, away, home_xg, away_xg).
    """
    rng = np.random.default_rng(42)
    advance_counts: dict[str, int] = {}

    for home_code, away_code, home_xg, away_xg in fixtures:
        res = simulate_soccer(home_xg, away_xg, knockout=True, n_sims=n_sims, rng=rng)
        advance_counts[home_code] = advance_counts.get(home_code, 0) + round(
            res.home_advance * n_sims
        )
        advance_counts[away_code] = advance_counts.get(away_code, 0) + round(
            res.away_advance * n_sims
        )

    return {code: count / n_sims for code, count in advance_counts.items()}
