"""
Edge AI endpoints.

Everything expensive or sensitive is decided here rather than in the browser:
who may ask, how often, and what context travels with the question. The
frontend sends a question and the game it is looking at; it never sends a
prompt, a tool list or a model name, and it never sees the API key.
"""
from __future__ import annotations

import time
from collections import deque
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from src.accounts.entitlements import entitlements_for
from src.accounts.models import User
from src.ai import edge_ai
from src.ai.provider import ProviderUnavailable
from src.api.routes.auth import current_user, require_user

router = APIRouter()

# Every answer costs money, so the ceiling is per account and enforced here.
# Generous enough not to interrupt a real conversation, low enough that a
# scripted loop cannot run up a bill overnight.
RATE_LIMIT_PER_HOUR = 40
RATE_WINDOW_SECONDS = 3600.0

_recent: dict[str, deque[float]] = {}


def _rate_check(user_id: str) -> tuple[bool, int]:
    """(allowed, remaining) for this account in the current window."""
    now = time.monotonic()
    window = _recent.setdefault(user_id, deque())
    while window and now - window[0] > RATE_WINDOW_SECONDS:
        window.popleft()
    if len(window) >= RATE_LIMIT_PER_HOUR:
        return False, 0
    window.append(now)
    return True, RATE_LIMIT_PER_HOUR - len(window)


def reset_rate_limits() -> None:
    _recent.clear()


class Turn(BaseModel):
    role: str = Field(..., max_length=16)
    content: str = Field(..., max_length=edge_ai.MAX_QUESTION_CHARS)


class AskRequest(BaseModel):
    question: str = Field(..., max_length=edge_ai.MAX_QUESTION_CHARS)
    # What the person is looking at, so "why did we move to 64%" resolves
    # without naming the teams again.
    league: Optional[str] = Field(default=None, max_length=12)
    event_id: Optional[str] = Field(default=None, max_length=40)
    history: list[Turn] = Field(default_factory=list)


@router.get("/ai/status", tags=["Edge AI"])
async def ai_status(request: Request) -> dict:
    """
    Whether Edge AI can answer, and for this caller.

    Public, because the UI has to decide whether to offer the feature at all,
    and an honest "not configured yet" is better than a button that fails.
    """
    report = edge_ai.status()
    user = current_user(request)
    ent = entitlements_for(user)
    return {
        "available": report["available"],
        "signed_in": user is not None,
        "may_ask": report["available"] and user is not None,
        "reason": (
            "" if report["available"] and user is not None
            else "Edge AI is not configured on this deployment yet." if not report["available"]
            else "Sign in to ask Edge AI."
        ),
        "rate_limit_per_hour": RATE_LIMIT_PER_HOUR,
        "level": ent.level,
        # The model name is product information, not a secret. The key is never
        # part of this response.
        "model": report.get("model", ""),
        "tools": report.get("tools", []),
    }


@router.post("/ai/ask", tags=["Edge AI"])
async def ask(body: AskRequest, user: User = Depends(require_user)) -> dict:
    """
    Ask Edge AI a question.

    Signing in is required because every answer costs money and the rate limit
    has to attach to somebody. The user id used for any personal lookup comes
    from the session here — the model cannot name an account.
    """
    allowed, remaining = _rate_check(user.id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=(
                f"You have reached {RATE_LIMIT_PER_HOUR} Edge AI questions this "
                "hour. Try again shortly."
            ),
        )

    try:
        answer = await edge_ai.ask(
            body.question,
            ctx=edge_ai.AskContext(
                user_id=user.id,
                league=(body.league or "").lower() or None,
                event_id=body.event_id or None,
            ),
            history=[t.model_dump() for t in body.history],
        )
    except ProviderUnavailable as exc:
        # 503, not 500: nothing is broken, the feature is switched off or the
        # model is briefly unreachable. Either way there is no answer to invent.
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "answer": answer.text,
        # Which lookups the answer rests on, so a reader can see what it is
        # built from rather than taking it on trust.
        "sources_used": sorted(set(answer.tools_used)),
        "truncated": answer.truncated,
        "questions_remaining_this_hour": remaining,
    }
