"""
User predictions.

A pick is a claim, timestamped before an event starts, that becomes immutable
the moment it does. That immutability is the entire product: a track record
only means something if nobody could have edited a losing pick afterwards.

Everything here is stored as submitted. The line and the price are captured at
submission time and never refreshed, because grading a pick against a line that
moved after it was made would flatter or punish it for something the analyst
never saw.
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

COLLECTION = "picks"

MARKETS = ("moneyline", "spread", "total")
SIDES = ("home", "away", "over", "under")

RESULTS = ("pending", "live", "win", "loss", "push", "void")

MIN_CONFIDENCE, MAX_CONFIDENCE = 50, 99
MAX_REASONING = 2000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class PickError(ValueError):
    """Rejected with a message the form can show."""


@dataclass
class Pick:
    id: str
    user_id: str
    username: str                  # denormalised so profiles render in one read
    game_id: str                   # "{league}:{event_id}"
    league: str
    event_id: str
    home: str
    away: str
    market: str                    # moneyline | spread | total
    side: str                      # home | away | over | under
    selection: str                 # human-readable, e.g. "Buffalo -3.5"
    line: Optional[float] = None   # as it stood when the pick was made
    price_american: Optional[int] = None
    odds_source: str = ""
    confidence: int = 60
    reasoning: str = ""
    kickoff: str = ""              # ISO-8601; the lock boundary
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    # Grading
    result: str = "pending"
    units: float = 0.0
    graded_at: str = ""
    final_home: Optional[int] = None
    final_away: Optional[int] = None

    @staticmethod
    def new(**kw) -> "Pick":
        return Pick(id=uuid.uuid4().hex, **kw)

    # ── lock state ───────────────────────────────────────────────────────────

    def is_locked(self, now: Optional[datetime] = None) -> bool:
        """
        True once the event has started.

        An unparseable kickoff locks the pick rather than leaving it open: a
        bad timestamp must not become a way to edit a pick during a game.
        """
        if not self.kickoff:
            return True
        try:
            start = datetime.fromisoformat(self.kickoff.replace("Z", "+00:00"))
        except ValueError:
            return True
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        return (now or datetime.now(timezone.utc)) >= start

    @property
    def graded(self) -> bool:
        return self.result in ("win", "loss", "push", "void")

    # ── serialisation ────────────────────────────────────────────────────────

    def to_doc(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_doc(doc: dict[str, Any]) -> "Pick":
        known = set(Pick.__dataclass_fields__)
        return Pick(**{k: v for k, v in doc.items() if k in known})

    def to_public(self, now: Optional[datetime] = None) -> dict[str, Any]:
        return {
            **asdict(self),
            "locked": self.is_locked(now),
            "graded": self.graded,
        }


def validate_confidence(value: Any) -> int:
    try:
        confidence = int(value)
    except (TypeError, ValueError) as exc:
        raise PickError("Confidence must be a number.") from exc
    if not MIN_CONFIDENCE <= confidence <= MAX_CONFIDENCE:
        # Below 50 is a pick on the other side; 100 is not a probability
        # anyone should be able to claim.
        raise PickError(f"Confidence must be between {MIN_CONFIDENCE} and {MAX_CONFIDENCE}.")
    return confidence


def validate_market(market: str, side: str) -> tuple[str, str]:
    market = (market or "").strip().lower()
    side = (side or "").strip().lower()
    if market not in MARKETS:
        raise PickError(f"Market must be one of: {', '.join(MARKETS)}.")
    allowed = ("over", "under") if market == "total" else ("home", "away")
    if side not in allowed:
        raise PickError(f"For {market}, pick one of: {', '.join(allowed)}.")
    return market, side
