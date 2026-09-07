"""
Authentication and account routes.

Sessions are httpOnly cookies resolved server-side on every request. The client
is never trusted for identity: no endpoint accepts a user id from the caller,
it reads the session instead. That is what makes a verified prediction record
possible — a user cannot claim to be someone else, or edit someone else's
history, by editing a request.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from src.accounts import sessions
from src.accounts.entitlements import Entitlements, entitlements_for
from src.accounts.models import User
from src.accounts.service import (
    AccountError, authenticate, change_username, get_by_id, register,
    update_profile, username_available,
)

router = APIRouter()


# ─── Dependencies ────────────────────────────────────────────────────────────

def current_user(request: Request) -> Optional[User]:
    """The signed-in user, or None. Never raises — anonymous is valid."""
    user_id = sessions.resolve(request.cookies.get(sessions.SESSION_COOKIE))
    return get_by_id(user_id) if user_id else None


def require_user(request: Request) -> User:
    """For endpoints that need an account. 401 when there is no session."""
    user = current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    return user


def require_admin(request: Request) -> User:
    user = require_user(request)
    if user.level != "admin":
        # 404 rather than 403: a 403 confirms the route exists.
        raise HTTPException(status_code=404, detail="Not found")
    return user


# ─── Schemas ─────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(..., max_length=40)
    email: str = Field(..., max_length=254)
    password: str = Field(..., max_length=256)
    display_name: str = Field(default="", max_length=60)


class LoginRequest(BaseModel):
    identifier: str = Field(..., max_length=254, description="Username or email")
    password: str = Field(..., max_length=256)


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=60)
    bio: Optional[str] = Field(default=None, max_length=400)
    avatar_url: Optional[str] = Field(default=None, max_length=500)
    favourite_sports: Optional[list[str]] = None
    favourite_teams: Optional[list[str]] = None
    interests: Optional[list[str]] = None
    profile_public: Optional[bool] = None
    onboarded: Optional[bool] = None


class UsernameChange(BaseModel):
    username: str = Field(..., max_length=40)


def _session_payload(user: User) -> dict:
    ent = entitlements_for(user)
    return {"user": user.to_private(), "entitlements": _ent_dict(ent)}


def _ent_dict(ent: Entitlements) -> dict:
    return {
        "level": ent.level,
        "authenticated": ent.authenticated,
        "beta_open": ent.beta_open,
        "features": ent.features,
        "unavailable_reason": ent.unavailable_reason,
        "billing_enabled": ent.billing_enabled,
        "note": ent.note,
    }


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.post("/auth/register", tags=["Auth"])
async def register_account(body: RegisterRequest, request: Request, response: Response) -> dict:
    """Create an account and sign in. Beta accounts keep a Founding Analyst badge."""
    try:
        user = register(
            username=body.username, email=body.email,
            password=body.password, display_name=body.display_name,
        )
    except AccountError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    token, expires = sessions.create(user.id, user_agent=request.headers.get("user-agent", ""))
    response.set_cookie(value=token, **sessions.cookie_kwargs(expires))
    return _session_payload(user)


@router.post("/auth/login", tags=["Auth"])
async def login(body: LoginRequest, request: Request, response: Response) -> dict:
    user = authenticate(identifier=body.identifier, password=body.password)
    if user is None:
        # One message for every failure — a distinct "no such account" reply
        # would let anyone test which emails are registered.
        raise HTTPException(status_code=401, detail="Incorrect username or password.")
    token, expires = sessions.create(user.id, user_agent=request.headers.get("user-agent", ""))
    response.set_cookie(value=token, **sessions.cookie_kwargs(expires))
    return _session_payload(user)


@router.post("/auth/logout", tags=["Auth"])
async def logout(request: Request, response: Response) -> dict:
    sessions.destroy(request.cookies.get(sessions.SESSION_COOKIE))
    response.delete_cookie(sessions.SESSION_COOKIE, path="/")
    return {"ok": True}


def _request_diagnostics(request: Request) -> dict:
    """
    Whether a session cookie reached this process at all.

    statedge.ca serves the SPA from Vercel and proxies /api to Fly, so a
    request crosses a boundary that can drop cookies. "Signed in but treated as
    a guest" and "never signed in" look identical from the browser; this tells
    them apart without exposing anything — presence and names only, never a
    value.
    """
    return {
        "cookies_received": sorted(request.cookies.keys()),
        "session_cookie_present": sessions.SESSION_COOKIE in request.cookies,
        "secure_cookies": sessions.SECURE_COOKIES,
        "origin": request.headers.get("origin", ""),
    }


@router.get("/auth/me", tags=["Auth"])
async def me(request: Request) -> dict:
    """The current session. Anonymous is a valid answer, not an error."""
    user = current_user(request)
    diagnostics = _request_diagnostics(request)
    if user is None:
        return {
            "user": None,
            "entitlements": _ent_dict(entitlements_for(None)),
            "debug": diagnostics,
        }
    return {**_session_payload(user), "debug": diagnostics}


@router.get("/auth/username-available", tags=["Auth"])
async def check_username(username: str) -> dict:
    """Live validation for the sign-up form."""
    return {"username": username, "available": username_available(username)}


@router.patch("/auth/profile", tags=["Auth"])
async def patch_profile(body: ProfileUpdate, user: User = Depends(require_user)) -> dict:
    """
    Edit your own profile.

    The user comes from the session, never from the request body, so there is
    no id to tamper with and no way to address someone else's account.
    """
    updated = update_profile(user, **body.model_dump(exclude_none=True))
    return _session_payload(updated)


@router.patch("/auth/username", tags=["Auth"])
async def patch_username(body: UsernameChange, user: User = Depends(require_user)) -> dict:
    try:
        updated = change_username(user, body.username)
    except AccountError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _session_payload(updated)
