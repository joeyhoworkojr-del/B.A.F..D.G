"""
Live game chat: sanitisation, authorization, moderation and restraint.

The tests that matter here are the ones about abuse. A chat is the part of a
product where other people's input reaches your users, so most of this is about
what the server refuses.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.accounts.models import User
from src.api.main import app
from src.chat import events, moderation, service
from src.chat.models import InvalidMessage, Message, game_id, sanitise
from src.chat.store import get_rooms, reset_rooms

client = TestClient(app)


def person(uid="u1", username="fan", level="beta") -> User:
    user = User.new(username, f"{username}@example.com", "hash")
    user.id = uid
    user.level = level
    user.display_name = username.title()
    return user


@pytest.fixture(autouse=True)
def _clean(tmp_path, monkeypatch):
    monkeypatch.setenv("LEDGER_PATH", str(tmp_path / "chat.db"))
    from src.store import documents
    documents.reset_docs()
    reset_rooms()
    moderation.reset_rate_state()
    service.reset_reactions()
    events.reset()
    yield
    reset_rooms()
    moderation.reset_rate_state()
    documents.reset_docs()


# ── sanitisation ─────────────────────────────────────────────────────────────

def test_message_text_is_never_treated_as_markup():
    """
    The client renders text into a text node, so this is belt and braces — but
    the stored value should be what was typed, not something re-encoded into a
    shape a future careless renderer could execute.
    """
    typed = '<script>alert(1)</script>'
    assert sanitise(typed) == typed          # stored verbatim, never as HTML
    assert "&lt;" not in sanitise(typed)     # and not double-encoded either


def test_bidirectional_overrides_are_stripped():
    """
    These characters make text render in an order other than the one it is
    stored in — the classic way to make a message read as something else.
    """
    assert sanitise("safe‮txet suoregnad") == "safetxet suoregnad"
    assert "‮" not in sanitise("a‮b")


def test_control_characters_are_stripped_but_newlines_survive():
    assert sanitise("a\x00\x07b") == "ab"
    assert sanitise("one\ntwo") == "one\ntwo"


def test_empty_and_oversized_messages_are_refused():
    for bad in ("", "   ", "\n\n", "x" * 5000):
        with pytest.raises(InvalidMessage):
            sanitise(bad)


def test_newline_spam_is_collapsed_then_capped():
    # Runs are collapsed rather than refused, because that is a formatting
    # accident more often than an attack.
    assert sanitise("a\n\n\n\n\nb") == "a\n\nb"
    # But a wall of single newlines is deliberate.
    with pytest.raises(InvalidMessage):
        sanitise("\n".join("abcdefgh"))


def test_rooms_are_keyed_per_game_so_a_rematch_gets_a_fresh_room():
    assert game_id("nfl", "401") != game_id("nfl", "402")
    assert game_id("nfl", "401") != game_id("ncaaf", "401")
    assert game_id(" NFL ", " 401 ") == "nfl:401"


# ── posting and reading ──────────────────────────────────────────────────────

def test_a_message_appears_for_the_next_reader():
    service.post(person(), "nfl", "1", "Buffalo look sharp")
    payload = service.since("nfl", "1")
    assert [m["text"] for m in payload["messages"]] == ["Buffalo look sharp"]


def test_reading_by_cursor_returns_only_what_is_new():
    author = person()
    service.post(author, "nfl", "1", "first")
    first = service.since("nfl", "1")
    service.post(author, "nfl", "1", "second")

    fresh = service.since("nfl", "1", after=first["cursor"])
    assert [m["text"] for m in fresh["messages"]] == ["second"]

    # And a quiet room returns nothing rather than the whole history again.
    assert service.since("nfl", "1", after=fresh["cursor"])["messages"] == []


def test_a_reply_carries_a_preview_of_what_it_answers():
    author = person()
    parent = service.post(author, "nfl", "1", "Who is covering the tight end?")
    reply = service.post(person("u2", "other"), "nfl", "1", "Nobody, evidently",
                         reply_to=parent.id)
    assert reply.reply_to == parent.id
    assert "tight end" in reply.reply_preview


def test_replying_to_a_message_that_has_gone_still_posts():
    """The person's words matter more than the thread link."""
    reply = service.post(person(), "nfl", "1", "still worth saying",
                         reply_to="a-message-that-never-existed")
    assert reply.reply_to is None
    assert reply.text == "still worth saying"


def test_mine_is_true_only_for_the_viewer_who_wrote_it():
    author = person("u1", "author")
    service.post(author, "nfl", "1", "hello")
    mine = service.since("nfl", "1", viewer=author)["messages"][0]
    theirs = service.since("nfl", "1", viewer=person("u2", "other"))["messages"][0]
    assert mine["mine"] is True
    assert theirs["mine"] is False


# ── rate limits and spam ─────────────────────────────────────────────────────

def test_flooding_one_room_is_stopped():
    author = person()
    for i in range(moderation.MESSAGES_PER_ROOM_PER_MINUTE):
        service.post(author, "nfl", "1", f"message {i}")
    with pytest.raises(moderation.Blocked) as exc:
        service.post(author, "nfl", "1", "one too many")
    assert "too quickly" in str(exc.value)


def test_repeated_flooding_earns_an_automatic_mute():
    author = person()
    for i in range(moderation.MESSAGES_PER_ROOM_PER_MINUTE):
        service.post(author, "nfl", "1", f"message {i}")
    blocked = 0
    for _ in range(moderation.FLOOD_STRIKES_BEFORE_MUTE):
        try:
            service.post(author, "nfl", "1", "again")
        except moderation.Blocked as exc:
            blocked += 1
            last = str(exc)
    assert blocked == moderation.FLOOD_STRIKES_BEFORE_MUTE
    assert "muted" in last
    assert moderation.active_sanction(author.id, game_id("nfl", "1")) is not None


def test_saying_the_same_thing_repeatedly_is_refused():
    author = person()
    for _ in range(moderation.MAX_IDENTICAL_IN_A_ROW):
        service.post(author, "nfl", "1", "LOCK OF THE YEAR")
    with pytest.raises(moderation.Blocked) as exc:
        service.post(author, "nfl", "1", "LOCK OF THE YEAR")
    assert "already said that" in str(exc.value)


def test_a_limit_in_one_room_does_not_silence_another():
    author = person()
    for i in range(moderation.MESSAGES_PER_ROOM_PER_MINUTE):
        service.post(author, "nfl", "1", f"message {i}")
    # A different game is a different room and a different limit.
    assert service.post(author, "nfl", "2", "hello elsewhere").text == "hello elsewhere"


# ── sanctions ────────────────────────────────────────────────────────────────

def test_a_mute_stops_posting_in_that_room_only():
    author = person()
    moderation.mute(author.id, minutes=10, game_id=game_id("nfl", "1"), reason="test")
    with pytest.raises(moderation.Blocked):
        service.post(author, "nfl", "1", "hello")
    assert service.post(author, "nfl", "2", "hello").text == "hello"


def test_a_suspension_stops_posting_everywhere():
    author = person()
    moderation.suspend(author.id, days=None, reason="abuse")
    for event in ("1", "2", "99"):
        with pytest.raises(moderation.Blocked) as exc:
            service.post(author, "nfl", event, "hello")
        assert "suspended" in str(exc.value)


def test_an_expired_sanction_stops_applying():
    author = person()
    moderation.mute(author.id, minutes=-1, game_id=game_id("nfl", "1"))
    assert moderation.active_sanction(author.id, game_id("nfl", "1")) is None


def test_a_sanction_with_an_unreadable_expiry_fails_open():
    """
    A bug in the stored value should not silence someone forever. Staff can
    reissue; an account nobody can un-mute is worse.
    """
    s = moderation.Sanction(user_id="u1", kind="mute", expires_at="not-a-date")
    assert s.active() is False


def test_lifting_a_sanction_restores_posting():
    author = person()
    moderation.mute(author.id, minutes=60, game_id=game_id("nfl", "1"))
    moderation.lift(author.id, "mute", game_id("nfl", "1"))
    assert service.post(author, "nfl", "1", "back").text == "back"


def test_sanctions_survive_the_process_that_issued_them():
    """
    A suspension that evaporated on the next deploy would not be a sanction.
    Rate-limit state may be reset; this may not.
    """
    author = person()
    moderation.suspend(author.id, days=7, reason="abuse")
    moderation.reset_rate_state()
    reset_rooms()
    assert moderation.active_sanction(author.id, "nfl:1") is not None


# ── deletion, reactions, reports ─────────────────────────────────────────────

def test_you_may_delete_your_own_message_and_not_someone_elses():
    author = person("u1", "author")
    message = service.post(author, "nfl", "1", "oops")
    with pytest.raises(service.NotAllowed):
        service.delete(person("u2", "other"), "nfl", "1", message.id)
    assert service.delete(author, "nfl", "1", message.id).deleted is True


def test_staff_may_delete_anyones_message():
    message = service.post(person("u1", "author"), "nfl", "1", "abusive")
    staff = person("u9", "refspot", level="moderator")
    assert service.delete(staff, "nfl", "1", message.id).deleted is True


def test_a_deleted_message_keeps_its_place_but_loses_its_text():
    """
    Removing the row would renumber the cursor everyone is paging from and
    leave replies pointing at nothing.
    """
    author = person()
    message = service.post(author, "nfl", "1", "secret")
    service.post(author, "nfl", "1", "after")
    service.delete(author, "nfl", "1", message.id)

    messages = service.since("nfl", "1")["messages"]
    assert len(messages) == 2
    assert messages[0]["deleted"] is True
    assert messages[0]["text"] == ""
    assert messages[1]["text"] == "after"


def test_a_reaction_toggles_and_counts_people_not_clicks():
    author = person("u1")
    message = service.post(author, "nfl", "1", "great call")
    for _ in range(5):
        service.react(author, "nfl", "1", message.id, "🔥")
        service.react(author, "nfl", "1", message.id, "🔥")
    after = service.react(author, "nfl", "1", message.id, "🔥")
    assert after.reactions == {"🔥": 1}
    service.react(author, "nfl", "1", message.id, "🔥")
    assert service.since("nfl", "1")["messages"][0]["reactions"] == {}


def test_an_arbitrary_emoji_is_not_a_reaction():
    """A free-text reaction would be a second, unmoderated message channel."""
    message = service.post(person(), "nfl", "1", "hi")
    with pytest.raises(InvalidMessage):
        service.react(person(), "nfl", "1", message.id, "🖕")


def test_enough_distinct_reporters_hide_a_message_but_do_not_delete_it():
    message = service.post(person("author", "author"), "nfl", "1", "questionable")
    for i in range(moderation.REPORTS_TO_HIDE):
        service.report(person(f"r{i}", f"reporter{i}"), "nfl", "1", message.id)

    shown = service.since("nfl", "1")["messages"][0]
    assert shown["hidden"] is True
    assert shown["deleted"] is False        # nobody has judged it yet
    assert shown["text"] == ""


def test_one_person_cannot_hide_a_message_alone():
    message = service.post(person("author", "author"), "nfl", "1", "unpopular opinion")
    reporter = person("r1", "reporter")
    for _ in range(10):
        service.report(reporter, "nfl", "1", message.id)
    assert service.since("nfl", "1")["messages"][0]["hidden"] is False


def test_you_cannot_report_yourself():
    author = person()
    message = service.post(author, "nfl", "1", "hello")
    with pytest.raises(service.NotAllowed):
        service.report(author, "nfl", "1", message.id)


def test_staff_can_restore_a_message_that_was_reported_but_is_fine():
    message = service.post(person("author", "author"), "nfl", "1", "fine actually")
    for i in range(moderation.REPORTS_TO_HIDE):
        service.report(person(f"r{i}", f"reporter{i}"), "nfl", "1", message.id)
    staff = person("u9", "refspot", level="moderator")
    assert service.restore(staff, "nfl", "1", message.id).hidden is False
    assert moderation.open_reports() == []


def test_an_ordinary_user_cannot_restore():
    message = service.post(person("author", "author"), "nfl", "1", "hi")
    with pytest.raises(service.NotAllowed):
        service.restore(person("u2", "other"), "nfl", "1", message.id)


# ── Stat Edge system messages ────────────────────────────────────────────────

def test_the_first_reading_only_sets_a_baseline():
    assert events.consider(
        league="nfl", event_id="1", home_abbr="BUF", away_abbr="KC",
        home_win=0.58, home_score=0, away_score=0,
    ) is None


def test_a_small_drift_is_not_worth_interrupting_anyone():
    common = dict(league="nfl", event_id="1", home_abbr="BUF", away_abbr="KC",
                  home_score=0, away_score=0)
    events.consider(home_win=0.58, **common)
    assert events.consider(home_win=0.60, **common) is None


def test_a_real_swing_is_announced_with_the_reason():
    common = dict(league="nfl", event_id="1", home_abbr="BUF", away_abbr="KC",
                  home_score=0, away_score=0)
    events.consider(home_win=0.50, **common)
    text = events.consider(home_win=0.68, drive_note="1st & goal at the KC 5.", **common)
    assert text is not None
    assert "BUF" in text and "goal" in text
    # And it actually reaches the room.
    assert any(m["system"] for m in service.since("nfl", "1")["messages"])


def test_the_room_is_not_spammed_by_a_second_swing_inside_the_cooldown():
    common = dict(league="nfl", event_id="1", home_abbr="BUF", away_abbr="KC",
                  home_score=0, away_score=0)
    events.consider(home_win=0.50, **common)
    assert events.consider(home_win=0.70, **common) is not None
    assert events.consider(home_win=0.90, **common) is None


def test_a_score_is_always_worth_a_line():
    events.consider(league="nfl", event_id="1", home_abbr="BUF", away_abbr="KC",
                    home_win=0.50, home_score=0, away_score=0)
    text = events.consider(league="nfl", event_id="1", home_abbr="BUF", away_abbr="KC",
                           home_win=0.52, home_score=7, away_score=0)
    assert text is not None and "7" in text


def test_a_system_message_cannot_be_deleted_by_an_ordinary_user():
    events.consider(league="nfl", event_id="1", home_abbr="BUF", away_abbr="KC",
                    home_win=0.50, home_score=0, away_score=0)
    events.consider(league="nfl", event_id="1", home_abbr="BUF", away_abbr="KC",
                    home_win=0.70, home_score=0, away_score=0)
    system = next(m for m in service.since("nfl", "1")["messages"] if m["system"])
    with pytest.raises(service.NotAllowed):
        service.delete(person("u2", "other"), "nfl", "1", system["id"])


def test_a_system_message_exposes_no_user_id():
    events.consider(league="nfl", event_id="1", home_abbr="BUF", away_abbr="KC",
                    home_win=0.50, home_score=0, away_score=0)
    events.consider(league="nfl", event_id="1", home_abbr="BUF", away_abbr="KC",
                    home_win=0.70, home_score=0, away_score=0)
    system = next(m for m in service.since("nfl", "1")["messages"] if m["system"])
    assert system["user_id"] == ""
    assert system["mine"] is False


# ── the HTTP surface ─────────────────────────────────────────────────────────

def test_reading_a_room_needs_no_account_but_posting_does():
    assert client.get("/api/v1/chat/nfl/401752").status_code == 200
    assert client.post("/api/v1/chat/nfl/401752", json={"text": "hi"}).status_code in (401, 403)


def test_the_moderation_queue_is_not_public():
    for path, method in (
        ("/api/v1/chat-moderation/reports", "get"),
        ("/api/v1/chat-moderation/mute", "post"),
        ("/api/v1/chat-moderation/suspend", "post"),
    ):
        call = getattr(client, method)
        response = call(path, json={"user_id": "victim"}) if method == "post" else call(path)
        assert response.status_code in (401, 404), path


def test_the_moderation_paths_cannot_be_mistaken_for_a_room():
    """
    /chat/moderation/reports would be two segments after /chat and would match
    the room route first — so moderation lives on its own prefix.
    """
    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/api/v1/chat-moderation/reports" in paths
    assert "/api/v1/chat/moderation/reports" not in paths


def test_chat_replies_are_never_cached_by_a_proxy():
    response = client.get("/api/v1/chat/nfl/401752")
    assert "no-store" in response.headers.get("cache-control", "")
