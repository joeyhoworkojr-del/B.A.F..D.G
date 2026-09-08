"""
Entitlements — the single place access is decided.

Every feature gate in the product resolves through `entitlements_for`. Nothing
else checks a level directly, so switching from free beta to paid access is a
change to this file and not a hunt for scattered `if user.pro` conditions.

The beta stance is deliberate: BETA receives everything PRO receives. Users
build habits and a verified record on the full product, and the level they
already hold is what the paywall will later read.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from src.accounts.models import User

# Features the product gates. A feature absent from a level's set is withheld
# by the endpoint that would serve it, not merely hidden in the UI.
FEATURES = (
    "model_predictions",        # full Stat Edge probabilities
    "player_props",
    "line_movement_history",
    "model_internals",
    "advanced_stats",
    "community_consensus",
    "make_pick",
    "leaderboard_full",
    "personal_analytics",
    "edge_ai",
    "edge_ai_unlimited",
    "alerts",
    "saved_games",
)

# What each level may access once the paywall is live.
_GRANTS: dict[str, set[str]] = {
    "guest": {"community_consensus", "leaderboard_full"},
    "free": {
        "community_consensus", "leaderboard_full", "make_pick",
        "personal_analytics", "saved_games", "edge_ai",
    },
    "beta": set(FEATURES),
    "pro": set(FEATURES),
    "admin": set(FEATURES),
}

# Features not implemented yet. These report False regardless of level, so the
# UI can never advertise something the backend cannot serve.
_NOT_IMPLEMENTED = {"alerts", "edge_ai_unlimited"}

# Features that are built but depend on something the deployment must supply.
# "Implemented" and "able to run here" are different claims, and a feature the
# UI offers must satisfy the second one — a plan that lists Edge AI on a
# deployment with no model behind it is advertising something that cannot be
# served, which is the same fault as shipping it unimplemented.
def _edge_ai_ready() -> bool:
    try:
        from src.ai.provider import get_provider
        return get_provider().available()
    except Exception:                                    # pragma: no cover
        return False


_REQUIRES_CONFIG = {"edge_ai": _edge_ai_ready}

_REASONS = {
    "alerts": "Alerts aren't built yet.",
    "edge_ai": "Edge AI isn't configured on this deployment yet.",
    "edge_ai_unlimited": "Edge AI isn't available yet.",
}

# While this is set, no feature is withheld from a signed-in account: the beta
# is genuinely free and gates must not fire early.
BETA_OPEN = os.getenv("STATEDGE_BETA_OPEN", "1") != "0"


@dataclass
class Entitlements:
    level: str
    authenticated: bool
    beta_open: bool
    features: dict[str, bool] = field(default_factory=dict)
    unavailable_reason: dict[str, str] = field(default_factory=dict)
    billing_enabled: bool = False
    note: str = ""

    def has(self, feature: str) -> bool:
        return self.features.get(feature, False)


def entitlements_for(user: Optional[User]) -> Entitlements:
    """Resolve what a caller may access. The only source of truth."""
    level = user.level if user else "guest"
    if level not in _GRANTS:
        level = "free" if user else "guest"

    granted = set(_GRANTS[level])
    if BETA_OPEN and user is not None:
        # Signed in during the beta means full access, whatever the stored
        # level says. Anonymous visitors still see the guest surface, which is
        # what gives an account a reason to exist.
        granted = set(FEATURES)

    features = {
        f: (
            f in granted
            and f not in _NOT_IMPLEMENTED
            and _REQUIRES_CONFIG.get(f, lambda: True)()
        )
        for f in FEATURES
    }
    unavailable = {
        f: _REASONS.get(f, "Not available on your current plan.")
        for f, ok in features.items() if not ok
    }

    return Entitlements(
        level=level,
        authenticated=user is not None,
        beta_open=BETA_OPEN,
        features=features,
        unavailable_reason=unavailable,
        billing_enabled=False,
        note=(
            "Full access is free during the Stat Edge beta."
            if BETA_OPEN else
            "Some Stat Edge intelligence requires a subscription."
        ),
    )
