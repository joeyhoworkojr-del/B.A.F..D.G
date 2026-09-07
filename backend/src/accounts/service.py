"""
Account operations.

Every rule that protects an identity lives here rather than in a route, so a
second entry point — an OAuth callback, an admin tool — cannot accidentally
skip one.
"""
from __future__ import annotations

import logging
from typing import Optional

from src.accounts import passwords
from src.accounts.models import (
    COLLECTION, InvalidUsername, User, normalise_email, normalise_username,
)
from src.store.documents import UniqueViolation, get_docs

log = logging.getLogger(__name__)


class AccountError(Exception):
    """A failure with a message safe to show the user."""


def _save(user: User) -> User:
    get_docs().put(COLLECTION, user.id, user.to_doc(), indexes=user.indexes())
    return user


def get_by_id(user_id: str) -> Optional[User]:
    doc = get_docs().get(COLLECTION, user_id)
    return User.from_doc(doc) if doc else None


def get_by_username(username: str) -> Optional[User]:
    try:
        name = normalise_username(username)
    except InvalidUsername:
        return None
    doc = get_docs().find(COLLECTION, "username", name)
    return User.from_doc(doc) if doc else None


def get_by_email(email: str) -> Optional[User]:
    doc = get_docs().find(COLLECTION, "email", (email or "").strip().lower())
    return User.from_doc(doc) if doc else None


def username_available(username: str) -> bool:
    try:
        normalise_username(username)
    except InvalidUsername:
        return False
    return get_by_username(username) is None


def register(*, username: str, email: str, password: str,
             display_name: str = "") -> User:
    """Create an account. Raises AccountError with a displayable message."""
    try:
        username = normalise_username(username)
        email = normalise_email(email)
        password_hash = passwords.hash_password(password)
    except (InvalidUsername, passwords.WeakPassword, ValueError) as exc:
        raise AccountError(str(exc)) from exc

    user = User.new(
        username=username, email=email, password_hash=password_hash,
        display_name=(display_name or "").strip()[:60],
        # Everyone who joins during the beta keeps this permanently.
        badges=["founding_analyst"],
        level="beta",
    )
    try:
        return _save(user)
    except UniqueViolation as exc:
        # Deliberately vague about which field collided: confirming that an
        # email is registered lets anyone enumerate the user base.
        raise AccountError("That username or email is already in use.") from exc


def authenticate(*, identifier: str, password: str) -> Optional[User]:
    """
    Verify credentials by username or email.

    Returns None for every failure, with no hint about which part was wrong —
    "no such user" and "wrong password" must be indistinguishable.
    """
    ident = (identifier or "").strip()
    user = get_by_email(ident) if "@" in ident else get_by_username(ident)
    if user is None or not user.password_hash:
        # Spend the hashing cost anyway, so response time does not reveal
        # whether the account exists.
        passwords.verify(_DUMMY_HASH, password or "")
        return None
    if not passwords.verify(user.password_hash, password or ""):
        return None
    if passwords.needs_rehash(user.password_hash):
        user.password_hash = passwords.hash_password(password)
        _save(user)
    return user


def update_profile(user: User, **changes) -> User:
    """Apply profile edits. Only fields a user owns can be written here."""
    editable = {
        "display_name": lambda v: str(v)[:60],
        "bio": lambda v: str(v)[:400],
        "avatar_url": lambda v: str(v)[:500],
        "favourite_sports": lambda v: [str(x)[:24] for x in list(v)[:12]],
        "favourite_teams": lambda v: [str(x)[:40] for x in list(v)[:40]],
        "interests": lambda v: [str(x)[:32] for x in list(v)[:12]],
        "profile_public": bool,
        "onboarded": bool,
    }
    for key, clean in editable.items():
        if key in changes and changes[key] is not None:
            setattr(user, key, clean(changes[key]))
    from src.accounts.models import _now
    user.updated_at = _now()
    return _save(user)


def change_username(user: User, new_username: str) -> User:
    """Rename. The old handle is released so it can be claimed again."""
    try:
        name = normalise_username(new_username)
    except InvalidUsername as exc:
        raise AccountError(str(exc)) from exc
    if name == user.username:
        return user
    old_indexes = user.indexes()
    if get_by_username(name) is not None:
        raise AccountError("That username isn't available.")
    get_docs().delete(COLLECTION, user.id, indexes=old_indexes)
    user.username = name
    try:
        return _save(user)
    except UniqueViolation as exc:
        raise AccountError("That username isn't available.") from exc


# A real Argon2 hash of a value nobody knows, used to keep failed logins as
# slow as successful ones.
_DUMMY_HASH = passwords.hash_password("statedge-timing-equaliser-value")
