"""
Account, profile and entitlement model.

One record per user. Credentials live alongside the profile because there is a
single identity here; if an external identity provider is added later, the
`password_hash` simply stops being set and `auth_provider` records which
service owns the credential instead.

`to_public()` is the only shape that reaches an API response. Everything
sensitive — the hash, the email, notification settings — is stripped there, so
a new field cannot leak by being added to the dataclass.
"""
from __future__ import annotations

import os
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

COLLECTION = "users"

# Account levels. BETA receives PRO functionality while the product is free;
# the level is stored so the switch to paid access is a data change, not a
# code change.
LEVELS = ("guest", "beta", "free", "pro", "admin")

USERNAME_RE = re.compile(r"^[a-z0-9_]{3,20}$")
RESERVED_USERNAMES = {
    "admin", "administrator", "root", "staff", "support", "help", "about",
    "api", "www", "statedge", "edge", "system", "moderator", "mod", "official",
    "games", "live", "props", "news", "results", "leaderboard", "discover",
    "account", "settings", "login", "logout", "register", "signup", "faq",
    "me", "my", "null", "undefined", "anonymous", "user", "users",
}


# Usernames promoted to admin on sign-in. An env var rather than a database
# flag, so admin cannot be granted by anything that can write to storage —
# only by someone who can change the deployment.
ADMIN_USERNAMES = {
    u.strip().lower()
    for u in (os.getenv("ADMIN_USERNAMES") or "").split(",")
    if u.strip()
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class InvalidUsername(ValueError):
    """Rejected with a reason the sign-up form can display."""


def normalise_username(raw: str) -> str:
    """
    Lower-case, validated handle.

    Handles are case-insensitive so @Joey and @joey cannot be different people
    — that ambiguity is an impersonation vector on a product whose whole value
    is a verified identity.
    """
    name = (raw or "").strip().lstrip("@").lower()
    if not USERNAME_RE.match(name):
        raise InvalidUsername(
            "Usernames are 3-20 characters, using letters, numbers and underscores."
        )
    if name in RESERVED_USERNAMES:
        raise InvalidUsername("That username isn't available.")
    return name


def normalise_email(raw: str) -> str:
    email = (raw or "").strip().lower()
    # Deliberately permissive: deliverability is proven by a verification mail,
    # not by a regex, and over-strict patterns reject valid addresses.
    if "@" not in email or "." not in email.split("@")[-1] or len(email) < 6:
        raise ValueError("Enter a valid email address.")
    return email


@dataclass
class User:
    id: str
    username: str
    email: str
    password_hash: str = ""
    auth_provider: str = "password"     # password | google | apple
    display_name: str = ""
    bio: str = ""
    avatar_url: str = ""
    level: str = "beta"                 # see LEVELS
    email_verified: bool = False
    favourite_sports: list[str] = field(default_factory=list)
    favourite_teams: list[str] = field(default_factory=list)
    interests: list[str] = field(default_factory=list)
    badges: list[str] = field(default_factory=list)
    onboarded: bool = False
    profile_public: bool = True
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    @staticmethod
    def new(username: str, email: str, password_hash: str, **kw) -> "User":
        return User(
            id=uuid.uuid4().hex,
            username=normalise_username(username),
            email=normalise_email(email),
            password_hash=password_hash,
            **kw,
        )

    # ── serialisation ────────────────────────────────────────────────────────

    def to_doc(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_doc(doc: dict[str, Any]) -> "User":
        known = {f for f in User.__dataclass_fields__}
        return User(**{k: v for k, v in doc.items() if k in known})

    def indexes(self) -> dict[str, str]:
        """Fields that must be unique across all accounts."""
        return {"username": self.username, "email": self.email}

    def to_public(self) -> dict[str, Any]:
        """
        What anyone may see. Never includes the hash, the email, or the
        account level — level is an entitlement, not a public attribute.
        """
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name or self.username,
            "bio": self.bio,
            "avatar_url": self.avatar_url,
            "favourite_sports": self.favourite_sports,
            "favourite_teams": self.favourite_teams,
            "badges": self.badges,
            "created_at": self.created_at,
        }

    def to_private(self) -> dict[str, Any]:
        """What the account holder may see about themselves."""
        return {
            **self.to_public(),
            "email": self.email,
            "email_verified": self.email_verified,
            "level": self.level,
            "interests": self.interests,
            "onboarded": self.onboarded,
            "profile_public": self.profile_public,
            "auth_provider": self.auth_provider,
        }
