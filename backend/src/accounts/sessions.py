"""
Server-side sessions.

A session is a random token stored server-side and handed to the browser in an
httpOnly cookie. The cookie carries no claims and no identity of its own: it is
a lookup key, so revoking a session is a delete rather than a wait for a token
to expire. That matters for a product where a compromised account can rewrite
someone's public record.

Nothing about authentication is ever kept in localStorage. It is readable by
any script on the page and cannot be marked httpOnly, so a single XSS would
hand over every logged-in session.
"""
from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.store.documents import get_docs

COLLECTION = "sessions"

SESSION_COOKIE = "statedge_session"
SESSION_DAYS = int(os.getenv("SESSION_DAYS", "30"))

# Cookies are Secure in production; over plain HTTP in local development a
# Secure cookie is simply never sent, which would make login appear broken.
SECURE_COOKIES = os.getenv("ENV", "development").lower() == "production"

# "lax" is correct when the API is same-origin with the site — which it is when
# /api is proxied — and it blocks cross-site POSTs, so it is the safer default.
#
# It is also wrong the moment the browser talks to the API host directly:
# statedge.ca calling statedge-api.fly.dev is cross-site, and a Lax cookie is
# simply not sent, which presents as being signed out immediately after signing
# in. Set SESSION_SAMESITE=none for that topology. None requires Secure, so it
# is only honoured over HTTPS.
_SAMESITE = os.getenv("SESSION_SAMESITE", "lax").strip().lower()
SAMESITE = _SAMESITE if _SAMESITE in ("lax", "strict", "none") else "lax"

# Set to ".statedge.ca" when the API is served from a subdomain of the site —
# api.statedge.ca alongside statedge.ca. The cookie is then first-party for
# both, which keeps SameSite=Lax working and, more importantly, survives
# Safari's third-party cookie blocking and Chrome's phase-out. A session that
# depends on third-party cookies works for some visitors and silently fails for
# others, which is worse than not working at all.
COOKIE_DOMAIN = (os.getenv("SESSION_COOKIE_DOMAIN") or "").strip()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _digest(token: str) -> str:
    """
    Sessions are stored as a hash of the token, not the token itself.

    A dump of the session store then contains nothing that can be replayed —
    the same reason passwords are not stored in the clear.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def create(user_id: str, *, user_agent: str = "") -> tuple[str, str]:
    """Start a session. Returns (token for the cookie, expiry as ISO-8601)."""
    token = secrets.token_urlsafe(32)
    expires = _now() + timedelta(days=SESSION_DAYS)
    digest = _digest(token)
    get_docs().put(COLLECTION, digest, {
        # The row carries its own key so a user's sessions can be found without
        # the tokens, which is what destroy_all needs on a password change.
        "id": digest,
        "user_id": user_id,
        "created_at": _now().isoformat(timespec="seconds"),
        "expires_at": expires.isoformat(timespec="seconds"),
        # Truncated: enough to recognise a device in a session list, not
        # enough to be a fingerprint.
        "user_agent": (user_agent or "")[:120],
    })
    return token, expires.isoformat(timespec="seconds")


def resolve(token: Optional[str]) -> Optional[str]:
    """The user id behind a session token, or None if absent or expired."""
    if not token:
        return None
    doc = get_docs().get(COLLECTION, _digest(token))
    if not doc:
        return None
    try:
        expires = datetime.fromisoformat(doc["expires_at"])
    except (KeyError, ValueError):
        return None
    if expires <= _now():
        destroy(token)          # expired sessions do not linger in storage
        return None
    return doc.get("user_id")


def destroy(token: Optional[str]) -> None:
    """Log out. Idempotent — an unknown token is not an error."""
    if token:
        get_docs().delete(COLLECTION, _digest(token))


def destroy_all(user_id: str) -> int:
    """
    End every session this account holds, on every device.

    What a password change is for. Changing a password that leaves the
    attacker's existing session alive has not actually locked anyone out, so
    this is the half of the operation that does the work.

    Returns the number of sessions ended. Sessions are keyed by a hash of their
    token, so finding a user's own requires scanning; the store is small (one
    row per signed-in device) and this runs only on a password change.
    """
    docs = get_docs()
    ended = 0
    for row in docs.list(COLLECTION) or []:
        if row.get("user_id") != user_id:
            continue
        token_digest = row.get("id") or row.get("_id")
        if token_digest:
            docs.delete(COLLECTION, token_digest)
            ended += 1
    return ended


def cookie_kwargs(expires_iso: str) -> dict:
    """
    Cookie flags, in one place so no endpoint can set a weaker combination.

    httponly  — script cannot read it, so XSS cannot steal the session
    samesite  — 'lax' blocks cross-site POSTs while keeping normal links working
    secure    — HTTPS only in production
    """
    return {
        "key": SESSION_COOKIE,
        "httponly": True,
        "samesite": SAMESITE,
        # SameSite=None is meaningless without Secure and browsers reject the
        # pair, so None forces Secure on regardless of environment.
        "secure": SECURE_COOKIES or SAMESITE == "none",
        "path": "/",
        "max_age": SESSION_DAYS * 24 * 3600,
        **({"domain": COOKIE_DOMAIN} if COOKIE_DOMAIN else {}),
    }
