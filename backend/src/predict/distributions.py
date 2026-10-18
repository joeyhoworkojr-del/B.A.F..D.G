"""
The distribution a player prop's probability comes out of.

Everything about a prop's price flows from this. A projection is a mean, and
"what is the chance he clears 6.5" is a question about the shape around that
mean, not about the mean itself. Get the shape wrong and a roughly correct
projection still produces prices that are wrong in one direction, every time.

That is what was happening. A symmetric normal was used for every market, and
measured against four seasons of real player games it overstated the over at
every probability above 30%:

    said 43.3%  →  happened 35.0%
    said 53.1%  →  happened 43.6%
    said 64.8%  →  happened 54.3%

Mean absolute calibration error, 8.1 points. The cause is not subtle: rushing
and receiving production is non-negative, lumpy and right-skewed — a player is
inactive, or blanked, or gets three touches, and occasionally has a huge game.
The mean of such a sample sits well above its median, so a symmetric curve
centred on the mean puts half its mass above a number reality clears far less
than half the time. Touchdown markets are worse still, because a normal curve
around 0.4 touchdowns is not a description of anything.

Measured on 142,000 line checks across 2023-2026, mean absolute calibration
error by market and family:

    market            normal   lognormal    gamma   empirical
    pass_yards          2.3p        5.2p     3.7p        4.2p
    pass_attempts       2.9p        4.6p     3.5p        4.4p
    rush_yards          9.4p        2.8p     1.9p        5.1p
    rec_yards           9.9p        3.4p     2.0p        4.7p
    receptions          8.7p        3.4p     2.7p        4.8p
    carries             7.0p        2.5p     2.1p        6.5p
    pass_tds            6.4p        6.9p     4.6p        2.8p
    rush_tds           19.9p        2.3p     2.6p        4.0p
    rec_tds            22.9p        3.1p     4.3p        5.3p

So the choice is per market, and it follows a reason rather than the table: a
starting quarterback plays every down, so his volume is near-symmetric and the
normal fits it best. Everything else is skewed and non-negative, and the gamma
fits that shape. Gamma is chosen over lognormal for the skewed markets even
where lognormal edges it on two thin touchdown markets, because two rules with
a reason behind them generalise better than nine fitted to one sample — and
both are four to ten times better than what they replace.

Reproduce any of this with `python -m tools.backtest props`.
"""
from __future__ import annotations

import math
from typing import Optional

# Which family each market's probability is drawn from. See the measured table
# above; the rule is "passing volume is symmetric, production is not".
NORMAL_MARKETS = frozenset({"pass_yards", "pass_attempts"})


def _norm_sf(x: float, mu: float, sigma: float) -> float:
    """P(X > x) for a normal with this mean and standard deviation."""
    if sigma <= 0:
        return 1.0 if mu > x else 0.0
    return 0.5 * (1.0 - math.erf((x - mu) / (sigma * math.sqrt(2.0))))


def normal_over(line: float, mean: float, sigma: float) -> float:
    return _norm_sf(line, mean, sigma)


def gamma_over(line: float, mean: float, sigma: float) -> Optional[float]:
    """
    P(X > line) for a gamma matched to this mean and standard deviation.

    Via the Wilson-Hilferty transform — the cube root of a gamma variate is
    close to normal — so this needs no special functions and no scipy. Accurate
    well past the precision a published probability is quoted to.

    Returns None where a gamma cannot be fitted (a non-positive mean or spread),
    so the caller can fall back rather than publish a number from nothing.
    """
    if mean <= 0 or sigma <= 0 or line <= 0:
        return None
    shape = (mean / sigma) ** 2
    scale = mean / shape
    if shape <= 0 or scale <= 0:
        return None
    x = line / scale
    denom = math.sqrt(1.0 / (9.0 * shape))
    if denom <= 0:
        return None
    z = ((x / shape) ** (1.0 / 3.0) - (1.0 - 1.0 / (9.0 * shape))) / denom
    return _norm_sf(z, 0.0, 1.0)


def over_probability(
    market: str, line: float, mean: float, sigma: float,
) -> Optional[float]:
    """
    The chance a player clears `line`, from the family that market calibrates
    under.

    The gamma is tried first for skewed markets and the normal is the fallback,
    not the other way round: a fallback that fires silently on the mis-measured
    family would undo the whole point.
    """
    if mean <= 0 or sigma <= 0:
        return None
    if market in NORMAL_MARKETS:
        return normal_over(line, mean, sigma)
    fitted = gamma_over(line, mean, sigma)
    return fitted if fitted is not None else normal_over(line, mean, sigma)


def family_for(market: str) -> str:
    """Which family a market uses, so a page can say so."""
    return "normal" if market in NORMAL_MARKETS else "gamma"
