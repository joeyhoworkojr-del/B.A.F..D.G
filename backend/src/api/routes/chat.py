"""
Live game chat.

Two transports, on purpose. `/chat/{league}/{event_id}/stream` is Server-Sent
Events and is what a browser uses when it can; `/chat/{league}/{event_id}`
returns everything after a cursor and is what it falls back to. The fallback
exists because statedge.ca serves the SPA from Vercel and proxies /api to Fly,
and a proxy that buffers a streaming response turns a live chat into a dead
one. Rather than bet the feature on that behaviour, the client tries the stream
and drops to polling if it does not arrive.

Polling here is not the thing the spec warns against. A poll carries the
sequence number the client already has and reads a capped list, so a quiet room
costs one comparison and returns nothing.
"""
from __future__ import annotations

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.accounts.models import User
from src.chat import moderation, service
from src.chat.models import MAX_LENGTH, REACTIONS, InvalidMessage
from src.api.routes.auth import current_user, require_moderator, require_user

router = APIRouter()

# How often the stream checks for new messages. Fast enough to feel live,
# slow enough that a hundred open rooms is not a hundred busy loops.
STREAM_TICK_SECONDS = 1.5

# A stream is closed and reconnected periodically. Proxies drop long-lived
# connections anyway, and a client that reconnects with its cursor loses
# nothing — whereas one that believes a dead connection is alive misses
# everything.
STREAM_MAX_SECONDS = 600


class PostMessage(BaseModel):
    text: str = Field(..., max_length=MAX_LENGTH * 2)
    reply_to: Optional[str] = Field(default=None, max_length=64)


class Reaction(BaseModel):
    emoji: str = Field(..., max_length=8)


class ReportMessage(BaseModel):
    reason: str = Field(default="", max_length=200)


class Sanction(BaseModel):
    user_id: str = Field(..., max_length=64)
    reason: str = Field(default="", max_length=200)
    minutes: Optional[int] = Field(default=None, ge=1, le=60 * 24 * 30)
    days: Optional[int] = Field(default=None, ge=1, le=3650)
    game_id: str = Field(default="", max_length=80)


def _blocked(exc: moderation.Blocked) -> HTTPException:
    # 403 with the reason shown verbatim: someone who is muted should be told
    # they are muted and until when, not left guessing why nothing sends.
    return HTTPException(status_code=403, detail=str(exc))


@router.get("/chat/{league}/{event_id}", tags=["Chat"])
async def read_chat(
    league: str, event_id: str, request: Request, after: int = 0,
) -> dict:
    """
    Messages after a cursor. Readable signed out — chat is part of the game
    page, and requiring an account to read would hide the room from the people
    most likely to join it.
    """
    viewer = current_user(request)
    payload = service.since(league, event_id, after, viewer)
    sanction = (
        moderation.active_sanction(viewer.id, payload["game_id"]) if viewer else None
    )
    return {
        **payload,
        "signed_in": viewer is not None,
        "may_post": viewer is not None and sanction is None,
        "blocked_reason": (
            "" if viewer is None or sanction is None
            else f"You are {'suspended from chat' if sanction.kind == 'suspension' else 'muted here'}"
                 + (f" until {sanction.expires_at}." if sanction.expires_at else ".")
        ),
        "reactions_available": list(REACTIONS),
    }


@router.get("/chat/{league}/{event_id}/stream", tags=["Chat"])
async def stream_chat(league: str, event_id: str, request: Request, after: int = 0):
    """
    Server-Sent Events for one room.

    Sends a comment line immediately so a proxy that buffers reveals itself
    fast, and a heartbeat between messages so an idle connection is not mistaken
    for a broken one.
    """
    viewer = current_user(request)
    viewer_id = viewer.id if viewer else ""

    async def events():
        cursor = after
        started = asyncio.get_event_loop().time()
        yield ": connected\n\n"
        while True:
            if await request.is_disconnected():
                return
            if asyncio.get_event_loop().time() - started > STREAM_MAX_SECONDS:
                # Tell the client to come back with its cursor rather than
                # letting a proxy sever this silently.
                yield f"event: reconnect\ndata: {json.dumps({'cursor': cursor})}\n\n"
                return
            try:
                payload = service.since(league, event_id, cursor, viewer)
            except Exception:
                yield ": error\n\n"
                await asyncio.sleep(STREAM_TICK_SECONDS)
                continue
            messages = payload["messages"]
            if messages:
                cursor = payload["cursor"]
                yield f"data: {json.dumps({'messages': messages, 'cursor': cursor})}\n\n"
            else:
                yield ": keep-alive\n\n"
            await asyncio.sleep(STREAM_TICK_SECONDS)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            # Nginx and several proxies honour this and stop buffering.
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/{league}/{event_id}", tags=["Chat"])
async def post_message(
    league: str, event_id: str, body: PostMessage, user: User = Depends(require_user),
) -> dict:
    """Say something. Signing in is required; the moderation gate runs here."""
    try:
        message = service.post(user, league, event_id, body.text, body.reply_to)
    except InvalidMessage as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except moderation.Blocked as exc:
        raise _blocked(exc) from exc
    return {"message": message.to_public(user.id)}


@router.post("/chat/{league}/{event_id}/{message_id}/react", tags=["Chat"])
async def react(
    league: str, event_id: str, message_id: str, body: Reaction,
    user: User = Depends(require_user),
) -> dict:
    try:
        message = service.react(user, league, event_id, message_id, body.emoji)
    except InvalidMessage as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except service.NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"message": message.to_public(user.id)}


@router.delete("/chat/{league}/{event_id}/{message_id}", tags=["Chat"])
async def delete_message(
    league: str, event_id: str, message_id: str, user: User = Depends(require_user),
) -> dict:
    try:
        message = service.delete(user, league, event_id, message_id)
    except service.NotAllowed as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except service.NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"message": message.to_public(user.id)}


@router.post("/chat/{league}/{event_id}/{message_id}/report", tags=["Chat"])
async def report_message(
    league: str, event_id: str, message_id: str, body: ReportMessage,
    user: User = Depends(require_user),
) -> dict:
    try:
        return service.report(user, league, event_id, message_id, body.reason)
    except service.NotAllowed as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except service.NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── Moderation. Writes, so these are gated on the moderate power, and they are
#    on this router rather than the admin one, which stays read-only.
#
#    Their own path prefix, not /chat/moderation/...: that would be two
#    segments after /chat and would be matched by /chat/{league}/{event_id}
#    first, so "GET the report queue" would silently become "read the chat for
#    a league called moderation". ────────────────────────────────────────────

@router.get("/chat-moderation/reports", tags=["Chat moderation"])
async def list_reports(staff: User = Depends(require_moderator)) -> dict:
    """The open report queue."""
    return {"reports": moderation.open_reports()}


@router.post("/chat-moderation/mute", tags=["Chat moderation"])
async def mute_user(body: Sanction, staff: User = Depends(require_moderator)) -> dict:
    sanction = moderation.mute(
        body.user_id, minutes=body.minutes, game_id=body.game_id,
        reason=body.reason, issued_by=staff.username,
    )
    return {"sanction": sanction.to_doc()}


@router.post("/chat-moderation/suspend", tags=["Chat moderation"])
async def suspend_user(body: Sanction, staff: User = Depends(require_moderator)) -> dict:
    """`days` omitted means permanent — asked for explicitly, never by default."""
    sanction = moderation.suspend(
        body.user_id, days=body.days, reason=body.reason, issued_by=staff.username,
    )
    return {"sanction": sanction.to_doc()}


@router.post("/chat-moderation/lift", tags=["Chat moderation"])
async def lift_sanction(
    body: Sanction, kind: str = "mute", staff: User = Depends(require_moderator),
) -> dict:
    if kind not in ("mute", "suspension"):
        raise HTTPException(status_code=422, detail="kind must be mute or suspension")
    moderation.lift(body.user_id, kind, body.game_id)
    return {"lifted": True, "user_id": body.user_id, "kind": kind}


@router.post("/chat-moderation/{league}/{event_id}/{message_id}/restore", tags=["Chat moderation"])
async def restore_message(
    league: str, event_id: str, message_id: str, staff: User = Depends(require_moderator),
) -> dict:
    """Un-hide a message that was reported but is fine."""
    try:
        message = service.restore(staff, league, event_id, message_id)
    except service.NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"message": message.to_public(staff.id)}
