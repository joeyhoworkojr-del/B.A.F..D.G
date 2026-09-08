"""
Chat operations, and who is allowed to perform them.

Every write goes through here rather than through a route, so authorization
lives in one place. The rules:

  * Posting requires an account, and passes the moderation gate.
  * You may delete your own message. Staff may delete anyone's.
  * Reactions are one per person per emoji, from a closed set.
  * Reporting is anonymous to other users and idempotent per person.

A deleted message is tombstoned, not removed. Removing the row would renumber
the cursor everyone is paging from and leave replies pointing at nothing.
"""
from __future__ import annotations

import logging
from typing import Optional

from src.accounts.models import User, has_power
from src.chat import moderation
from src.chat.models import (
    REACTIONS, InvalidMessage, Message, game_id as make_game_id, sanitise,
)
from src.chat.store import get_rooms

log = logging.getLogger(__name__)

# How many messages one read may return. A client that has been away for an
# hour gets the most recent window rather than the whole room.
PAGE = 100

# Reactions are stored as a set of user ids per emoji so a person cannot inflate
# a count, but only the totals are published.
_reactors: dict[str, dict[str, set[str]]] = {}


class NotAllowed(PermissionError):
    """The caller may not do this."""


class NotFound(LookupError):
    """No such message."""


def post(
    user: User, league: str, event_id: str, text: str,
    reply_to: Optional[str] = None,
) -> Message:
    """Add a message to a game's chat."""
    gid = make_game_id(league, event_id)
    clean = sanitise(text)
    # Raises Blocked, which the route reports as 403 with the reason shown.
    moderation.check_may_post(user.id, gid, clean)

    rooms = get_rooms()
    preview = ""
    if reply_to:
        parent = rooms.get(gid, reply_to)
        if parent is None:
            # A reply to something that has scrolled out of the window becomes
            # an ordinary message rather than an error — the person's words are
            # worth more than the thread link.
            reply_to = None
        elif not (parent.deleted or parent.hidden):
            preview = parent.text[:80]

    message = Message.new(
        game_id=gid, user_id=user.id, username=user.username,
        display_name=user.display_name or user.username,
        avatar_url=user.avatar_url, text=clean,
        reply_to=reply_to, reply_preview=preview,
    )
    rooms.append(message)
    moderation.note_posted(user.id, gid, clean)
    return message


def system_message(league: str, event_id: str, text: str) -> Message:
    """
    A StatEdge message. Not attributable to a person and not rate limited,
    because nothing user-controlled reaches it — see events.py for what may
    trigger one.
    """
    gid = make_game_id(league, event_id)
    message = Message.new(
        game_id=gid, user_id="", username="statedge",
        display_name="Stat Edge", avatar_url="", text=text.strip()[:400],
        system=True,
    )
    return get_rooms().append(message)


def since(league: str, event_id: str, after: int = 0, viewer: Optional[User] = None) -> dict:
    """
    Everything after a cursor.

    `after=0` returns the most recent window rather than the whole history, so
    opening a busy room is one bounded read.
    """
    gid = make_game_id(league, event_id)
    rooms = get_rooms()
    messages = rooms.latest(gid, PAGE) if after <= 0 else rooms.since(gid, after, PAGE)
    viewer_id = viewer.id if viewer else ""
    return {
        "game_id": gid,
        "messages": [m.to_public(viewer_id) for m in messages],
        "cursor": messages[-1].seq if messages else after,
        "count": rooms.count(gid),
    }


def _load(gid: str, message_id: str) -> Message:
    message = get_rooms().get(gid, message_id)
    if message is None:
        raise NotFound("That message is no longer here.")
    return message


def react(user: User, league: str, event_id: str, message_id: str, emoji: str) -> Message:
    """Toggle one reaction. A closed set, so this cannot become a second channel."""
    if emoji not in REACTIONS:
        raise InvalidMessage("That is not a reaction you can leave.")
    gid = make_game_id(league, event_id)
    message = _load(gid, message_id)

    per_message = _reactors.setdefault(message_id, {})
    people = per_message.setdefault(emoji, set())
    if user.id in people:
        people.discard(user.id)
    else:
        people.add(user.id)

    if people:
        message.reactions[emoji] = len(people)
    else:
        message.reactions.pop(emoji, None)
    get_rooms().replace(message)
    return message


def delete(user: User, league: str, event_id: str, message_id: str) -> Message:
    """Remove a message's text. Yours always; anyone's with the moderate power."""
    gid = make_game_id(league, event_id)
    message = _load(gid, message_id)
    is_staff = has_power(user.level, "moderate")
    if message.user_id != user.id and not is_staff:
        raise NotAllowed("You can only delete your own messages.")
    if message.system and not is_staff:
        raise NotAllowed("That message is not yours to delete.")

    message.deleted = True
    message.deleted_by = "staff" if is_staff and message.user_id != user.id else "author"
    get_rooms().replace(message)
    if is_staff:
        moderation.resolve_reports(message_id, user.id)
    return message


def report(user: User, league: str, event_id: str, message_id: str, reason: str = "") -> dict:
    """
    Flag a message for staff.

    Enough distinct reporters hides it pending review. Hidden is not deleted —
    nobody has judged it yet, and a mob should not be able to erase something
    outright.
    """
    gid = make_game_id(league, event_id)
    message = _load(gid, message_id)
    if message.user_id == user.id:
        raise NotAllowed("You cannot report your own message.")

    count = moderation.report(message_id, gid, user.id, reason)
    message.reports = count
    if count >= moderation.REPORTS_TO_HIDE and not message.hidden:
        message.hidden = True
    get_rooms().replace(message)
    return {
        "reported": True,
        "hidden": message.hidden,
        "note": (
            "Hidden pending staff review."
            if message.hidden
            else "Thanks — staff will take a look."
        ),
    }


def restore(user: User, league: str, event_id: str, message_id: str) -> Message:
    """Staff: un-hide a message that was reported but is fine."""
    if not has_power(user.level, "moderate"):
        raise NotAllowed("Not found")
    gid = make_game_id(league, event_id)
    message = _load(gid, message_id)
    message.hidden = False
    message.deleted = False
    get_rooms().replace(message)
    moderation.resolve_reports(message_id, user.id)
    return message


def reset_reactions() -> None:
    _reactors.clear()
