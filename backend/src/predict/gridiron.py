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
from src.data.ncaaf import get_ncaaf_ratings
from src.data.nfl import get_nfl_ratings
from src.predict import expected_points as ep_model

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
    # College football: bigger talent gaps, more scoring, and blowouts are
    # common, so both the margin and total distributions are wider than the NFL.
    "ncaaf": {
        "ratings": get_ncaaf_ratings,
        "margin_sigma": 16.5,
        "total_sigma": 17.5,
        "team_sigma": 12.5,
        "hfa": 2.6,
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
    home_elo: Optional[float] = None,
    away_elo: Optional[float] = None,
) -> tuple[float, float]:
    """
    Expected points for each side: the average of what the offense usually
    scores and what the opposing defense usually allows, centered on the
    league scoring environment, plus home field.

    `home_elo`/`away_elo` override the teams' static ratings — this is how the
    self-correcting ratings feed the model.
    """
    params = LEAGUE_PARAMS[league]
    home_off, home_def = params["ratings"](home_code, home_elo)
    away_off, away_def = params["ratings"](away_code, away_elo)
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


# ─── Live in-game projection ──────────────────────────────────────────────────

GAME_SECONDS = 3600.0    # 4 × 15:00 regulation (NFL and NCAA)
QUARTER_SECONDS = 900.0


def time_remaining_fraction(period: Optional[int], clock_seconds: float) -> float:
    """Fraction of regulation left, from the period and seconds left in it."""
    if period is None or period <= 0:
        return 1.0
    if period > 4:
        return 0.02   # overtime — essentially no clock left; the margin decides
    elapsed = (period - 1) * QUARTER_SECONDS + (QUARTER_SECONDS - max(0.0, clock_seconds))
    return max(0.0, min(1.0, (GAME_SECONDS - elapsed) / GAME_SECONDS))


# The expected-points curve is calibrated to published anchors, not fitted on
# this season, so its estimate carries model error that the margin sigma knows
# nothing about. Shrinking the possession term toward zero is the honest way to
# price that in: the model still moves before the score does, just not as far
# as a perfectly-known expectation would justify.
DRIVE_VALUE_SHRINK = 0.85


def live_projection(
    *,
    league: str,
    home_score: int,
    away_score: int,
    period: Optional[int],
    clock_seconds: float,
    pregame_margin: float,     # model's pre-game expected home margin (home − away)
    total_estimate: float,     # model's pre-game total points
    home_share: float,         # pre-game share of scoring that is the home team's
    possession_home: Optional[bool] = None,
    yard_line: Optional[int] = None,     # from the possessing team's own goal
    down: Optional[int] = None,
    distance: Optional[int] = None,
) -> dict:
    """
    Update the win probability and projected final score *during* a game.

    Three things decide the projection, in decreasing order of weight as the
    clock runs down: the current margin, the pre-game lean over the time still
    to play, and the expected points of the drive in progress.

    That third term is what makes the model predictive rather than reactive. A
    team on the opponent's 5 with 1st and goal is about five points better off
    than a team that has just taken a kickoff, and those points are in the
    projection now — the number moves as the drive moves, not in a step when
    the touchdown lands.

    The expected-points term needs no separate time weighting. It is already
    denominated in points, and the uncertainty around the remaining margin
    shrinks with the clock, so the same five points barely register in the
    first quarter and are close to decisive in the fourth. That is the correct
    behaviour and it falls out of the model rather than being imposed on it.

    Field position is optional throughout. Without it the possession term is
    zero and this is the scoreboard-and-clock model it has always been.
    """
    m_sigma = LEAGUE_PARAMS[league]["margin_sigma"]
    frac = time_remaining_fraction(period, clock_seconds)
    cur_margin = float(home_score - away_score)

    # Expected final margin = current margin + the pre-game edge, scaled by the
    # share of the game still to play.
    exp_margin = cur_margin + pregame_margin * frac

    drive_value = 0.0
    drive_note = ""
    state: Optional[ep_model.GameState] = None
    if possession_home is not None and yard_line is not None:
        state = ep_model.GameState(
            yard_line=int(yard_line), down=down, distance=distance,
        )
        if state.is_usable():
            drive_value = ep_model.possession_value(state, league) * DRIVE_VALUE_SHRINK
            drive_note = ep_model.describe(state, league)
            exp_margin += drive_value if possession_home else -drive_value
    elif possession_home is not None and frac < 0.25 and abs(cur_margin) <= 8:
        # No field position published. Having the ball late in a close game is
        # still worth something; this is the crude stand-in it always was.
        exp_margin += 1.6 if possession_home else -1.6

    # Remaining-outcome uncertainty shrinks toward zero as the clock empties.
    sigma = max(1.0, m_sigma * math.sqrt(max(frac, 1e-4)))
    hw = win_probability(exp_margin, sigma)

    rem_points = max(0.0, total_estimate) * frac
    # Points the drive in progress is expected to add land on the team that
    # actually has the ball, rather than being split by the pre-game share.
    if state is not None and state.is_usable():
        drive_points = max(0.0, ep_model.expected_points(state, league))
        rem_points = max(0.0, rem_points - drive_points)
        proj_home = home_score + rem_points * home_share
        proj_away = away_score + rem_points * (1.0 - home_share)
        if possession_home:
            proj_home += drive_points
        else:
            proj_away += drive_points
    else:
        proj_home = home_score + rem_points * home_share
        proj_away = away_score + rem_points * (1.0 - home_share)

    return {
        "home_win": hw,
        "away_win": 1.0 - hw,
        "proj_home": round(proj_home, 1),
        "proj_away": round(proj_away, 1),
        "time_remaining_pct": round(frac * 100, 1),
        # Reported so the UI and Edge AI can say *why* the number moved, and so
        # a projection built without field position is distinguishable from one
        # that had it.
        "drive_value": round(drive_value, 2),
        "drive_note": drive_note,
        "state_aware": state is not None and state.is_usable(),
        "red_zone": bool(state.red_zone) if state is not None else False,
        "goal_to_go": bool(state.goal_to_go) if state is not None else False,
    }


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
        home_elo=home_elo, away_elo=away_elo,
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
