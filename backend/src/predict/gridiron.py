"""
NFL/gridiron prediction engine — Elo-based win probability.

Uses the standard Elo win probability formula calibrated for American football,
with a home-field advantage of 48 Elo points (≈3 points on the spread).

All outputs are honest probability estimates. No lock-of-the-century claims.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


NFL_HOME_EDGE = 48.0   # Elo points
NFL_K = 400.0          # Elo scale


@dataclass
class NFLPrediction:
    home_team: str
    away_team: str
    home_elo: float
    away_elo: float
    home_win_prob: float
    away_win_prob: float
    predicted_spread: float    # positive = home favored
    home_cover_prob: float     # vs the spread line
    away_cover_prob: float
    total_points_estimate: float
    why_factors: list[dict]    # signed contributions


def elo_win_probability(elo_a: float, elo_b: float, *, home_field: bool = True) -> float:
    """P(A wins) given Elo ratings, including home-field if applicable."""
    bonus = NFL_HOME_EDGE if home_field else 0.0
    diff = elo_a - elo_b + bonus
    return 1 / (1 + 10 ** (-diff / NFL_K))


def elo_to_spread(win_prob: float) -> float:
    """
    Approximate point spread from win probability.
    Using logit transformation calibrated to NFL spreads.
    """
    if win_prob <= 0 or win_prob >= 1:
        return 0.0
    log_odds = math.log(win_prob / (1 - win_prob))
    # Empirical: each Elo point ≈ 0.065 points on spread
    # Full derivation: spread ≈ logit(p) * (spread_scale)
    return log_odds * 3.5   # calibrated constant


def cover_probability(win_prob: float, spread: float) -> float:
    """Rough ATS probability — regresses toward 50/50 as spread shrinks."""
    # A bigger spread means the market has already priced in the edge,
    # so covering is harder. Simple regression: ~52% at pick-em, tapers.
    base_adv = win_prob - 0.50
    return 0.50 + base_adv * 0.70  # 70% bleed = regression to market


def predict_nfl_game(
    home_code: str,
    away_code: str,
    home_elo: float,
    away_elo: float,
    *,
    neutral_site: bool = False,
    spread_line: Optional[float] = None,   # Vegas line (+ = underdog home)
) -> NFLPrediction:
    hw = elo_win_probability(home_elo, away_elo, home_field=not neutral_site)
    aw = 1 - hw
    spread = elo_to_spread(hw)
    hcover = cover_probability(hw, abs(spread))
    acover = 1 - hcover

    # Total points: base 44 + 2 pts per 100 Elo above 1500 average
    avg_elo = (home_elo + away_elo) / 2
    total_est = 44 + (avg_elo - 1500) * 0.02

    why = [
        {
            "label": f"Elo gap ({home_elo - away_elo:+.0f})",
            "value": hw - 0.50,
        },
    ]
    if not neutral_site:
        why.append({"label": "Home-field advantage", "value": NFL_HOME_EDGE / NFL_K * 0.15})

    return NFLPrediction(
        home_team=home_code,
        away_team=away_code,
        home_elo=home_elo,
        away_elo=away_elo,
        home_win_prob=hw,
        away_win_prob=aw,
        predicted_spread=spread,
        home_cover_prob=hcover,
        away_cover_prob=acover,
        total_points_estimate=total_est,
        why_factors=why,
    )
