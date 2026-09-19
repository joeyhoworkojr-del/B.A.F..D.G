"""
Who is allowed to tell the model a player is out.

Reading availability is public — it is part of explaining a projection. Setting
it is not: an override lands on every subsequent prediction for that team, so
an unauthenticated write is a stranger moving StatEdge's published numbers.
Both writes were reachable anonymously; these pin them shut.
"""
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
    monkeypatch.setenv("LEDGER_PATH", str(tmp_path / "lineups.db"))
    documents.reset_docs()
    yield
    documents.reset_docs()


def register(client, username):
    return client.post("/api/v1/auth/register", json={
        "username": username, "email": f"{username}@example.com",
        "password": "a-strong-passphrase"})


def as_admin(monkeypatch, username="boss"):
    from src.accounts import models, service
    monkeypatch.setenv("ADMIN_USERNAMES", username)
    importlib.reload(models)
    importlib.reload(service)
    import src.api.routes.auth as auth
    importlib.reload(auth)
    c = TestClient(app)
    register(c, username)
    return c


def a_key_player(client, team="KC"):
    players = client.get(f"/api/v1/lineups/nfl/{team}").json()
    assert players, "KC should have key players on file"
    return players[0]["name"]


def test_anyone_may_read_who_is_available():
    c = TestClient(app)
    assert c.get("/api/v1/lineups/nfl/KC").status_code == 200


def test_a_stranger_cannot_rule_a_quarterback_out():
    c = TestClient(app)
    name = a_key_player(c)
    assert c.post("/api/v1/lineups/nfl/KC",
                  json={"player": name, "status": "out"}).status_code == 401
    # And the model still thinks he is playing.
    after = [p for p in c.get("/api/v1/lineups/nfl/KC").json() if p["name"] == name]
    assert after[0]["status"] == "fit"


def test_a_stranger_cannot_wipe_the_teams_overrides():
    assert TestClient(app).delete("/api/v1/lineups/nfl/KC").status_code == 401


def test_a_signed_in_reader_is_still_not_staff():
    """
    404 rather than 403, matching the rest of the staff surface: a 403 would
    confirm to an ordinary account that the route is there to be found.
    """
    c = TestClient(app)
    register(c, "ordinary")
    name = a_key_player(c)
    assert c.post("/api/v1/lineups/nfl/KC",
                  json={"player": name, "status": "out"}).status_code == 404
    after = [p for p in c.get("/api/v1/lineups/nfl/KC").json() if p["name"] == name]
    assert after[0]["status"] == "fit"


def test_staff_can_still_set_and_reset_availability(monkeypatch):
    # The lock must not break the people it exists for.
    c = as_admin(monkeypatch)
    name = a_key_player(c)

    assert c.post("/api/v1/lineups/nfl/KC",
                  json={"player": name, "status": "out"}).status_code == 200
    out = [p for p in c.get("/api/v1/lineups/nfl/KC").json() if p["name"] == name]
    assert out[0]["status"] == "out"

    assert c.delete("/api/v1/lineups/nfl/KC").status_code == 200
    back = [p for p in c.get("/api/v1/lineups/nfl/KC").json() if p["name"] == name]
    assert back[0]["status"] == "fit"


def test_an_unknown_sport_is_still_rejected_for_staff(monkeypatch):
    c = as_admin(monkeypatch, "boss2")
    assert c.delete("/api/v1/lineups/quidditch/KC").status_code == 404
