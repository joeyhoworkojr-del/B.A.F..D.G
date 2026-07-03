"""
Betting value engine — odds conversion, vig removal, expected value, Kelly.

All probabilities are decimals in [0, 1]. Odds helpers accept American
(e.g. -150, +240) or decimal (e.g. 1.67, 3.40) formats.

The edge pipeline:
  1. Convert quoted odds to implied probabilities.
  2. Strip the bookmaker's vig (proportional method) to get market probs.
  3. Compare model probability vs no-vig market probability → edge.
  4. Compute EV per unit staked and a fractional-Kelly stake suggestion.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ─── Odds conversions ─────────────────────────────────────────────────────────

def american_to_decimal(american: float) -> float:
    if american == 0:
        raise ValueError("American odds cannot be 0")
    if american > 0:
        return 1.0 + american / 100.0
    return 1.0 + 100.0 / abs(american)


def decimal_to_american(decimal_odds: float) -> float:
    if decimal_odds <= 1.0:
        raise ValueError("Decimal odds must be > 1.0")
    if decimal_odds >= 2.0:
        return (decimal_odds - 1.0) * 100.0
    return -100.0 / (decimal_odds - 1.0)


def implied_probability(decimal_odds: float) -> float:
    if decimal_odds <= 1.0:
        raise ValueError("Decimal odds must be > 1.0")
    return 1.0 / decimal_odds


def normalize_odds(value: float, odds_format: str = "decimal") -> float:
    """Return decimal odds regardless of the input format."""
    if odds_format == "american":
        return american_to_decimal(value)
    if odds_format == "decimal":
        if value <= 1.0:
            raise ValueError(f"Decimal odds must be > 1.0, got {value}")
        return value
    raise ValueError(f"Unknown odds format: {odds_format!r}")


def fair_decimal_odds(probability: float) -> float:
    """The break-even decimal odds for a probability."""
    p = min(max(probability, 1e-6), 1 - 1e-9)
    return 1.0 / p


# ─── Vig removal ──────────────────────────────────────────────────────────────

def remove_vig(implied_probs: list[float]) -> list[float]:
    """
    Proportional (multiplicative) vig removal across a full market.
    Input: raw implied probabilities (sum > 1 due to overround).
    Output: fair probabilities summing to 1.
    """
    total = sum(implied_probs)
    if total <= 0:
        raise ValueError("Implied probabilities must be positive")
    return [p / total for p in implied_probs]


def overround(implied_probs: list[float]) -> float:
    """Bookmaker margin: sum of implied probs minus 1 (e.g. 0.05 = 5% vig)."""
    return sum(implied_probs) - 1.0


# ─── Value metrics ────────────────────────────────────────────────────────────

def expected_value(model_prob: float, decimal_odds: float) -> float:
    """EV per 1 unit staked: p·(odds−1) − (1−p)."""
    return model_prob * (decimal_odds - 1.0) - (1.0 - model_prob)


def kelly_fraction(
    model_prob: float,
    decimal_odds: float,
    *,
    fraction: float = 0.25,
) -> float:
    """
    Fractional Kelly stake as a share of bankroll (quarter-Kelly default —
    full Kelly is far too volatile given model uncertainty). Never negative.
    """
    b = decimal_odds - 1.0
    if b <= 0:
        return 0.0
    full = (model_prob * b - (1.0 - model_prob)) / b
    return max(0.0, full * fraction)


def edge_rating(edge_pp: float) -> str:
    """Bucket an edge (in percentage points) into a confidence grade."""
    if edge_pp >= 6.0:
        return "A"
    if edge_pp >= 3.5:
        return "B"
    if edge_pp >= 1.5:
        return "C"
    return "-"


# ─── Market evaluation ────────────────────────────────────────────────────────

@dataclass
class BetEdge:
    market: str            # e.g. "1X2", "Total 2.5", "Spread -3.5", "Moneyline"
    selection: str         # e.g. "ARG win", "Over 2.5"
    model_prob: float
    implied_prob: float    # raw, vig included
    market_prob: float     # no-vig fair probability
    decimal_odds: float
    fair_odds: float       # model's break-even odds
    edge_pp: float         # (model − no-vig market) × 100
    ev_per_unit: float
    kelly_stake: float     # fraction of bankroll (quarter-Kelly)
    rating: str            # "A" | "B" | "C" | "-"


def evaluate_market(
    market: str,
    selections: list[tuple[str, float, Optional[float]]],
    *,
    odds_format: str = "decimal",
    kelly_frac: float = 0.25,
) -> list[BetEdge]:
    """
    Evaluate one market. `selections` = [(name, model_prob, quoted_odds)].
    Selections with no quoted odds are skipped for edge math but the market's
    vig is computed only from the priced selections that form a full book.
    """
    priced = [(n, p, o) for n, p, o in selections if o is not None]
    if not priced:
        return []

    decimals = [normalize_odds(o, odds_format) for _, _, o in priced]
    implieds = [implied_probability(d) for d in decimals]

    # Only strip vig when the priced selections plausibly form a full market
    if len(priced) >= 2 and sum(implieds) > 1.0:
        fair = remove_vig(implieds)
    else:
        fair = implieds

    out: list[BetEdge] = []
    for (name, model_p, _), dec, imp, mkt_p in zip(priced, decimals, implieds, fair):
        edge = (model_p - mkt_p) * 100.0
        out.append(BetEdge(
            market=market,
            selection=name,
            model_prob=model_p,
            implied_prob=imp,
            market_prob=mkt_p,
            decimal_odds=dec,
            fair_odds=fair_decimal_odds(model_p),
            edge_pp=edge,
            ev_per_unit=expected_value(model_p, dec),
            kelly_stake=kelly_fraction(model_p, dec, fraction=kelly_frac),
            rating=edge_rating(edge),
        ))
    out.sort(key=lambda e: -e.edge_pp)
    return out
