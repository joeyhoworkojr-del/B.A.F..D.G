"""
Grading.

Settles a pick against a final score using the line as it stood when the pick
was made. Pure functions: no storage, no clock, no network — which is what
makes every edge case here directly testable.

Units assume a one-unit stake at the recorded price, defaulting to -110 where
the feed published a line but no price. A push returns the stake; a void is a
no-action that never touches the record.
"""
from __future__ import annotations

from typing import Optional

DEFAULT_PRICE = -110


def _profit(price_american: Optional[int]) -> float:
    """Units won by a one-unit stake at this price."""
    price = price_american if price_american else DEFAULT_PRICE
    return price / 100.0 if price > 0 else 100.0 / abs(price)


def grade_moneyline(side: str, home_score: int, away_score: int) -> str:
    if home_score == away_score:
        return "push"          # a tie settles as a push, not a loss
    winner = "home" if home_score > away_score else "away"
    return "win" if side == winner else "loss"


def grade_spread(side: str, line: Optional[float],
                 home_score: int, away_score: int) -> str:
    """
    `line` is the home side's spread in betting convention: home -3.5 is -3.5.

    Without a recorded line there is nothing to settle against, so the pick is
    voided rather than guessed at.
    """
    if line is None:
        return "void"
    margin = home_score - away_score
    adjusted = margin + line          # home covers when this is positive
    if adjusted == 0:
        return "push"
    home_covered = adjusted > 0
    return "win" if (side == "home") == home_covered else "loss"


def grade_total(side: str, line: Optional[float],
                home_score: int, away_score: int) -> str:
    if line is None:
        return "void"
    total = home_score + away_score
    if total == line:
        return "push"
    return "win" if (side == "over") == (total > line) else "loss"


def settle(market: str, side: str, line: Optional[float],
           home_score: int, away_score: int) -> str:
    if market == "moneyline":
        return grade_moneyline(side, home_score, away_score)
    if market == "spread":
        return grade_spread(side, line, home_score, away_score)
    if market == "total":
        return grade_total(side, line, home_score, away_score)
    return "void"


def units_for(result: str, price_american: Optional[int]) -> float:
    """Units won or lost. Push and void are both zero."""
    if result == "win":
        return round(_profit(price_american), 3)
    if result == "loss":
        return -1.0
    return 0.0
