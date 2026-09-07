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
    get_docs().put(COLLECTION, _digest(token), {
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
        "samesite": "lax",
        "secure": SECURE_COOKIES,
        "path": "/",
        "max_age": SESSION_DAYS * 24 * 3600,
    }
