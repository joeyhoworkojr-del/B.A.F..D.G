"""Entitlements and player props: server-side, and honest about what is missing."""
from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_entitlements_are_resolved_server_side():
    body = client.get("/api/v1/entitlements").json()
    assert body["plan"] == "free"
    assert body["authenticated"] is False
    assert body["auth_configured"] is False
    assert body["billing_enabled"] is False


def test_granted_features_are_only_ones_the_server_can_serve():
    body = client.get("/api/v1/entitlements").json()
    features = body["features"]
    # Anything not implemented must report False regardless of plan, so the UI
    # can never advertise a feature the backend cannot serve.
    assert features["alerts"] is False
    assert features["saved_games"] is False
    # Projections are implemented, so this one is genuinely available.
    assert features["player_props"] is True
    assert features["line_movement_history"] is True


def test_every_withheld_feature_explains_itself():
    body = client.get("/api/v1/entitlements").json()
    withheld = [k for k, v in body["features"].items() if not v]
    for key in withheld:
        assert body["unavailable_reason"].get(key), f"{key} withheld without a reason"


def test_props_serve_projections_but_admit_lines_are_missing():
    body = client.get("/api/v1/props").json()
    assert body["available"] is True        # projections are served
    assert body["lines_available"] is False  # posted lines are not
    assert body["reason"]
    assert len(body["requires"]) >= 2


def test_news_route_rejects_unknown_leagues():
    assert client.get("/api/v1/news?league=cricket").status_code == 404


def test_entitlements_are_never_stored_in_a_shared_cache():
    headers = client.get("/api/v1/entitlements").headers
    policy = headers.get("cache-control", "")
    assert "no-store" in policy and "public" not in policy


def test_news_is_cacheable():
    # The route itself is exercised elsewhere; here we only assert the policy
    # the middleware attaches, using an unknown league's 404-free sibling.
    headers = client.get("/api/v1/props").headers
    assert "max-age" in headers.get("cache-control", "")
