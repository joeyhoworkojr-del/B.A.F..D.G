"""
NFL/gridiron prediction engine — expected-points model with margin and total
distributions.

Instead of a bare Elo win formula, each matchup produces expected points for
both teams (offense rating vs opposing defense rating, plus home field, plus
live adjustments for weather and inactive players). From there:

  margin ~ Normal(home_pts − away_pts, σ = 13.45)   [historical NFL margin σ]
  total  ~ Normal(home_pts + away_pts, σ = 13.70)   [historical NFL total σ]

which gives real probabilities for every market:
  win, spread cover at ANY line, over/under at ANY line, team totals.

All outputs are honest probability estimates. No lock-of-the-century claims.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from src.data.cfl import get_cfl_ratings
from src.data.nfl import get_nfl_ratings

MARGIN_SIGMA = 13.45   # std-dev of final margin vs expectation
TOTAL_SIGMA = 13.70    # std-dev of final total vs expectation
TEAM_SIGMA = 10.0      # std-dev of a single team's points
HFA_POINTS = 2.1       # home-field advantage, points

# Per-league parameters. CFL: 3-down football — more possessions, more
# scoring, slightly wider distributions, a touch more home edge (travel).
LEAGUE_PARAMS: dict[str, dict] = {
    "nfl": {
        "ratings": get_nfl_ratings,
        "margin_sigma": MARGIN_SIGMA,
        "total_sigma": TOTAL_SIGMA,
        "team_sigma": TEAM_SIGMA,
        "hfa": HFA_POINTS,
    },
    "cfl": {
        "ratings": get_cfl_ratings,
        "margin_sigma": 13.9,
        "total_sigma": 14.5,
        "team_sigma": 10.5,
        "hfa": 2.5,
    },
}


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


@dataclass
class NFLPrediction:
    home_team: str
    away_team: str
    home_elo: float
    away_elo: float
    home_win_prob: float
    away_win_prob: float
    predicted_spread: float    # positive = home favored
    home_cover_prob: float     # vs the quoted (or model) spread line
    away_cover_prob: float
    total_points_estimate: float
    why_factors: list[dict]    # signed contributions
    # Expected-points breakdown
    home_expected_pts: float = 0.0
    away_expected_pts: float = 0.0
    # Totals market
    total_line: Optional[float] = None
    over_prob: float = 0.0
    under_prob: float = 0.0
    over_by_line: dict[str, float] = field(default_factory=dict)
    home_team_total_over: dict[str, float] = field(default_factory=dict)
    away_team_total_over: dict[str, float] = field(default_factory=dict)
    # Live conditions
    base_home_win_prob: float = 0.0   # before live conditions
    base_total_estimate: float = 0.0
    conditions: list = field(default_factory=list)
    fair_odds: dict[str, float] = field(default_factory=dict)


def expected_points(
    home_code: str,
    away_code: str,
    *,
    neutral_site: bool = False,
    league: str = "nfl",
) -> tuple[float, float]:
    """
    Expected points for each side: the average of what the offense usually
    scores and what the opposing defense usually allows, centered on the
    league scoring environment, plus home field.
    """
    params = LEAGUE_PARAMS[league]
    home_off, home_def = params["ratings"](home_code)
    away_off, away_def = params["ratings"](away_code)
    home_pts = (home_off + away_def) / 2.0
    away_pts = (away_off + home_def) / 2.0
    if not neutral_site:
        home_pts += params["hfa"] / 2.0
        away_pts -= params["hfa"] / 2.0
    return home_pts, away_pts


def win_probability(margin_mu: float, sigma: float = MARGIN_SIGMA) -> float:
    """P(home wins) = P(margin > 0) under Normal(margin_mu, sigma)."""
    return 1.0 - _norm_cdf(-margin_mu / sigma)


def cover_probability(margin_mu: float, spread_line: float, sigma: float = MARGIN_SIGMA) -> float:
    """
    P(home covers a spread of `spread_line`), where the line follows the
    betting convention: home -3.5 → spread_line = -3.5, home covers when
    margin > 3.5, i.e. margin + spread_line > 0.
    """
    return 1.0 - _norm_cdf(-(margin_mu + spread_line) / sigma)


def total_over_probability(total_mu: float, total_line: float, sigma: float = TOTAL_SIGMA) -> float:
    """P(total points > line) under Normal(total_mu, sigma)."""
    return 1.0 - _norm_cdf((total_line - total_mu) / sigma)


# Legacy Elo helpers kept for compatibility ------------------------------------

NFL_HOME_EDGE = 48.0   # Elo points
NFL_K = 400.0          # Elo scale


def elo_win_probability(elo_a: float, elo_b: float, *, home_field: bool = True) -> float:
    """P(A wins) given Elo ratings, including home-field if applicable."""
    bonus = NFL_HOME_EDGE if home_field else 0.0
    diff = elo_a - elo_b + bonus
    return 1 / (1 + 10 ** (-diff / NFL_K))


# ─── Main entry point ─────────────────────────────────────────────────────────

def predict_nfl_game(
    home_code: str,
    away_code: str,
    home_elo: float,
    away_elo: float,
    *,
    neutral_site: bool = False,
    spread_line: Optional[float] = None,   # betting convention: home -3.5 → -3.5
    total_line: Optional[float] = None,    # e.g. 44.5
    adjustments: Optional[list] = None,    # list[Adjustment] from live conditions
    league: str = "nfl",                   # "nfl" | "cfl"
) -> NFLPrediction:
    params = LEAGUE_PARAMS[league]
    m_sigma = params["margin_sigma"]
    t_sigma = params["total_sigma"]
    team_sigma = params["team_sigma"]
    hfa = params["hfa"]

    base_home_pts, base_away_pts = expected_points(
        home_code, away_code, neutral_site=neutral_site, league=league,
    )

    # Live conditions: weather and inactives shift expected points
    conditions = list(adjustments or [])
    home_pts = base_home_pts + sum(a.home_pts_delta for a in conditions)
    away_pts = base_away_pts + sum(a.away_pts_delta for a in conditions)
    home_pts = max(6.0, home_pts)   # floor: teams rarely project under a TD
    away_pts = max(6.0, away_pts)

    margin_mu = home_pts - away_pts
    total_mu = home_pts + away_pts

    hw = win_probability(margin_mu, m_sigma)
    base_hw = win_probability(base_home_pts - base_away_pts, m_sigma)
    base_total = base_home_pts + base_away_pts

    # Spread: use the quoted line if provided, else the model's own number
    line = spread_line if spread_line is not None else -margin_mu
    hcover = cover_probability(margin_mu, line, m_sigma)

    # Totals: quoted line or the model's expectation rounded to the half point
    t_line = total_line if total_line is not None else round(total_mu * 2) / 2
    over_p = total_over_probability(total_mu, t_line, t_sigma)

    # Probability curve across nearby alternate lines (for the line explorer)
    center = round(total_mu)
    over_by_line = {
        f"{center + off + 0.5}": total_over_probability(total_mu, center + off + 0.5, t_sigma)
        for off in range(-8, 9)
    }

    def _team_over(mu: float) -> dict[str, float]:
        c = round(mu)
        return {
            f"{c + off + 0.5}": 1.0 - _norm_cdf((c + off + 0.5 - mu) / team_sigma)
            for off in range(-4, 5)
        }

    # Why factors: signed contributions to home win probability
    even_hw = win_probability(0.0 if neutral_site else hfa, m_sigma)
    rating_margin = (base_home_pts - base_away_pts) - (0.0 if neutral_site else hfa)
    why = [
        {
            "label": f"Team strength ({rating_margin:+.1f} pts)",
            "value": base_hw - even_hw,
        },
    ]
    if not neutral_site:
        why.append({
            "label": f"Home field (+{hfa:.1f} pts)",
            "value": even_hw - 0.5,
        })
    if conditions:
        why.append({"label": "Live conditions", "value": hw - base_hw})

    def _fair(p: float) -> float:
        return round(1.0 / max(p, 1e-6), 2)

    return NFLPrediction(
        home_team=home_code,
        away_team=away_code,
        home_elo=home_elo,
        away_elo=away_elo,
        home_win_prob=hw,
        away_win_prob=1.0 - hw,
        predicted_spread=margin_mu,
        home_cover_prob=hcover,
        away_cover_prob=1.0 - hcover,
        total_points_estimate=total_mu,
        why_factors=why,
        home_expected_pts=home_pts,
        away_expected_pts=away_pts,
        total_line=t_line,
        over_prob=over_p,
        under_prob=1.0 - over_p,
        over_by_line=over_by_line,
        home_team_total_over=_team_over(home_pts),
        away_team_total_over=_team_over(away_pts),
        base_home_win_prob=base_hw,
        base_total_estimate=base_total,
        conditions=conditions,
        fair_odds={
            "home_ml": _fair(hw),
            "away_ml": _fair(1.0 - hw),
            "over": _fair(over_p),
            "under": _fair(1.0 - over_p),
            "home_cover": _fair(hcover),
            "away_cover": _fair(1.0 - hcover),
        },
    )
