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
    assert ent.has("alerts") is False
    assert ent.unavailable_reason["alerts"]


def test_a_built_feature_is_still_withheld_where_it_cannot_run(monkeypatch):
    """
    Edge AI is implemented, but a deployment with no model behind it cannot
    serve it. Listing it on the plan there would advertise something that does
    not work, which is the same fault as shipping it unimplemented.
    """
    from src.ai import provider as provider_mod
    user = User.new("joey", "j@e.com", "h")
    user.level = "admin"

    provider_mod.set_provider(provider_mod.UnconfiguredProvider())
    try:
        ent = entitlements_for(user)
        assert ent.has("edge_ai") is False
        assert "configured" in ent.unavailable_reason["edge_ai"]
    finally:
        provider_mod.set_provider(None)


def test_edge_ai_is_offered_once_a_model_is_configured(monkeypatch):
    from src.ai import provider as provider_mod
    user = User.new("joey", "j@e.com", "h")
    user.level = "admin"

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    provider_mod.set_provider(provider_mod.AnthropicProvider())
    try:
        assert entitlements_for(user).has("edge_ai") is True
    finally:
        provider_mod.set_provider(None)


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


# ─── Cross-origin diagnostics ────────────────────────────────────────────────

def test_me_reports_whether_a_session_cookie_arrived(client):
    """
    statedge.ca proxies /api to Fly, so a cookie can be dropped in transit.
    "Signed in but seen as a guest" and "never signed in" are indistinguishable
    from the browser without this.
    """
    anon = TestClient(app).get("/api/v1/auth/me").json()
    assert anon["debug"]["session_cookie_present"] is False

    _register(client)
    signed_in = client.get("/api/v1/auth/me").json()
    assert signed_in["debug"]["session_cookie_present"] is True
    assert "statedge_session" in signed_in["debug"]["cookies_received"]


def test_the_diagnostic_never_exposes_a_cookie_value(client):
    _register(client)
    body = client.get("/api/v1/auth/me").text
    token = client.cookies.get("statedge_session")
    assert token
    assert token not in body      # names only, never values


def test_the_cookie_policy_can_be_widened_for_a_cross_site_api(monkeypatch):
    """
    A Lax cookie is not sent when the browser calls the API host directly,
    which looks exactly like being signed out right after signing in.
    """
    import importlib
    from src.accounts import sessions as sess
    monkeypatch.setenv("SESSION_SAMESITE", "none")
    importlib.reload(sess)
    kwargs = sess.cookie_kwargs("2026-10-01T00:00:00+00:00")
    assert kwargs["samesite"] == "none"
    # Browsers reject SameSite=None without Secure, so it is forced on.
    assert kwargs["secure"] is True
    monkeypatch.delenv("SESSION_SAMESITE")
    importlib.reload(sess)


def test_an_unrecognised_samesite_value_falls_back_to_lax(monkeypatch):
    import importlib
    from src.accounts import sessions as sess
    monkeypatch.setenv("SESSION_SAMESITE", "banana")
    importlib.reload(sess)
    assert sess.SAMESITE == "lax"
    monkeypatch.delenv("SESSION_SAMESITE")
    importlib.reload(sess)


def test_the_production_site_is_an_allowed_origin():
    from src.config import settings
    assert "https://statedge.ca" in settings.cors_origins


def test_the_cookie_can_be_scoped_to_a_parent_domain(monkeypatch):
    """
    api.statedge.ca and statedge.ca share a registrable domain, so a cookie
    scoped to ".statedge.ca" is first-party for both — which is what survives
    Safari's third-party cookie blocking.
    """
    import importlib
    from src.accounts import sessions as sess
    monkeypatch.setenv("SESSION_COOKIE_DOMAIN", ".statedge.ca")
    importlib.reload(sess)
    assert sess.cookie_kwargs("2026-10-01T00:00:00+00:00")["domain"] == ".statedge.ca"
    monkeypatch.delenv("SESSION_COOKIE_DOMAIN")
    importlib.reload(sess)


def test_no_domain_is_set_by_default(monkeypatch):
    """Host-only is correct when the API and site are the same host."""
    import importlib
    from src.accounts import sessions as sess
    monkeypatch.delenv("SESSION_COOKIE_DOMAIN", raising=False)
    importlib.reload(sess)
    assert "domain" not in sess.cookie_kwargs("2026-10-01T00:00:00+00:00")


# ─── Bearer fallback for cookie-stripping proxies ────────────────────────────

def test_a_bearer_token_authenticates_when_no_cookie_arrives(client):
    """
    Vercel's rewrite to an external host drops the Cookie header, which made a
    cookie-only session unusable in production however correct it was.
    """
    token = _register(client).json()["session_token"]
    assert token

    bare = TestClient(app)          # a client with no cookies at all
    me = bare.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["user"]["username"] == "joey"
    assert me.json()["debug"]["session_cookie_present"] is False
    assert me.json()["debug"]["bearer_present"] is True


def test_login_also_returns_a_token(client):
    _register(client)
    client.cookies.clear()
    body = client.post("/api/v1/auth/login", json={
        "identifier": "joey", "password": "a-strong-passphrase"}).json()
    assert body["session_token"]


def test_a_forged_bearer_token_is_rejected():
    bare = TestClient(app)
    me = bare.get("/api/v1/auth/me", headers={"Authorization": "Bearer nonsense"})
    assert me.json()["user"] is None


def test_a_malformed_authorization_header_is_ignored():
    bare = TestClient(app)
    for header in ("", "Bearer", "Basic abc", "Bearer   "):
        assert bare.get("/api/v1/auth/me",
                        headers={"Authorization": header}).json()["user"] is None


def test_the_cookie_wins_when_both_are_present(client):
    """The httpOnly cookie is the stronger credential, so it takes precedence."""
    _register(client)
    me = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer stale-token"})
    assert me.json()["user"]["username"] == "joey"


def test_logout_works_over_bearer_too(client):
    token = _register(client).json()["session_token"]
    bare = TestClient(app)
    headers = {"Authorization": f"Bearer {token}"}
    assert bare.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert bare.get("/api/v1/auth/me", headers=headers).json()["user"] is None


def test_picks_can_be_published_over_bearer(client):
    """The whole point: accounts and picks both work behind the proxy."""
    from datetime import datetime, timedelta, timezone
    token = _register(client).json()["session_token"]
    bare = TestClient(app)
    kickoff = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat(timespec="seconds")
    r = bare.post("/api/v1/picks", headers={"Authorization": f"Bearer {token}"}, json={
        "league": "ncaaf", "event_id": "401752", "home": "A", "away": "B",
        "kickoff": kickoff, "market": "moneyline", "side": "home",
        "selection": "A", "confidence": 70,
    })
    assert r.status_code == 200, r.text
    assert r.json()["username"] == "joey"
