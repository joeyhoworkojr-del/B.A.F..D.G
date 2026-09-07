"""
Account + entitlement routes.

Entitlements are resolved here, on the server, so the client is never the
security boundary: a premium payload is withheld by the endpoint that would
serve it, not by hiding a panel with CSS.

Authentication is not configured in this deployment. Rather than pretend
otherwise, `/api/v1/entitlements` reports `authenticated=false` and
`auth_configured=false`, and this release grants every feature to everyone —
StatEdge is free while the model's public track record is still short. When an
identity provider and durable storage are configured (see DEPLOYMENT.md), the
resolver below reads the caller's plan instead of returning the anonymous one;
no route that consumes `resolve_entitlements` has to change.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter()

# Feature keys the frontend asks about. Kept here so the server owns the list.
FEATURES = (
    "line_movement_history",
    "model_internals",
    "alerts",
    "player_props",
    "saved_games",
)

# Set when an identity provider is wired up. Absent in this deployment.
AUTH_PROVIDER = os.getenv("AUTH_PROVIDER", "").strip()

# This release is free: every implemented feature is granted to every visitor.
# Features that are not implemented are reported False regardless of plan, so
# the UI can never advertise something the backend cannot serve.
IMPLEMENTED: dict[str, bool] = {
    "line_movement_history": True,
    "model_internals": True,
    "alerts": False,        # needs durable per-user storage
    "player_props": False,  # needs a props odds provider (see /api/v1/props)
    "saved_games": False,   # needs durable per-user storage
}


class EntitlementsOut(BaseModel):
    plan: str = "free"
    authenticated: bool = False
    auth_configured: bool = False
    # feature key → granted. False here means the server will refuse the
    # payload, not merely that the UI hides it.
    features: dict[str, bool] = Field(default_factory=dict)
    # Feature key → why it is unavailable, when it is.
    unavailable_reason: dict[str, str] = Field(default_factory=dict)
    billing_enabled: bool = False
    note: str = ""


_REASONS = {
    "alerts": "Requires a signed-in account and durable storage; neither is configured yet.",
    "player_props": "Requires a licensed player-props odds provider; none is configured yet.",
    "saved_games": "Requires a signed-in account and durable storage; neither is configured yet.",
}


def resolve_entitlements(request: Request) -> EntitlementsOut:
    """
    The single place a caller's access is decided.

    With no identity provider configured every caller is anonymous and on the
    free plan. Feature grants are the intersection of the plan's allowance and
    what is actually implemented, so a granted feature is always servable.
    """
    authenticated = False   # no session to read until AUTH_PROVIDER is wired up
    plan = "free"

    features = {key: IMPLEMENTED.get(key, False) for key in FEATURES}
    unavailable = {k: _REASONS[k] for k, granted in features.items()
                   if not granted and k in _REASONS}

    return EntitlementsOut(
        plan=plan,
        authenticated=authenticated,
        auth_configured=bool(AUTH_PROVIDER),
        features=features,
        unavailable_reason=unavailable,
        billing_enabled=False,
        note=(
            "StatEdge is free during this release. Every implemented feature is "
            "available to everyone; nothing is being sold and no payment method "
            "is collected."
        ),
    )


@router.get("/entitlements", response_model=EntitlementsOut, tags=["Account"])
async def get_entitlements(request: Request) -> EntitlementsOut:
    """What the caller may access, decided server-side."""
    return resolve_entitlements(request)


class PropsOut(BaseModel):
    """
    Player props are not available.

    ESPN's keyless site API — the source behind every other market on the site —
    carries no player-prop lines. Rather than invent numbers, this endpoint
    reports the gap and names exactly what is required to close it.
    """
    available: bool = False
    league: str = ""
    event_id: str = ""
    props: list[dict] = Field(default_factory=list)
    reason: str = ""
    requires: list[str] = Field(default_factory=list)


PROPS_REQUIREMENTS = [
    "A licensed player-props odds provider (for example The Odds API, "
    "OddsJam, or a sportsbook partner feed) with player-level markets for "
    "NFL and NCAA football.",
    "The provider's API key supplied as the PROPS_API_KEY environment "
    "variable, plus PROPS_PROVIDER naming the integration to use.",
    "Per-player projections from the model. The gridiron engine currently "
    "projects team scores and game totals only; player-level distributions "
    "are not implemented.",
]


@router.get("/props/{league}/{event_id}", response_model=PropsOut, tags=["Props"])
async def get_player_props(league: str, event_id: str) -> PropsOut:
    """Player props for one game — unavailable until a props provider is configured."""
    return PropsOut(
        available=False,
        league=league.lower(),
        event_id=event_id,
        reason=(
            "StatEdge has no player-props data source. The keyless ESPN feed "
            "behind the rest of the site does not publish player-prop lines, and "
            "the model does not yet produce player-level projections."
        ),
        requires=PROPS_REQUIREMENTS,
    )


@router.get("/props", response_model=PropsOut, tags=["Props"])
async def get_props_status() -> PropsOut:
    """Whether player props are available at all, and what they would need."""
    return PropsOut(
        available=False,
        reason=(
            "StatEdge has no player-props data source. The keyless ESPN feed "
            "behind the rest of the site does not publish player-prop lines, and "
            "the model does not yet produce player-level projections."
        ),
        requires=PROPS_REQUIREMENTS,
    )
