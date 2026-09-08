"""Staff portal access control and content."""
from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.store import documents


@pytest.fixture(autouse=True)
def clean_store(tmp_path, monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("LEDGER_PATH", str(tmp_path / "admin.db"))
    documents.reset_docs()
    yield
    documents.reset_docs()


def register(client, username="joey"):
    return client.post("/api/v1/auth/register", json={
        "username": username, "email": f"{username}@example.com",
        "password": "a-strong-passphrase"})


def as_admin(monkeypatch, username="boss"):
    """Promote via the environment, the only way admin is granted."""
    from src.accounts import models, service
    monkeypatch.setenv("ADMIN_USERNAMES", username)
    importlib.reload(models)
    importlib.reload(service)
    import src.api.routes.auth as auth
    importlib.reload(auth)
    c = TestClient(app)
    register(c, username)
    return c


def test_an_anonymous_visitor_cannot_reach_the_portal():
    assert TestClient(app).get("/api/v1/admin/overview").status_code == 401


def test_an_ordinary_account_gets_a_404_not_a_403():
    """A 403 would confirm the route exists; staff surface should not."""
    c = TestClient(app)
    register(c)
    assert c.get("/api/v1/admin/overview").status_code == 404
    assert c.get("/api/v1/admin/users").status_code == 404
    assert c.get("/api/v1/admin/picks").status_code == 404


def test_admin_is_granted_only_by_the_environment(monkeypatch):
    c = as_admin(monkeypatch)
    assert c.get("/api/v1/auth/me").json()["user"]["level"] == "admin"
    assert c.get("/api/v1/admin/overview").status_code == 200


def test_a_user_cannot_promote_themselves(monkeypatch):
    """The level is not user-writable, and storage is not the source of truth."""
    monkeypatch.setenv("ADMIN_USERNAMES", "")
    from src.accounts import models, service
    importlib.reload(models)
    importlib.reload(service)
    c = TestClient(app)
    register(c)
    c.patch("/api/v1/auth/profile", json={"level": "admin"})
    assert c.get("/api/v1/auth/me").json()["user"]["level"] != "admin"


def test_removing_a_name_demotes_on_the_next_read(monkeypatch):
    c = as_admin(monkeypatch)
    assert c.get("/api/v1/auth/me").json()["user"]["level"] == "admin"

    monkeypatch.setenv("ADMIN_USERNAMES", "")
    from src.accounts import models, service
    importlib.reload(models)
    importlib.reload(service)
    assert c.get("/api/v1/auth/me").json()["user"]["level"] == "beta"


def test_the_overview_reports_real_counts(monkeypatch):
    c = as_admin(monkeypatch)
    body = c.get("/api/v1/admin/overview").json()
    assert body["accounts"]["total"] == 1
    assert body["accounts"]["founding"] == 1
    assert body["picks"]["total"] == 0
    assert body["storage"]["backend"] in ("sqlite", "postgres", "redis")


def test_the_user_list_never_exposes_a_password_hash(monkeypatch):
    c = as_admin(monkeypatch)
    body = c.get("/api/v1/admin/users").text
    assert "password_hash" not in body
    assert "argon2" not in body


def test_the_portal_offers_no_way_to_alter_a_graded_pick():
    """
    A staff tool that could quietly rewrite a result would undermine the only
    claim the product makes, so the routes simply do not exist.
    """
    paths = [r.path for r in app.routes if "/admin/" in getattr(r, "path", "")]
    for route in app.routes:
        if "/admin/" in getattr(route, "path", ""):
            methods = getattr(route, "methods", set())
            assert methods <= {"GET", "HEAD", "OPTIONS"}, f"{route.path} is writable"
    assert paths, "expected admin routes to exist"
