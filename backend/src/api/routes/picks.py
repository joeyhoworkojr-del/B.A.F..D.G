"""
User prediction routes.

Identity comes from the session on every call. No endpoint accepts a user id
from the caller, and no endpoint trusts the client's view of whether a game has
started — both are resolved server-side, which is what the "verified record"
claim rests on.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from src.accounts.entitlements import entitlements_for
from src.accounts.models import User
from src.accounts.service import get_by_username
from src.api.routes.auth import current_user, require_user
from src.picks import service
from src.picks.models import PickError

router = APIRouter()


class SubmitPick(BaseModel):
    league: str = Field(..., max_length=16)
    event_id: str = Field(..., max_length=64)
    home: str = Field(..., max_length=80)
    away: str = Field(..., max_length=80)
    kickoff: str = Field(..., max_length=40)
    market: str = Field(..., max_length=16)
    side: str = Field(..., max_length=8)
    selection: str = Field(..., max_length=120)
    line: Optional[float] = None
    price_american: Optional[int] = None
    odds_source: str = Field(default="", max_length=40)
    confidence: int = 60
    reasoning: str = Field(default="", max_length=2000)


class EditPick(BaseModel):
    side: Optional[str] = Field(default=None, max_length=8)
    selection: Optional[str] = Field(default=None, max_length=120)
    confidence: Optional[int] = None
    reasoning: Optional[str] = Field(default=None, max_length=2000)


@router.post("/picks", tags=["Picks"])
async def create_pick(body: SubmitPick, user: User = Depends(require_user)) -> dict:
    """Publish a prediction. Refused once the game has started."""
    if not entitlements_for(user).has("make_pick"):
        raise HTTPException(status_code=403, detail="Your plan doesn't include publishing picks.")
    try:
        pick = service.submit(
            user_id=user.id, username=user.username,
            **body.model_dump(),
        )
    except PickError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return pick.to_public()


@router.get("/picks/mine", tags=["Picks"])
async def my_picks(user: User = Depends(require_user)) -> dict:
    picks = service.for_user(user.id)
    return {
        "record": service.record_for(user.id),
        "picks": [p.to_public() for p in picks],
    }


@router.patch("/picks/{pick_id}", tags=["Picks"])
async def edit_pick(pick_id: str, body: EditPick,
                    user: User = Depends(require_user)) -> dict:
    pick = service.get(pick_id)
    # 404 rather than 403 for someone else's pick: a 403 confirms it exists.
    if pick is None or pick.user_id != user.id:
        raise HTTPException(status_code=404, detail="Pick not found.")
    try:
        updated = service.update(pick, **body.model_dump(exclude_none=True))
    except PickError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return updated.to_public()


@router.delete("/picks/{pick_id}", tags=["Picks"])
async def withdraw_pick(pick_id: str, user: User = Depends(require_user)) -> dict:
    pick = service.get(pick_id)
    if pick is None or pick.user_id != user.id:
        raise HTTPException(status_code=404, detail="Pick not found.")
    try:
        service.delete(pick)
    except PickError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True}


@router.get("/picks/game/{league}/{event_id}", tags=["Picks"])
async def game_community(league: str, event_id: str, request: Request) -> dict:
    """
    Community picks on one game.

    Only locked picks are exposed alongside a breakdown, so an open pick cannot
    be reverse-engineered before kickoff — and the consensus reflects positions
    people actually committed to.
    """
    game_id = f"{league.lower()}:{event_id}"
    picks = service.for_game(game_id)
    locked = [p for p in picks if p.is_locked()]

    by_side: dict[str, int] = {}
    for pick in picks:
        if pick.market == "moneyline":
            by_side[pick.side] = by_side.get(pick.side, 0) + 1
    total = sum(by_side.values())

    viewer = current_user(request)
    mine = [p.to_public() for p in picks if viewer and p.user_id == viewer.id]

    return {
        "game_id": game_id,
        "total_picks": len(picks),
        # Percentages only once there is something real to divide; an empty
        # game shows an invitation, not a fabricated 50/50.
        "moneyline_split": (
            {side: round(n / total * 100, 1) for side, n in by_side.items()}
            if total else {}
        ),
        "recent_analysis": [
            {
                "username": p.username, "selection": p.selection,
                "confidence": p.confidence, "reasoning": p.reasoning,
                "market": p.market, "created_at": p.created_at,
                "result": p.result,
            }
            for p in sorted(locked, key=lambda p: p.created_at, reverse=True)[:10]
            if p.reasoning
        ],
        "your_picks": mine,
    }


@router.get("/analysts/{username}", tags=["Picks"])
async def analyst_profile(username: str) -> dict:
    """A public analyst profile: identity, verified record and locked picks."""
    user = get_by_username(username)
    if user is None or not user.profile_public:
        raise HTTPException(status_code=404, detail="Analyst not found.")
    picks = service.for_user(user.id)
    return {
        "profile": user.to_public(),
        "record": service.record_for(user.id),
        # Open picks stay private until they lock, so nobody can be tailed or
        # front-run before an event starts.
        "picks": [p.to_public() for p in picks if p.is_locked()],
    }
