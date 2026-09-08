"""
What Edge AI is allowed to cost.

The per-user rate limit bounds one person's questions. It does not bound the
bill: a hundred people at forty questions an hour is ninety-six thousand
answers a day, and nothing in the rate limiter objects. This module is the
thing that does.

Spend is tracked per UTC day and stored durably. A cap that reset on every
deploy would not be a cap — the busiest day is exactly when a deploy is most
likely, and "we shipped a fix and the budget started over" is not a control.

Cost is estimated from the token counts the API returns, priced from a table
here. That makes it an estimate rather than a bill: prices change, and this
file is not the billing system. It is deliberately conservative — the point is
to stop a runaway, not to reconcile an invoice.
"""
from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from src.store.documents import get_docs

log = logging.getLogger(__name__)

COLLECTION = "ai_usage"

# US dollars per million tokens, input/output. Used only to estimate spend
# against the cap; the real figure comes from the provider's own billing.
PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-5": (5.0, 25.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-haiku-4-5": (1.0, 5.0),
}

# A model not in the table is priced at the most expensive one we know about,
# so an unrecognised name cannot quietly buy an unlimited budget.
_FALLBACK_PRICE = (5.0, 25.0)

# The daily ceiling. Deliberately low: the failure mode of too-low is "Edge AI
# is off today", which is recoverable and visible. The failure mode of too-high
# is an invoice nobody saw coming.
#
# At this cap on the default model that is roughly 330 answers a day — far more
# than beta traffic, and a hard stop on any runaway.
DEFAULT_DAILY_USD = 2.0
ENV_VAR = "EDGE_AI_DAILY_USD"

_LOCK = threading.Lock()


def daily_limit() -> float:
    raw = (os.getenv(ENV_VAR) or "").strip()
    if not raw:
        return DEFAULT_DAILY_USD
    try:
        value = float(raw)
    except ValueError:
        log.warning("%s is not a number; using the default", ENV_VAR)
        return DEFAULT_DAILY_USD
    # Zero is a legitimate setting: it switches Edge AI off without removing
    # the key. Negative is a typo, and is treated as zero rather than as
    # unlimited — the safe reading of a mistake.
    return max(0.0, value)


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    in_price, out_price = PRICING.get(model, _FALLBACK_PRICE)
    return (input_tokens * in_price + output_tokens * out_price) / 1_000_000


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


@dataclass
class Usage:
    day: str
    answers: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_usd: float = 0.0

    def to_doc(self) -> dict:
        return {
            "id": self.day, "day": self.day, "answers": self.answers,
            "input_tokens": self.input_tokens, "output_tokens": self.output_tokens,
            "estimated_usd": round(self.estimated_usd, 6),
        }

    @classmethod
    def from_doc(cls, doc: dict) -> "Usage":
        return cls(
            day=doc.get("day") or doc.get("id") or _today(),
            answers=int(doc.get("answers") or 0),
            input_tokens=int(doc.get("input_tokens") or 0),
            output_tokens=int(doc.get("output_tokens") or 0),
            estimated_usd=float(doc.get("estimated_usd") or 0.0),
        )


def _load(day: Optional[str] = None) -> Usage:
    day = day or _today()
    try:
        doc = get_docs().get(COLLECTION, day)
    except Exception as exc:
        log.warning("Edge AI usage read failed: %s", type(exc).__name__)
        doc = None
    return Usage.from_doc(doc) if doc else Usage(day=day)


def spent_today() -> float:
    return _load().estimated_usd


def remaining_today() -> float:
    return max(0.0, daily_limit() - spent_today())


def within_budget() -> bool:
    """
    Whether another answer may be paid for.

    Checked before the request, so the cap is a gate rather than a report. A
    single answer can push spend slightly past the limit — the alternative is
    refusing to answer until certain, which would mean rejecting the last
    question of every day.
    """
    return remaining_today() > 0.0


def record(model: str, input_tokens: int, output_tokens: int) -> Usage:
    """
    Add one answer to today's total.

    Never raises. A usage write that failed must not lose the answer the person
    already received — but it does mean the cap under-counts, which is why the
    staff page reports the store's health alongside the number.
    """
    cost = estimate_cost(model, input_tokens, output_tokens)
    with _LOCK:
        usage = _load()
        usage.answers += 1
        usage.input_tokens += max(0, input_tokens)
        usage.output_tokens += max(0, output_tokens)
        usage.estimated_usd += cost
        try:
            get_docs().put(COLLECTION, usage.day, usage.to_doc(), indexes=None)
        except Exception as exc:
            log.warning("Edge AI usage write failed: %s", type(exc).__name__)
        return usage


def history(days: int = 14) -> list[dict]:
    """Recent daily usage, newest first, for the staff page."""
    try:
        rows = get_docs().list(COLLECTION) or []
    except Exception:
        return []
    rows.sort(key=lambda r: r.get("day") or "", reverse=True)
    return rows[:days]


def status() -> dict:
    """Today's spend against the cap. No credentials, ever."""
    usage = _load()
    limit = daily_limit()
    return {
        "day": usage.day,
        "answers_today": usage.answers,
        "estimated_usd_today": round(usage.estimated_usd, 4),
        "daily_limit_usd": limit,
        "remaining_usd": round(max(0.0, limit - usage.estimated_usd), 4),
        "within_budget": usage.estimated_usd < limit,
        "limit_env_var": ENV_VAR,
        # An estimate priced from a local table, not a bill. Said plainly so
        # nobody reconciles this against an invoice and finds it wrong.
        "note": "Estimated from token counts, not billed amounts.",
    }
