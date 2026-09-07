"""
Account, session and entitlement behaviour.

Mirrors the ACCOUNTS acceptance list: register, login, logout, session
persistence, unique usernames, profile updates, and — most importantly — that
one user cannot touch another's account.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.accounts import passwords
from src.accounts.entitlements import entitlements_for
from src.accounts.models import User, normalise_username, InvalidUsername
from src.api.main import app
from src.store import documents


@pytest.fixture(autouse=True)
def clean_store(tmp_path, monkeypatch):
    """Each test gets its own SQLite-backed document store."""
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("LEDGER_PATH", str(tmp_path / "test.db"))
    documents.reset_docs()
    yield
    documents.reset_docs()


@pytest.fixture
def client():
    return TestClient(app)


def _register(client, username="joey", email="joey@example.com",
              password="a-strong-passphrase"):
    return client.post("/api/v1/auth/register", json={
        "username": username, "email": email, "password": password,
    })


# ─── Registration ────────────────────────────────────────────────────────────

def test_a_user_can_register_and_is_signed_in(client):
    r = _register(client)
    assert r.status_code == 200, r.text
    assert r.json()["user"]["username"] == "joey"
    assert "statedge_session" in r.cookies


def test_registration_never_returns_the_password_hash(client):
    body = _register(client).text
    assert "password_hash" not in body
    assert "argon2" not in body


def test_beta_registrations_receive_the_founding_analyst_badge(client):
    assert "founding_analyst" in _register(client).json()["user"]["badges"]


def test_usernames_are_unique(client):
    assert _register(client).status_code == 200
    dupe = _register(client, email="other@example.com")
    assert dupe.status_code == 400


def test_emails_are_unique(client):
    assert _register(client).status_code == 200
    dupe = _register(client, username="someone")
    assert dupe.status_code == 400


def test_a_collision_does_not_reveal_which_field_collided(client):
    """Confirming an email is registered would let anyone enumerate users."""
    _register(client)
    detail = _register(client, username="someone").json()["detail"].lower()
    assert "email" in detail and "username" in detail   # deliberately ambiguous


def test_a_weak_password_is_rejected_with_a_reason(client):
    r = _register(client, password="short")
    assert r.status_code == 400
    assert "10 characters" in r.json()["detail"]


def test_reserved_usernames_are_refused(client):
    assert _register(client, username="admin").status_code == 400


def test_usernames_are_case_insensitive(client):
    _register(client, username="Joey")
    clash = _register(client, username="JOEY", email="other@example.com")
    assert clash.status_code == 400


# ─── Login / session ─────────────────────────────────────────────────────────

def test_login_by_username_and_by_email(client):
    _register(client)
    client.cookies.clear()
    assert client.post("/api/v1/auth/login", json={
        "identifier": "joey", "password": "a-strong-passphrase"}).status_code == 200
    client.cookies.clear()
    assert client.post("/api/v1/auth/login", json={
        "identifier": "joey@example.com", "password": "a-strong-passphrase"}).status_code == 200


def test_a_wrong_password_is_rejected(client):
    _register(client)
    client.cookies.clear()
    r = client.post("/api/v1/auth/login",
                    json={"identifier": "joey", "password": "not-the-password"})
    assert r.status_code == 401


def test_unknown_account_and_wrong_password_are_indistinguishable(client):
    _register(client)
    client.cookies.clear()
    missing = client.post("/api/v1/auth/login",
                          json={"identifier": "ghost", "password": "whatever-long"})
    wrong = client.post("/api/v1/auth/login",
                        json={"identifier": "joey", "password": "whatever-long"})
    assert missing.status_code == wrong.status_code == 401
    assert missing.json()["detail"] == wrong.json()["detail"]


def test_the_session_persists_across_requests(client):
    _register(client)
    me = client.get("/api/v1/auth/me")
    assert me.json()["user"]["username"] == "joey"


def test_logout_ends_the_session(client):
    _register(client)
    client.post("/api/v1/auth/logout")
    assert client.get("/api/v1/auth/me").json()["user"] is None


def test_an_anonymous_caller_is_not_an_error(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 200
    assert r.json()["user"] is None
    assert r.json()["entitlements"]["level"] == "guest"


def test_the_session_cookie_is_httponly_and_samesite(client):
    """localStorage cannot be marked httpOnly; a cookie can, so XSS can't read it."""
    header = _register(client).headers["set-cookie"].lower()
    assert "httponly" in header
    assert "samesite=lax" in header


def test_a_forged_session_cookie_is_rejected(client):
    _register(client)
    client.cookies.set("statedge_session", "not-a-real-token")
    assert client.get("/api/v1/auth/me").json()["user"] is None


# ─── Profile ─────────────────────────────────────────────────────────────────

def test_a_user_can_update_their_own_profile(client):
    _register(client)
    r = client.patch("/api/v1/auth/profile", json={
        "display_name": "Joey Howorko", "bio": "Football analyst",
        "favourite_sports": ["nfl", "ncaaf"], "onboarded": True,
    })
    assert r.status_code == 200
    user = r.json()["user"]
    assert user["display_name"] == "Joey Howorko"
    assert user["favourite_sports"] == ["nfl", "ncaaf"]
    assert user["onboarded"] is True


def test_profile_updates_require_a_session(client):
    assert client.patch("/api/v1/auth/profile",
                        json={"display_name": "nobody"}).status_code == 401


def test_a_user_cannot_edit_another_account(client):
    """
    The identity comes from the session, never the request body, so there is
    no id to tamper with — the request below can only ever edit its own owner.
    """
    _register(client)
    other = TestClient(app)
    _register(other, username="rival", email="rival@example.com")
    rival_id = other.get("/api/v1/auth/me").json()["user"]["id"]

    client.patch("/api/v1/auth/profile",
                 json={"display_name": "hijacked", "id": rival_id})
    assert other.get("/api/v1/auth/me").json()["user"]["display_name"] != "hijacked"


def test_the_account_level_is_not_user_writable(client):
    _register(client)
    client.patch("/api/v1/auth/profile", json={"display_name": "x", "level": "admin"})
    assert client.get("/api/v1/auth/me").json()["user"]["level"] == "beta"


def test_a_username_can_be_changed_and_the_old_one_freed(client):
    _register(client)
    assert client.patch("/api/v1/auth/username",
                        json={"username": "joeyh"}).status_code == 200
    other = TestClient(app)
    assert _register(other, username="joey", email="new@example.com").status_code == 200


def test_username_availability_is_reported(client):
    assert client.get("/api/v1/auth/username-available?username=freehandle"
                      ).json()["available"] is True
    _register(client, username="freehandle")
    assert client.get("/api/v1/auth/username-available?username=freehandle"
                      ).json()["available"] is False


# ─── Public shape ────────────────────────────────────────────────────────────

def test_the_public_profile_hides_email_and_credentials():
    user = User.new("joey", "joey@example.com", "hash")
    public = user.to_public()
    assert "email" not in public
    assert "password_hash" not in public
    assert "level" not in public   # an entitlement, not a public attribute


# ─── Entitlements ────────────────────────────────────────────────────────────

def test_a_guest_cannot_make_picks_but_can_see_the_leaderboard():
    ent = entitlements_for(None)
    assert ent.has("make_pick") is False
    assert ent.has("leaderboard_full") is True


def test_beta_accounts_receive_pro_features():
    user = User.new("joey", "j@e.com", "h")
    ent = entitlements_for(user)
    assert ent.level == "beta"
    for feature in ("player_props", "advanced_stats", "personal_analytics"):
        assert ent.has(feature) is True, feature


def test_unimplemented_features_are_withheld_from_every_level():
    """The UI must never advertise something the backend cannot serve."""
    user = User.new("joey", "j@e.com", "h")
    user.level = "admin"
    ent = entitlements_for(user)
    assert ent.has("edge_ai") is False
    assert ent.unavailable_reason["edge_ai"]


def test_no_gate_fires_while_the_beta_is_open(monkeypatch):
    """A signed-in beta user must not hit a paywall before one exists."""
    import importlib
    from src.accounts import entitlements as ent_mod
    monkeypatch.setenv("STATEDGE_BETA_OPEN", "1")
    importlib.reload(ent_mod)
    user = User.new("joey", "j@e.com", "h")
    user.level = "free"
    ent = ent_mod.entitlements_for(user)
    assert ent.has("player_props") is True
    importlib.reload(ent_mod)


def test_billing_is_not_enabled():
    assert entitlements_for(None).billing_enabled is False


# ─── Passwords ───────────────────────────────────────────────────────────────

def test_passwords_are_hashed_with_argon2id():
    h = passwords.hash_password("a-strong-passphrase")
    assert h.startswith("$argon2id$")
    assert "a-strong-passphrase" not in h


def test_verification_accepts_the_right_password_only():
    h = passwords.hash_password("a-strong-passphrase")
    assert passwords.verify(h, "a-strong-passphrase") is True
    assert passwords.verify(h, "a-strong-passphras") is False


def test_verification_of_a_corrupt_hash_returns_false_rather_than_raising():
    assert passwords.verify("not-a-hash", "anything") is False


@pytest.mark.parametrize("bad", ["ab", "admin", "has space", "x" * 30, "Joey!"])
def test_invalid_usernames_are_refused(bad):
    with pytest.raises(InvalidUsername):
        normalise_username(bad)
