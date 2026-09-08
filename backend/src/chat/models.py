"""
What a chat message is, and what is allowed to be in one.

Sanitisation happens here, at the edge, before anything is stored. Two rules
shape it:

  * Message text is never HTML and is never rendered as HTML. The client puts
    it in a text node, so escaping is not the defence — not producing markup in
    the first place is.
  * URLs are kept as plain text and are never turned into links. The spec asks
    for malicious links to be prevented; the reliable way to do that is not to
    build a clickable thing out of user input at all. Someone who wants to
    visit a link can copy it, having read it first.
"""
from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

MAX_LENGTH = 500
MAX_NEWLINES = 6

# The reactions people may leave. A closed set, so a "reaction" cannot become a
# second, unmoderated message channel.
REACTIONS = ("👍", "🔥", "😂", "😮", "💀")

# Control and formatting characters that do not belong in a chat line: the C0
# and C1 blocks except newline and tab, plus the bidirectional overrides that
# can make text render in an order other than the one it is stored in.
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f‪-‮⁦-⁩]")
_MANY_NEWLINES = re.compile(r"\n{3,}")
_MANY_SPACES = re.compile(r"[^\S\n]{4,}")


class InvalidMessage(ValueError):
    """Rejected with a reason the composer can show."""


def sanitise(text: str) -> str:
    """
    Clean one message, or refuse it.

    Normalising to NFC first means two visually identical strings compare
    equal, which matters for the flood detector — repeating a line in a
    different normal form is still repeating it.
    """
    if text is None:
        raise InvalidMessage("Write something first.")
    cleaned = unicodedata.normalize("NFC", str(text))
    cleaned = _CONTROL.sub("", cleaned)
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = _MANY_NEWLINES.sub("\n\n", cleaned)
    cleaned = _MANY_SPACES.sub("   ", cleaned)
    cleaned = "\n".join(line.rstrip() for line in cleaned.split("\n")).strip()

    if not cleaned:
        raise InvalidMessage("Write something first.")
    if len(cleaned) > MAX_LENGTH:
        raise InvalidMessage(f"Messages are limited to {MAX_LENGTH} characters.")
    if cleaned.count("\n") > MAX_NEWLINES:
        raise InvalidMessage("That is a lot of line breaks — tighten it up.")
    return cleaned


def game_id(league: str, event_id: str) -> str:
    """
    The chat's key.

    Scoped to the league and the event, so a future Bills-Chiefs game gets its
    own room rather than inheriting an old one's history.
    """
    return f"{(league or '').strip().lower()}:{(event_id or '').strip()}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Message:
    """One line in a game's chat."""
    id: str
    game_id: str
    user_id: str
    username: str
    display_name: str
    avatar_url: str
    text: str
    created_at: str
    # Set when this is a StatEdge system message rather than a person.
    system: bool = False
    # The message being replied to, when there is one.
    reply_to: Optional[str] = None
    reply_preview: str = ""
    # Emoji → number of distinct people who left it.
    reactions: dict[str, int] = field(default_factory=dict)
    # Deleted messages are tombstoned rather than removed, so a reply still has
    # something to point at and so staff can see that a removal happened.
    deleted: bool = False
    deleted_by: str = ""
    # Hidden pending review after enough distinct reports. Not the same as
    # deleted: nobody has judged it yet.
    hidden: bool = False
    reports: int = 0
    # Set by the store on write; the cursor clients page from.
    seq: int = 0

    @classmethod
    def new(cls, **kwargs) -> "Message":
        return cls(id=uuid.uuid4().hex, created_at=_now(), **kwargs)

    def to_doc(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_doc(cls, doc: dict) -> "Message":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in doc.items() if k in known})

    def to_public(self, viewer_id: str = "") -> dict[str, Any]:
        """
        What a reader may see.

        A deleted or hidden message keeps its place in the sequence but loses
        its text — removing the row outright would renumber everyone else's
        cursor and make a reply point at nothing.
        """
        withheld = self.deleted or self.hidden
        return {
            "id": self.id,
            "seq": self.seq,
            "user_id": "" if self.system else self.user_id,
            "username": self.username,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "text": "" if withheld else self.text,
            "created_at": self.created_at,
            "system": self.system,
            "reply_to": self.reply_to,
            "reply_preview": "" if withheld else self.reply_preview,
            "reactions": dict(self.reactions),
            "deleted": self.deleted,
            "hidden": self.hidden,
            "mine": bool(viewer_id) and viewer_id == self.user_id and not self.system,
        }
