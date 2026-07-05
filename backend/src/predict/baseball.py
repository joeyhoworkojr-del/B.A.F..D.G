"""
MLB prediction engine — Poisson run-scoring grid.

Baseball scoring is discrete and low — a Poisson grid over runs (like the
soccer engine) fits far better than the Normal-margin model used for
football. Pipeline:

  1. Expected runs per side: offense rating vs opposing run prevention,
     scaled by the home park factor, plus a small home edge.
  2. Live conditions (weather, starting-pitcher availability) scale runs.
  3. P(home i runs, away j runs) grid → win probability (ties resolved as
     extra innings with a 52% home split), totals at ANY line, team totals,
     run-line cover probabilities.

Results are packaged in the shared NFLPrediction shape so the API and UI
treat all three leagues uniformly.
"""
from __future__ import annotations

import math
from typing import Optional

from src.data.mlb import get_mlb_ratings, get_park_factor
from src.predict.gridiron import NFLPrediction

MAX_RUNS = 15          # grid truncation
HOME_EDGE_MULT = 1.03  # small home lift on expected runs
TIE_HOME_SPLIT = 0.52  # extra innings lean slightly home


def _poisson_pmf(lam: float, max_k: int = MAX_RUNS) -> list[float]:
    pmf = []
    p = math.exp(-lam)
    pmf.append(p)
    for k in range(1, max_k + 1):
        p *= lam / k
        pmf.append(p)
    total = sum(pmf)
    return [x / total for x in pmf]


def expected_runs(
    home_code: str,
    away_code: str,
    *,
    neutral_site: bool = False,
    home_elo: Optional[float] = None,
    away_elo: Optional[float] = None,
) -> tuple[float, float]:
    home_off, home_def = get_mlb_ratings(home_code, home_elo)
    away_off, away_def = get_mlb_ratings(away_code, away_elo)
    pf = 1.0 if neutral_site else get_park_factor(home_code)
    home_runs = (home_off + away_def) / 2.0 * pf
    away_runs = (away_off + home_def) / 2.0 * pf
    if not neutral_site:
        home_runs *= HOME_EDGE_MULT
    return home_runs, away_runs


def predict_mlb_game(
    home_code: str,
    away_code: str,
    home_elo: float,
    away_elo: float,
    *,
    neutral_site: bool = False,
    spread_line: Optional[float] = None,   # run line, home-based (-1.5 typical)
    total_line: Optional[float] = None,    # e.g. 8.5
    adjustments: Optional[list] = None,    # list[Adjustment] from live conditions
) -> NFLPrediction:
    base_home, base_away = expected_runs(
        home_code, away_code, neutral_site=neutral_site,
        home_elo=home_elo, away_elo=away_elo,
    )

    conditions = list(adjustments or [])
    home_mu, away_mu = base_home, base_away
    for a in conditions:
        # xg multipliers double as run multipliers; point deltas as run deltas
        home_mu = home_mu * a.home_xg_mult + a.home_pts_delta
        away_mu = away_mu * a.away_xg_mult + a.away_pts_delta
    home_mu = max(1.5, home_mu)
    away_mu = max(1.5, away_mu)

    hp = _poisson_pmf(home_mu)
    ap = _poisson_pmf(away_mu)

    def outcome_probs(hpmf: list[float], apmf: list[float]) -> tuple[float, float]:
        hw = tie = 0.0
        for i, ph in enumerate(hpmf):
            for j, pa in enumerate(apmf):
                if i > j:
                    hw += ph * pa
                elif i == j:
                    tie += ph * pa
        return hw + tie * TIE_HOME_SPLIT, tie

    hw_prob, _ = outcome_probs(hp, ap)
    base_hw_prob, _ = outcome_probs(_poisson_pmf(base_home), _poisson_pmf(base_away))

    # Distribution of total runs
    total_dist = [0.0] * (2 * MAX_RUNS + 1)
    for i, ph in enumerate(hp):
        for j, pa in enumerate(ap):
            total_dist[i + j] += ph * pa

    def p_total_over(line: float) -> float:
        k = int(math.floor(line))
        return sum(total_dist[k + 1:])

    # Margin distribution for run-line covers: P(home - away > -line)
    def p_cover(line: float) -> float:
        p = 0.0
        for i, ph in enumerate(hp):
            for j, pa in enumerate(ap):
                diff = i - j
                if diff + line > 0:
                    p += ph * pa
                elif diff == j - i and diff + line == 0:
                    pass   # push impossible on half lines; ignored on int lines
        return p

    total_mu = home_mu + away_mu
    line = spread_line if spread_line is not None else -(home_mu - away_mu)
    hcover = p_cover(line)

    t_line = total_line if total_line is not None else round(total_mu * 2) / 2
    over_p = p_total_over(t_line)

    center = round(total_mu)
    over_by_line = {
        f"{center + off + 0.5}": p_total_over(center + off + 0.5)
        for off in range(-5, 6)
        if center + off + 0.5 > 0
    }

    def _team_over(pmf: list[float], mu: float) -> dict[str, float]:
        c = max(1, round(mu))
        out = {}
        for off in range(-3, 4):
            ln = c + off + 0.5
            if ln <= 0:
                continue
            out[f"{ln}"] = sum(pmf[int(math.floor(ln)) + 1:])
        return out

    # Why factors
    rating_margin = base_home - base_away
    even_hw, _ = outcome_probs(_poisson_pmf(4.4 * HOME_EDGE_MULT), _poisson_pmf(4.4))
    why = [
        {"label": f"Run ratings ({rating_margin:+.2f} runs)", "value": base_hw_prob - even_hw},
    ]
    if not neutral_site:
        pf = get_park_factor(home_code)
        if abs(pf - 1.0) >= 0.03:
            why.append({"label": f"Park factor ×{pf:.2f}", "value": 0.0})
        why.append({"label": "Home edge (+3% runs, extras lean)", "value": even_hw - 0.5})
    if conditions:
        why.append({"label": "Live conditions", "value": hw_prob - base_hw_prob})

    def _fair(p: float) -> float:
        return round(1.0 / max(p, 1e-6), 2)

    return NFLPrediction(
        home_team=home_code,
        away_team=away_code,
        home_elo=home_elo,
        away_elo=away_elo,
        home_win_prob=hw_prob,
        away_win_prob=1.0 - hw_prob,
        predicted_spread=home_mu - away_mu,
        home_cover_prob=hcover,
        away_cover_prob=1.0 - hcover,
        total_points_estimate=total_mu,
        why_factors=why,
        home_expected_pts=home_mu,
        away_expected_pts=away_mu,
        total_line=t_line,
        over_prob=over_p,
        under_prob=1.0 - over_p,
        over_by_line=over_by_line,
        home_team_total_over=_team_over(hp, home_mu),
        away_team_total_over=_team_over(ap, away_mu),
        base_home_win_prob=base_hw_prob,
        base_total_estimate=base_home + base_away,
        conditions=conditions,
        fair_odds={
            "home_ml": _fair(hw_prob),
            "away_ml": _fair(1.0 - hw_prob),
            "over": _fair(over_p),
            "under": _fair(1.0 - over_p),
            "home_cover": _fair(hcover),
            "away_cover": _fair(1.0 - hcover),
        },
    )
