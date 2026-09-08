"""
Leaderboards and Edge Rating.

Two rules shape this more than any formula.

First, a short sample says nothing. Someone 5-0 is not the best analyst on the
platform, so anyone under the minimum is marked provisional and ranked below
everyone who has cleared it, however good their numbers look.

Second, popularity is not skill. Followers are deliberately absent from the
rating — a large audience does not make a prediction more likely to be right.

The rating itself is intentionally simple: profitability per pick, shrunk
toward the mean by sample size, on a 0-100 scale. It is honest about being a
first version, and `rate()` is the only thing that has to change when a better
one exists.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.accounts.service import get_by_id
from src.picks.service import all_picks, record_for

# Below this, a record is shown but not ranked against established analysts.
MIN_GRADED = 10

# How hard small samples are pulled toward neutral. At K graded picks a record
# carries half its weight, so a hot start moves the rating without owning it.
SHRINK_K = 20

BASELINE = 50.0     # a neutral rating: no evidence either way
SCALE = 120.0       # ROI points to rating points


@dataclass
class Standing:
    user_id: str
    username: str
    display_name: str
    avatar_url: str
    badges: list[str]
    edge_rating: float
    provisional: bool
    graded: int
    wins: int
    losses: int
    pushes: int
    win_rate: Optional[float]
    units: float
    roi_pct: Optional[float]


def rate(units: float, graded: int) -> float:
    """
    Edge Rating, 0-100.

    Profit per graded pick, shrunk toward neutral by sample size. Replace this
    function — not its callers — when there is enough history to calibrate
    something better against closing-line value and confidence.
    """
    if graded <= 0:
        return BASELINE
    roi = units / graded
    confidence = graded / (graded + SHRINK_K)
    return round(max(0.0, min(100.0, BASELINE + roi * SCALE * confidence)), 1)


def standings(league: Optional[str] = None) -> list[Standing]:
    """
    Every analyst with at least one graded pick, best first.

    Provisional analysts sort below established ones regardless of rating, so a
    3-0 start cannot appear above a proven record.
    """
    by_user: dict[str, list] = {}
    for pick in all_picks():
        if league and pick.league != league.lower():
            continue
        by_user.setdefault(pick.user_id, []).append(pick)

    out: list[Standing] = []
    for user_id, picks in by_user.items():
        graded = [p for p in picks if p.graded and p.result != "void"]
        if not graded:
            continue

        user = get_by_id(user_id)
        if user is None or not user.profile_public:
            continue

        wins = sum(1 for p in graded if p.result == "win")
        losses = sum(1 for p in graded if p.result == "loss")
        pushes = sum(1 for p in graded if p.result == "push")
        units = round(sum(p.units for p in graded), 2)
        settled = wins + losses

        out.append(Standing(
            user_id=user_id,
            username=user.username,
            display_name=user.display_name or user.username,
            avatar_url=user.avatar_url,
            badges=user.badges,
            edge_rating=rate(units, len(graded)),
            provisional=len(graded) < MIN_GRADED,
            graded=len(graded), wins=wins, losses=losses, pushes=pushes,
            win_rate=round(wins / settled, 4) if settled else None,
            units=units,
            roi_pct=round(units / len(graded) * 100, 2),
        ))

    out.sort(key=lambda s: (s.provisional, -s.edge_rating, -s.units))
    return out


def user_standing(user_id: str, league: Optional[str] = None) -> Optional[dict]:
    """One analyst's place in the table, with their rank."""
    table = standings(league)
    for rank, s in enumerate(table, start=1):
        if s.user_id == user_id:
            return {**s.__dict__, "rank": rank, "of": len(table)}
    return None
