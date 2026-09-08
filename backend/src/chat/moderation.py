"""
Who may speak, and what happens when they abuse it.

Everything here is decided server-side. The client can hide a compose box, but
that is a courtesy to the user, never the control: `check_may_post` runs on
every write and is the only thing that decides.

Moderation state is durable, unlike the messages it governs. A mute or a
suspension that evaporated on the next deploy would not be a sanction, and
someone who had been removed for abuse would simply reappear. Reports are
durable for the same reason — staff need to see them after a restart.

The thresholds below are defaults, chosen to be reversible rather than
clever. Every one of them is a number in this file and can be changed without
touching logic.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.store.documents import get_docs

log = logging.getLogger(__name__)

SANCTIONS = "chat_sanctions"
REPORTS = "chat_reports"

# Rate limits, per person. The per-room limit is what stops one game being
# flooded; the global one stops the same person doing it across every game at
# once.
MESSAGES_PER_ROOM_PER_MINUTE = 10
MESSAGES_PER_MINUTE_TOTAL = 25
RATE_WINDOW_SECONDS = 60.0

# Repeating yourself. Identical consecutive messages are the cheapest kind of
# spam and the easiest to catch.
MAX_IDENTICAL_IN_A_ROW = 2

# Tripping the rate limit repeatedly earns a short automatic mute, so a script
# gets slower rather than merely rejected.
FLOOD_STRIKES_BEFORE_MUTE = 3
AUTO_MUTE_MINUTES = 5

# Distinct people, not distinct reports — one person cannot hide a message by
# reporting it repeatedly. At this many, the message is hidden pending review.
# Hidden is not deleted: nobody has judged it yet.
REPORTS_TO_HIDE = 3


class Blocked(PermissionError):
    """Refused, with a reason the composer shows the person verbatim."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(when: datetime) -> str:
    return when.isoformat(timespec="seconds")


@dataclass
class Sanction:
    """A mute or a suspension against one account."""
    user_id: str
    kind: str                    # "mute" | "suspension"
    reason: str = ""
    # Which room a mute applies to. Empty means everywhere.
    game_id: str = ""
    created_at: str = ""
    # None for permanent. A permanent mute is a suspension by another name, so
    # in practice only suspensions use it.
    expires_at: Optional[str] = None
    issued_by: str = "system"

    def active(self, now: Optional[datetime] = None) -> bool:
        if self.expires_at is None:
            return True
        try:
            return datetime.fromisoformat(self.expires_at) > (now or _now())
        except ValueError:
            # An unparseable expiry is treated as expired rather than as
            # permanent: failing open on a sanction is the safer direction for
            # a bug, and staff can always reissue it.
            return False

    def to_doc(self) -> dict:
        return asdict(self)

    @classmethod
    def from_doc(cls, doc: dict) -> "Sanction":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in doc.items() if k in known})


# Rate-limit and repetition state is per-process and deliberately not durable:
# it is a sixty-second window, and losing it on a deploy costs one minute of
# throttling, not a sanction.
_recent: dict[str, deque[float]] = defaultdict(deque)
_recent_in_room: dict[str, deque[float]] = defaultdict(deque)
_last_texts: dict[str, list[str]] = defaultdict(list)
_flood_strikes: dict[str, int] = defaultdict(int)


def _prune(window: deque[float], now: float) -> None:
    while window and now - window[0] > RATE_WINDOW_SECONDS:
        window.popleft()


def _sanction_id(user_id: str, kind: str, game_id: str = "") -> str:
    return f"{user_id}:{kind}:{game_id}" if game_id else f"{user_id}:{kind}"


def sanctions_for(user_id: str) -> list[Sanction]:
    """
    Every sanction on file for an account, expired ones included.

    Scanned rather than indexed: `find` is a unique-index lookup and a user may
    hold several sanctions at once (a global suspension and a per-room mute).
    The collection only ever holds rows for people who have actually been
    sanctioned, so it stays small.
    """
    rows = get_docs().list(SANCTIONS) or []
    return [Sanction.from_doc(r) for r in rows if r.get("user_id") == user_id]


def active_sanction(user_id: str, game_id: str = "") -> Optional[Sanction]:
    """
    The sanction that would stop this person posting here, if any.

    A suspension outranks a mute: it applies everywhere and is the more
    serious finding, so it is the one worth telling them about.
    """
    now = _now()
    live = [s for s in sanctions_for(user_id) if s.active(now)]
    suspension = next((s for s in live if s.kind == "suspension"), None)
    if suspension is not None:
        return suspension
    return next(
        (s for s in live if s.kind == "mute" and s.game_id in ("", game_id)),
        None,
    )


def mute(user_id: str, *, minutes: Optional[int], game_id: str = "",
         reason: str = "", issued_by: str = "system") -> Sanction:
    """Stop someone posting, in one room or everywhere, for a while."""
    sanction = Sanction(
        user_id=user_id, kind="mute", reason=reason, game_id=game_id,
        created_at=_iso(_now()), issued_by=issued_by,
        expires_at=_iso(_now() + timedelta(minutes=minutes)) if minutes else None,
    )
    get_docs().put(SANCTIONS, _sanction_id(user_id, "mute", game_id),
                   sanction.to_doc(), indexes=None)
    return sanction


def suspend(user_id: str, *, days: Optional[int], reason: str = "",
            issued_by: str = "system") -> Sanction:
    """
    Stop someone posting anywhere. `days=None` is permanent.

    Deliberately separate from mute so the two read differently in the record
    and so a permanent sanction has to be asked for explicitly.
    """
    sanction = Sanction(
        user_id=user_id, kind="suspension", reason=reason,
        created_at=_iso(_now()), issued_by=issued_by,
        expires_at=_iso(_now() + timedelta(days=days)) if days else None,
    )
    get_docs().put(SANCTIONS, _sanction_id(user_id, "suspension"),
                   sanction.to_doc(), indexes=None)
    return sanction


def lift(user_id: str, kind: str, game_id: str = "") -> None:
    """Remove a sanction. Idempotent."""
    get_docs().delete(SANCTIONS, _sanction_id(user_id, kind, game_id))


def check_may_post(user_id: str, game_id: str, text: str) -> None:
    """
    The gate every message passes through. Raises Blocked with a reason.

    Ordered cheapest and most serious first: a suspended account is told it is
    suspended rather than being told it is going too fast.
    """
    sanction = active_sanction(user_id, game_id)
    if sanction is not None:
        if sanction.kind == "suspension":
            until = (
                "Your account is suspended from chat."
                if sanction.expires_at is None
                else f"Your account is suspended from chat until {sanction.expires_at}."
            )
            raise Blocked(until)
        raise Blocked(
            "You are muted in this chat."
            if sanction.expires_at is None
            else f"You are muted here until {sanction.expires_at}."
        )

    now = time.monotonic()
    room_key = f"{user_id}:{game_id}"

    _prune(_recent[user_id], now)
    _prune(_recent_in_room[room_key], now)

    over_room = len(_recent_in_room[room_key]) >= MESSAGES_PER_ROOM_PER_MINUTE
    over_total = len(_recent[user_id]) >= MESSAGES_PER_MINUTE_TOTAL
    if over_room or over_total:
        _flood_strikes[user_id] += 1
        if _flood_strikes[user_id] >= FLOOD_STRIKES_BEFORE_MUTE:
            _flood_strikes[user_id] = 0
            mute(user_id, minutes=AUTO_MUTE_MINUTES, game_id=game_id,
                 reason="Automatic: repeated rate-limit breaches")
            raise Blocked(
                f"You have been muted here for {AUTO_MUTE_MINUTES} minutes for "
                "sending messages too quickly."
            )
        raise Blocked("You are sending messages too quickly. Wait a moment.")

    history = _last_texts[room_key]
    if len(history) >= MAX_IDENTICAL_IN_A_ROW and all(t == text for t in history[-MAX_IDENTICAL_IN_A_ROW:]):
        raise Blocked("You have already said that.")


def note_posted(user_id: str, game_id: str, text: str) -> None:
    """Record a successful post, for the limits above."""
    now = time.monotonic()
    room_key = f"{user_id}:{game_id}"
    _recent[user_id].append(now)
    _recent_in_room[room_key].append(now)
    history = _last_texts[room_key]
    history.append(text)
    del history[:-MAX_IDENTICAL_IN_A_ROW]


def report(message_id: str, game_id: str, reporter_id: str, reason: str = "") -> int:
    """
    Record a report and return how many distinct people have made one.

    Keyed by message and reporter, so reporting twice counts once — otherwise
    one person could hide anything they disliked.
    """
    doc_id = f"{message_id}:{reporter_id}"
    get_docs().put(REPORTS, doc_id, {
        "id": doc_id, "message_id": message_id, "game_id": game_id,
        "reporter_id": reporter_id, "reason": (reason or "")[:200],
        "created_at": _iso(_now()), "resolved": False,
    }, indexes=None)
    return reports_on(message_id)


def reports_on(message_id: str) -> int:
    """How many distinct people have reported one message."""
    rows = get_docs().list(REPORTS) or []
    return sum(1 for r in rows if r.get("message_id") == message_id)


def open_reports(limit: int = 100) -> list[dict]:
    """Unresolved reports, newest first, for the staff queue."""
    rows = [r for r in (get_docs().list(REPORTS) or []) if not r.get("resolved")]
    rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return rows[:limit]


def resolve_reports(message_id: str, resolved_by: str) -> int:
    """Mark every report on one message as dealt with."""
    rows = [r for r in (get_docs().list(REPORTS) or [])
            if r.get("message_id") == message_id]
    for row in rows:
        row["resolved"] = True
        row["resolved_by"] = resolved_by
        row["resolved_at"] = _iso(_now())
        get_docs().put(REPORTS, row["id"], row, indexes=None)
    return len(rows)


def reset_rate_state() -> None:
    """Test seam. Does not touch sanctions, which are durable on purpose."""
    _recent.clear()
    _recent_in_room.clear()
    _last_texts.clear()
    _flood_strikes.clear()
