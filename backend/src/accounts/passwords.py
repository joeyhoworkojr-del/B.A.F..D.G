"""
Password hashing.

Argon2id, via the reference implementation. StatEdge never stores a password,
only a verification hash, and the hash is never returned by any endpoint.

Parameters are the argon2-cffi defaults, which target roughly 50-100ms on
server hardware. That cost is the point: it is what makes an offline attack on
a leaked hash expensive.
"""
from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()

MIN_LENGTH = 10
MAX_LENGTH = 256   # bound the work an attacker can make the server do


class WeakPassword(ValueError):
    """Rejected before hashing, with a reason the user can act on."""


def validate(password: str) -> None:
    """Raise WeakPassword unless the password clears the minimum bar."""
    if not password or len(password) < MIN_LENGTH:
        raise WeakPassword(f"Use at least {MIN_LENGTH} characters.")
    if len(password) > MAX_LENGTH:
        raise WeakPassword(f"Use at most {MAX_LENGTH} characters.")
    if password.lower() in _COMMON:
        raise WeakPassword("That password is too common. Choose something else.")


def hash_password(password: str) -> str:
    validate(password)
    return _hasher.hash(password)


def verify(stored_hash: str, password: str) -> bool:
    """True when the password matches. Never raises on a bad password."""
    try:
        return _hasher.verify(stored_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    """True when the hash predates the current parameters and should be upgraded."""
    try:
        return _hasher.check_needs_rehash(stored_hash)
    except InvalidHashError:
        return False


# A short deny-list of passwords that appear at the top of every breach corpus.
# Not a substitute for a length minimum — it only removes the worst choices.
_COMMON = {
    "password", "password1", "password123", "123456789", "1234567890",
    "qwertyuiop", "letmein123", "iloveyou1", "adminadmin", "welcome123",
    "football12", "statedge12", "changeme123", "passw0rd123", "qwerty12345",
}
