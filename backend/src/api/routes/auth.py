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

from src.accounts import avatars, passwords, sessions
from src.accounts.entitlements import Entitlements, entitlements_for
from src.accounts.models import ROLE_POWERS, User, has_power, staff_config_report
from src.accounts.service import (
    AccountError, authenticate, change_username, get_by_id, register,
    set_password, update_profile, username_available,
)

router = APIRouter()


# ─── Dependencies ────────────────────────────────────────────────────────────

def _session_token(request: Request) -> Optional[str]:
    """
    The session token, from the cookie or the Authorization header.

    The cookie is preferred: it is httpOnly, so script cannot read it. But a
    proxy between the browser and this process can drop the Cookie header —
    Vercel's rewrite to an external host does exactly that — and when it does,
    a cookie-only session is unusable no matter how correct it is.

    The bearer header is the fallback for that topology. It is weaker, because
    the client has to hold the token somewhere script can reach, and it stops
    being used the moment the cookie arrives.
    """
    cookie = request.cookies.get(sessions.SESSION_COOKIE)
    if cookie:
        return cookie
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return None


def current_user(request: Request) -> Optional[User]:
    """The signed-in user, or None. Never raises — anonymous is valid."""
    user_id = sessions.resolve(_session_token(request))
    return get_by_id(user_id) if user_id else None


def require_user(request: Request) -> User:
    """For endpoints that need an account. 401 when there is no session."""
    user = current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    return user


def _require_power(request: Request, power: str) -> User:
    """
    Gate a route on a staff power rather than on a specific level.

    404 rather than 403 throughout: a 403 confirms the route exists, and a
    staff area that announces itself to everyone who probes for it is a worse
    starting point than one that simply is not there. The hidden footer link is
    a convenience for staff, never the control — this check is.
    """
    user = require_user(request)
    if not has_power(user.level, power):
        raise HTTPException(status_code=404, detail="Not found")
    return user


def require_admin(request: Request) -> User:
    """Full control, including anything destructive."""
    return _require_power(request, "manage_users")


def require_staff(request: Request) -> User:
    """Operational visibility — the staff dashboard and its read-only views."""
    return _require_power(request, "view_staff")


def require_moderator(request: Request) -> User:
    """Community and chat moderation."""
    return _require_power(request, "moderate")


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


def _session_payload(user: User, token: Optional[str] = None) -> dict:
    ent = entitlements_for(user)
    body = {"user": user.to_private(), "entitlements": _ent_dict(ent)}
    if token:
        # Returned so a client behind a cookie-stripping proxy can still hold a
        # session. Clients that receive their cookie normally ignore this.
        body["session_token"] = token
    return body


def _ent_dict(ent: Entitlements) -> dict:
    return {
        "level": ent.level,
        # The powers this account actually holds, so the UI can show a Staff
        # link without hard-coding which levels count as staff. The server
        # checks these again on every request — this list is for rendering.
        "powers": sorted(ROLE_POWERS.get(ent.level, frozenset())),
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
    return _session_payload(user, token)


@router.post("/auth/login", tags=["Auth"])
async def login(body: LoginRequest, request: Request, response: Response) -> dict:
    user = authenticate(identifier=body.identifier, password=body.password)
    if user is None:
        # One message for every failure — a distinct "no such account" reply
        # would let anyone test which emails are registered.
        raise HTTPException(status_code=401, detail="Incorrect username or password.")
    token, expires = sessions.create(user.id, user_agent=request.headers.get("user-agent", ""))
    response.set_cookie(value=token, **sessions.cookie_kwargs(expires))
    return _session_payload(user, token)


@router.post("/auth/logout", tags=["Auth"])
async def logout(request: Request, response: Response) -> dict:
    sessions.destroy(_session_token(request))
    # A cookie is only cleared by a matching path and domain; omitting the
    # domain here would leave the browser holding a dead session cookie.
    response.delete_cookie(
        sessions.SESSION_COOKIE, path="/",
        **({"domain": sessions.COOKIE_DOMAIN} if sessions.COOKIE_DOMAIN else {}),
    )
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
        "bearer_present": request.headers.get("authorization", "").lower().startswith("bearer "),
        "secure_cookies": sessions.SECURE_COOKIES,
        "origin": request.headers.get("origin", ""),
        # Whether ADMIN_USERNAMES reached *this* process. Set on the wrong
        # host (the SPA's env instead of the API's) it is silently empty, and
        # a missing Staff link looks identical to a username that did not
        # match. The count answers that; the names stay private.
        "staff_roles_configured": staff_config_report(),
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


class PasswordChange(BaseModel):
    current_password: str = Field(..., max_length=256)
    new_password: str = Field(..., max_length=256)


class AvatarUpload(BaseModel):
    # A data: URL from a canvas, or the bare base64 payload.
    image: str = Field(..., max_length=avatars.MAX_BYTES * 2)


@router.post("/auth/password", tags=["Auth"])
async def change_password_route(
    body: PasswordChange, request: Request, response: Response,
    user: User = Depends(require_user),
) -> dict:
    """
    Change your own password.

    The current password is required even though the caller already holds a
    session: a borrowed laptop should not be enough to lock the owner out of
    their own account. Every other session is destroyed on success, so a
    password change actually evicts whoever prompted it, and this one is
    reissued so the person doing it is not signed out of their own browser.
    """
    if not passwords.verify(user.password_hash, body.current_password):
        raise HTTPException(status_code=401, detail="That is not your current password.")
    try:
        passwords.validate(body.new_password)
    except passwords.WeakPassword as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    set_password(user, body.new_password)
    sessions.destroy_all(user.id)
    token, expires = sessions.create(user.id, user_agent=request.headers.get("user-agent", ""))
    response.set_cookie(value=token, **sessions.cookie_kwargs(expires))
    return {**_session_payload(user, token), "signed_out_other_sessions": True}


@router.post("/auth/avatar", tags=["Auth"])
async def upload_avatar(body: AvatarUpload, user: User = Depends(require_user)) -> dict:
    """
    Replace your profile photo.

    The image arrives already cropped and resized by the browser; this endpoint
    checks it really is an image, of a format that cannot carry script, and
    small enough to store.
    """
    try:
        saved = avatars.save(user.id, body.image)
    except avatars.InvalidImage as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    updated = update_profile(user, avatar_url=avatars.url_for(user.id, saved.etag))
    return _session_payload(updated)


@router.delete("/auth/avatar", tags=["Auth"])
async def delete_avatar(user: User = Depends(require_user)) -> dict:
    """Remove your photo. The profile falls back to initials."""
    avatars.remove(user.id)
    updated = update_profile(user, avatar_url="")
    return _session_payload(updated)


@router.get("/avatars/{user_id}", tags=["Auth"])
async def serve_avatar(user_id: str) -> Response:
    """
    Serve a profile photo.

    Public, because avatars appear beside names on leaderboards and in chat
    where the viewer may not be signed in. Cached hard and busted by the etag
    in the URL, so a new upload appears immediately without every page paying
    for a revalidation.
    """
    avatar = avatars.load(user_id)
    if avatar is None:
        raise HTTPException(status_code=404, detail="No photo")
    return Response(
        content=avatar.data,
        media_type=avatar.content_type,
        headers={
            "Cache-Control": "public, max-age=604800, immutable",
            "ETag": f'"{avatar.etag}"',
            # Belt and braces against a stored file being interpreted as
            # anything other than the image type sniffed from its own bytes.
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; sandbox",
        },
    )


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
