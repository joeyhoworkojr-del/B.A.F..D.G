"""
Expected points from football game state.

The live win-probability model used to see only the scoreboard and the clock,
which made it reactive: a team on the opponent's 5 with 1st and goal looked
exactly like a team that had just been stuffed on its own 20, right up until
the touchdown landed and the number jumped. That is backwards. Those seven
points are already very likely; the model should say so *before* they go up.

This module answers one question:

    given down, distance and field position, how many net points is the team
    with the ball expected to score before the other team next scores?

That number — expected points — is what turns a scoreboard reading into a
prediction. `live_projection` adds the possession's expected points to the
current margin, so the projection moves when the game state moves rather than
only when the score does.

The curve is parametric rather than a fitted lookup table. It is calibrated to
published NFL expected-points values at the anchors that matter (own 20, the
midfield mark, the opponent's 20, the goal line), which is enough to get the
*shape* right: field position is worth more the closer it gets, a later down
is worth less, and a long distance to gain is worth less than a short one.

Every function here is pure and total. There is no feed to fail and nothing to
raise: an unknown state produces a neutral value, and the caller falls back to
the scoreboard-only model rather than acting on a fabricated one.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

# Field position is always "yards from the possessing team's own goal line", so
# 0 is their own end zone and 100 is the one they are attacking.
OWN_GOAL = 0
OPP_GOAL = 100

# Expected points on 1st & 10 at these spots, from published NFL values. The
# quadratic below is fitted through them.
#   own 20 → 0.6, midfield → 2.0, opponent 20 → 4.2, goal line → ~6.0
_EP_A = 0.111111
_EP_B = 0.015556
_EP_C = 0.000444

# Backed up against their own goal line, a team is not merely in a bad spot —
# a safety is live and a turnover is a short field. Neither is in the quadratic.
_SAFETY_ZONE = 10.0
_SAFETY_PENALTY = 0.6

# What each down costs relative to 1st, before distance is taken into account.
# 4th is expensive because possession usually changes hands on it; the
# field-goal floor below is what stops that being the whole story in range.
_DOWN_COST = {1: 0.0, 2: 0.45, 3: 1.20, 4: 2.40}

# Distance scales the down cost: 3rd & 1 is nearly a free down, 3rd & 15 is
# close to a punt. Clamped so a 1st & 25 after a penalty stays sane.
_DISTANCE_MIN = 0.35
_DISTANCE_MAX = 1.80

# A drive that starts after a touchback. Used as the neutral reference point —
# the value of *having the ball at all*, which possession alone already implies.
BASELINE_YARD_LINE = 25
BASELINE_DOWN = 1
BASELINE_DISTANCE = 10

# Field goals: distance from the spot to the posts is the yards to the goal
# line plus the end zone and the snap.
_FG_SNAP_AND_ENDZONE = 17
_FG_CENTRE = 52.0      # the distance a kick is a coin flip from
_FG_SCALE = 7.0

# A punt hands the ball over but flips the field, so even 4th & 20 on your own
# 15 is not worth negative points to you — it is worth roughly nothing.
_PUNT_FLOOR = -0.35

# College football is higher scoring and its kickers are less reliable from
# distance; both are scaled rather than modelled separately.
_LEAGUE_EP_SCALE = {"nfl": 1.0, "ncaaf": 1.12, "cfl": 1.05}
_LEAGUE_FG_PENALTY = {"nfl": 0.0, "ncaaf": 4.0, "cfl": 2.0}


def field_goal_probability(yard_line: float, league: str = "nfl") -> float:
    """P(a field goal from this spot is good), as a logistic in kick distance."""
    kick = (OPP_GOAL - _clamp(yard_line, 0, 100)) + _FG_SNAP_AND_ENDZONE
    kick += _LEAGUE_FG_PENALTY.get(league, 0.0)
    return 1.0 / (1.0 + math.exp((kick - _FG_CENTRE) / _FG_SCALE))


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _base_expected_points(yard_line: float) -> float:
    """Expected points on 1st & 10 from this spot, before down/distance."""
    y = _clamp(yard_line, 0.0, 100.0)
    ep = _EP_A + _EP_B * y + _EP_C * y * y
    if y < _SAFETY_ZONE:
        ep -= _SAFETY_PENALTY * (_SAFETY_ZONE - y) / _SAFETY_ZONE
    return ep


def _down_distance_cost(down: int, distance: float, to_end_zone: float) -> float:
    """
    What being on this down, needing this many yards, costs against 1st & 10.

    Both matter and they interact: the penalty for 3rd down is small when a
    yard will do and large when twelve will not.

    Goal-to-go is measured differently. Ordinarily "five to go" is half a
    normal series, but five to go from the five is the *whole* remaining field
    with no room to convert and try again — closer to a long down than a short
    one. Taking the harsher of the two readings is what stops 4th and goal
    from the five being valued like 4th and 5 at midfield.
    """
    base = _DOWN_COST.get(down, 0.0)
    if base == 0.0:
        return 0.0
    scale = distance / 10.0
    if 0 < to_end_zone <= distance:
        scale = max(scale, 0.9 * distance / to_end_zone)
    return base * _clamp(scale, _DISTANCE_MIN, _DISTANCE_MAX)


@dataclass(frozen=True)
class GameState:
    """
    The situation the offence is in.

    `yard_line` is measured from the offence's own goal line, so it means the
    same thing for both teams and needs no home/away convention.
    """
    yard_line: int
    down: Optional[int] = None
    distance: Optional[int] = None

    @property
    def goal_to_go(self) -> bool:
        """True when the end zone is closer than the line to gain."""
        if self.distance is None:
            return False
        return self.distance >= (OPP_GOAL - self.yard_line)

    @property
    def red_zone(self) -> bool:
        return self.yard_line >= 80

    def is_usable(self) -> bool:
        """
        Whether there is enough here to be worth modelling.

        A yard line alone is usable — it is most of the signal. Down and
        distance sharpen it, and their absence is not a reason to fall back to
        the scoreboard.
        """
        return 0 <= self.yard_line <= 100


def expected_points(state: GameState, league: str = "nfl") -> float:
    """
    Net points the offence is expected to score from here before the defence
    next scores.

    Positive throughout most of the field: having the ball is worth something
    almost everywhere. It turns negative only when a team is pinned deep on a
    late down, where a safety or a short field for the opponent is the likelier
    next event.
    """
    if not state.is_usable():
        return 0.0

    y = float(_clamp(state.yard_line, 0, 100))
    down = state.down if state.down in _DOWN_COST else 1
    # You cannot need more yards than there is field left; goal-to-go is what
    # that constraint looks like in the data.
    to_end_zone = OPP_GOAL - y
    distance = float(state.distance) if state.distance is not None else 10.0
    distance = _clamp(distance, 1.0, max(1.0, min(distance, to_end_zone if to_end_zone > 0 else distance)))

    ep = _base_expected_points(y) - _down_distance_cost(down, distance, to_end_zone)

    # On 4th down the drive usually ends here, but ending it in field-goal
    # range is worth about three points times the chance of making it. Without
    # this floor the model would treat 4th & 8 on the opponent's 20 as a
    # disaster rather than as a routine three points.
    if down == 4:
        ep = max(ep, 3.0 * field_goal_probability(y, league) - 0.25)

    # And no situation is worth less than giving the ball away in good field
    # position for the punting team, which is roughly break-even.
    ep = max(ep, _PUNT_FLOOR)

    return ep * _LEAGUE_EP_SCALE.get(league, 1.0)


def baseline_expected_points(league: str = "nfl") -> float:
    """The value of a possession that has just started, after a touchback."""
    return expected_points(
        GameState(BASELINE_YARD_LINE, BASELINE_DOWN, BASELINE_DISTANCE), league,
    )


def possession_value(state: GameState, league: str = "nfl") -> float:
    """
    How much *this* possession is worth over an ordinary one.

    This is the number the win-probability model wants. A team that just took
    a kickoff is at zero — possession is already priced into the pre-game
    projection. A team on the opponent's 5 with 1st and goal is several points
    ahead of that, and those points belong in the projection now rather than
    after the ball crosses the line.
    """
    if not state.is_usable():
        return 0.0
    return expected_points(state, league) - baseline_expected_points(league)


def describe(state: GameState, league: str = "nfl") -> str:
    """
    A plain sentence for why the projection moved, for the UI and for Edge AI.

    Deliberately describes the situation and its value, and claims nothing
    about what will happen.
    """
    if not state.is_usable():
        return ""
    ep = expected_points(state, league)
    value = possession_value(state, league)
    spot = (
        "the goal line" if state.yard_line >= 99
        else f"their own {state.yard_line}" if state.yard_line <= 50
        else f"the opposing {OPP_GOAL - state.yard_line}"
    )
    situation = ""
    if state.down and state.distance:
        label = "goal" if state.goal_to_go else str(state.distance)
        situation = f"{_ordinal(state.down)} & {label} at "
    worth = (
        "well above" if value > 1.5
        else "above" if value > 0.4
        else "below" if value < -0.4
        else "about"
    )
    return (
        f"{situation}{spot} is worth {ep:.1f} expected points — "
        f"{worth} an ordinary possession."
    )


def _ordinal(n: int) -> str:
    return {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}.get(n, f"{n}th")
