"""
Password changes, profile photos and staff roles.

The security-relevant behaviour is what these check: a password change must
evict other sessions, an uploaded file must be an image because of its own
bytes rather than because the caller said so, and staff access must come from
the deployment rather than from anything a request can write.
"""
from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient

from src.accounts import avatars, models, sessions
from src.accounts.models import has_power, role_for, staff_config_report
from src.api.main import app

client = TestClient(app)

# The smallest real files of each type, used to check sniffing rather than
# rendering — nothing here decodes an image.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"\x00" * 40
GIF = b"GIF89a" + b"\x00" * 40
WEBP = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 40


# ── image validation ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("data,expected", [
    (PNG, "image/png"),
    (JPEG, "image/jpeg"),
    (GIF, "image/gif"),
    (WEBP, "image/webp"),
])
def test_the_format_is_read_from_the_bytes_not_the_claim(data, expected):
    assert avatars.sniff_content_type(data) == expected


def test_an_svg_is_refused_however_it_is_labelled():
    """
    SVG is a document that can carry script. Serving one from our own origin
    would be a stored-XSS hole, so it is not an accepted format at all.
    """
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    assert avatars.sniff_content_type(svg) is None
    with pytest.raises(avatars.InvalidImage):
        avatars.decode_upload(base64.b64encode(svg).decode())


def test_a_declared_content_type_cannot_smuggle_a_non_image():
    """A data: URL announcing image/png does not make the payload a PNG."""
    payload = base64.b64encode(b"#!/bin/sh\nrm -rf /\n").decode()
    with pytest.raises(avatars.InvalidImage):
        avatars.decode_upload(f"data:image/png;base64,{payload}")


def test_a_data_url_and_a_bare_payload_are_both_accepted():
    encoded = base64.b64encode(PNG).decode()
    bare, _ = avatars.decode_upload(encoded)
    prefixed, _ = avatars.decode_upload(f"data:image/png;base64,{encoded}")
    assert bare == prefixed == PNG


def test_an_oversized_image_is_refused_before_it_is_decoded():
    oversized = base64.b64encode(b"\xff\xd8\xff" + b"\x00" * (avatars.MAX_BYTES + 10)).decode()
    with pytest.raises(avatars.InvalidImage) as exc:
        avatars.decode_upload(oversized)
    assert "too large" in str(exc.value).lower()


def test_empty_and_unreadable_uploads_are_refused_with_a_reason():
    for bad in ("", "   ", "not base64 at all!!", "data:image/png;base64,"):
        with pytest.raises(avatars.InvalidImage):
            avatars.decode_upload(bad)


def test_the_url_changes_when_the_image_does():
    """A new photo must not sit behind a week-long cache of the old one."""
    first = avatars.url_for("u1", "aaaaaaaaaaaaaaaa")
    second = avatars.url_for("u1", "bbbbbbbbbbbbbbbb")
    assert first != second
    assert first.startswith("/api/v1/avatars/u1")


# ── staff roles ──────────────────────────────────────────────────────────────

def test_roles_come_from_the_environment_and_the_highest_one_wins(monkeypatch):
    monkeypatch.setattr(models, "ADMIN_USERNAMES", {"boss"})
    monkeypatch.setattr(models, "STAFF_USERNAMES", {"boss", "helper"})
    monkeypatch.setattr(models, "MODERATOR_USERNAMES", {"mod"})
    assert role_for("boss") == "admin"
    assert role_for("helper") == "staff"
    assert role_for("mod") == "moderator"
    assert role_for("nobody") is None
    assert role_for("BOSS") == "admin"      # case and spacing are forgiven
    assert role_for("  boss ") == "admin"


def test_each_role_carries_only_the_powers_it_should():
    assert has_power("admin", "manage_users") is True
    assert has_power("staff", "manage_users") is False
    assert has_power("staff", "view_staff") is True
    assert has_power("moderator", "view_staff") is False
    assert has_power("moderator", "moderate") is True
    # An ordinary account has none of them.
    for power in ("view_staff", "manage_users", "moderate", "configure"):
        assert has_power("beta", power) is False
        assert has_power("guest", power) is False


def test_the_config_report_counts_roles_without_naming_anyone(monkeypatch):
    monkeypatch.setattr(models, "ADMIN_USERNAMES", {"someone-private"})
    monkeypatch.setattr(models, "STAFF_USERNAMES", set())
    monkeypatch.setattr(models, "MODERATOR_USERNAMES", set())
    report = staff_config_report()
    assert report["admin"] == 1
    assert report["any_configured"] is True
    assert "someone-private" not in repr(report)


# ── the staff area is not protected by being hidden ──────────────────────────

def test_an_anonymous_visitor_typing_the_staff_url_gets_nothing():
    for path in ("/api/v1/admin/overview", "/api/v1/admin/users", "/api/v1/admin/picks"):
        assert client.get(path).status_code in (401, 404)


def test_the_staff_routes_remain_read_only():
    """
    No route here may alter a graded pick. A staff tool that could quietly
    rewrite a result would undermine the one claim the product makes.
    """
    for route in app.routes:
        path = getattr(route, "path", "")
        if path.startswith("/api/v1/admin"):
            assert set(getattr(route, "methods", set())) <= {"GET", "HEAD", "OPTIONS"}


# ── sessions ─────────────────────────────────────────────────────────────────

def test_ending_all_sessions_leaves_other_accounts_alone(tmp_path, monkeypatch):
    monkeypatch.setenv("STATEDGE_DB", str(tmp_path / "sessions.db"))
    mine_a, _ = sessions.create("user-a")
    mine_b, _ = sessions.create("user-a")
    theirs, _ = sessions.create("user-b")

    ended = sessions.destroy_all("user-a")

    assert ended == 2
    assert sessions.resolve(mine_a) is None
    assert sessions.resolve(mine_b) is None
    assert sessions.resolve(theirs) == "user-b"


def test_ending_sessions_for_an_account_with_none_is_not_an_error():
    assert sessions.destroy_all("nobody-at-all") == 0
