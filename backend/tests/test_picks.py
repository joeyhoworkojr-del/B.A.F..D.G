"""
Verified pick integrity: submission, locking, grading and records.

Mirrors the PICKS acceptance list. The locking tests matter most — a track
record is only worth publishing if a losing pick could not have been edited or
deleted after the event started.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.picks import grading, service
from src.picks.models import Pick, PickError
from src.store import documents


def iso(hours: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat(timespec="seconds")


@pytest.fixture(autouse=True)
def clean_store(tmp_path, monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("LEDGER_PATH", str(tmp_path / "picks.db"))
    documents.reset_docs()
    yield
    documents.reset_docs()


@pytest.fixture
def client():
    c = TestClient(app)
    c.post("/api/v1/auth/register", json={
        "username": "joey", "email": "joey@example.com",
        "password": "a-strong-passphrase"})
    return c


def pick_body(**kw) -> dict:
    body = dict(league="ncaaf", event_id="401752", home="Florida State",
                away="Clemson", kickoff=iso(3), market="spread", side="home",
                selection="Florida State +3", line=3.0, price_american=-110,
                odds_source="ESPN BET", confidence=72,
                reasoning="The model reads the line as too short.")
    body.update(kw)
    return body


# ─── Submission ──────────────────────────────────────────────────────────────

def test_a_signed_in_user_can_publish_a_pick(client):
    r = client.post("/api/v1/picks", json=pick_body())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["selection"] == "Florida State +3"
    assert body["confidence"] == 72
    assert body["result"] == "pending"
    assert body["locked"] is False


def test_the_line_and_price_are_stored_as_submitted(client):
    body = client.post("/api/v1/picks", json=pick_body()).json()
    assert body["line"] == 3.0
    assert body["price_american"] == -110
    assert body["odds_source"] == "ESPN BET"


def test_the_submission_is_timestamped(client):
    assert client.post("/api/v1/picks", json=pick_body()).json()["created_at"]


def test_reasoning_is_stored(client):
    body = client.post("/api/v1/picks", json=pick_body()).json()
    assert body["reasoning"].startswith("The model reads")


def test_publishing_requires_an_account():
    anon = TestClient(app)
    assert anon.post("/api/v1/picks", json=pick_body()).status_code == 401


def test_a_pick_after_kickoff_is_refused(client):
    r = client.post("/api/v1/picks", json=pick_body(kickoff=iso(-1)))
    assert r.status_code == 400
    assert "already started" in r.json()["detail"]


def test_a_duplicate_market_on_the_same_game_is_refused(client):
    """Otherwise a user could take both sides and claim whichever won."""
    client.post("/api/v1/picks", json=pick_body())
    dupe = client.post("/api/v1/picks", json=pick_body(side="away"))
    assert dupe.status_code == 400


def test_a_different_market_on_the_same_game_is_allowed(client):
    client.post("/api/v1/picks", json=pick_body())
    other = client.post("/api/v1/picks", json=pick_body(
        market="total", side="over", selection="Over 52.5", line=52.5))
    assert other.status_code == 200


@pytest.mark.parametrize("confidence", [49, 100, 0, -5])
def test_confidence_outside_the_allowed_band_is_refused(client, confidence):
    assert client.post("/api/v1/picks",
                       json=pick_body(confidence=confidence)).status_code == 400


def test_a_side_that_does_not_belong_to_the_market_is_refused(client):
    assert client.post("/api/v1/picks",
                       json=pick_body(market="total", side="home")).status_code == 400


# ─── Locking ─────────────────────────────────────────────────────────────────

def test_a_pick_can_be_edited_before_kickoff(client):
    pick_id = client.post("/api/v1/picks", json=pick_body()).json()["id"]
    r = client.patch(f"/api/v1/picks/{pick_id}", json={"confidence": 80})
    assert r.status_code == 200
    assert r.json()["confidence"] == 80


def test_a_locked_pick_cannot_be_edited(client):
    """The core integrity rule, enforced server-side."""
    pick = service.submit(user_id="u1", username="joey", league="ncaaf",
                          event_id="9", home="A", away="B", kickoff=iso(2),
                          market="moneyline", side="home", selection="A")
    pick.kickoff = iso(-1)          # the game has now started
    service._save(pick)
    with pytest.raises(PickError):
        service.update(pick, confidence=99)


def test_a_locked_pick_cannot_be_deleted(client):
    pick = service.submit(user_id="u1", username="joey", league="ncaaf",
                          event_id="9", home="A", away="B", kickoff=iso(2),
                          market="moneyline", side="home", selection="A")
    pick.kickoff = iso(-1)
    service._save(pick)
    with pytest.raises(PickError):
        service.delete(pick)


def test_the_api_refuses_to_edit_a_locked_pick(client):
    pick_id = client.post("/api/v1/picks", json=pick_body()).json()["id"]
    stored = service.get(pick_id)
    stored.kickoff = iso(-1)
    service._save(stored)
    assert client.patch(f"/api/v1/picks/{pick_id}",
                        json={"confidence": 99}).status_code == 409
    assert client.delete(f"/api/v1/picks/{pick_id}").status_code == 409


def test_an_unparseable_kickoff_locks_rather_than_opens():
    """A bad timestamp must not become a way to edit a pick mid-game."""
    assert Pick.new(user_id="u", username="j", game_id="g", league="nfl",
                    event_id="1", home="A", away="B", market="moneyline",
                    side="home", selection="A", kickoff="not-a-date").is_locked()


def test_a_user_cannot_edit_someone_elses_pick(client):
    pick_id = client.post("/api/v1/picks", json=pick_body()).json()["id"]
    rival = TestClient(app)
    rival.post("/api/v1/auth/register", json={
        "username": "rival", "email": "rival@example.com",
        "password": "another-strong-pass"})
    # 404, not 403 — a 403 would confirm the pick exists.
    assert rival.patch(f"/api/v1/picks/{pick_id}",
                       json={"confidence": 99}).status_code == 404
    assert rival.delete(f"/api/v1/picks/{pick_id}").status_code == 404


# ─── Grading ─────────────────────────────────────────────────────────────────

def test_moneyline_grading():
    assert grading.grade_moneyline("home", 27, 24) == "win"
    assert grading.grade_moneyline("away", 27, 24) == "loss"
    assert grading.grade_moneyline("home", 24, 24) == "push"


def test_spread_grading_uses_the_recorded_line():
    # Home +3: home loses by 2, so the pick covers.
    assert grading.grade_spread("home", 3.0, 21, 23) == "win"
    # Home -3: home wins by 2, so the pick does not cover.
    assert grading.grade_spread("home", -3.0, 23, 21) == "loss"


def test_a_spread_landing_exactly_on_the_number_is_a_push():
    assert grading.grade_spread("home", -3.0, 24, 21) == "push"
    assert grading.grade_spread("away", -3.0, 24, 21) == "push"


def test_a_total_landing_exactly_on_the_number_is_a_push():
    assert grading.grade_total("over", 45.0, 24, 21) == "push"


def test_total_grading():
    assert grading.grade_total("over", 45.5, 24, 24) == "win"
    assert grading.grade_total("under", 45.5, 24, 24) == "loss"


def test_a_missing_line_voids_rather_than_guesses():
    assert grading.grade_spread("home", None, 27, 24) == "void"
    assert grading.grade_total("over", None, 27, 24) == "void"


def test_units_follow_the_recorded_price():
    assert grading.units_for("win", -110) == pytest.approx(0.909, abs=1e-3)
    assert grading.units_for("win", 150) == 1.5
    assert grading.units_for("loss", 150) == -1.0
    assert grading.units_for("push", -110) == 0.0
    assert grading.units_for("void", -110) == 0.0


def test_a_missing_price_settles_at_the_standard_minus_110():
    assert grading.units_for("win", None) == pytest.approx(0.909, abs=1e-3)


def test_grading_a_game_settles_its_picks(client):
    client.post("/api/v1/picks", json=pick_body())
    assert service.grade_game("ncaaf:401752", home_score=21, away_score=23) == 1
    [pick] = service.for_user(service.all_picks()[0].user_id)
    assert pick.result == "win"     # Florida State +3, lost by 2
    assert pick.final_home == 21


def test_grading_is_idempotent(client):
    """A feed reporting the same final twice must not move a record twice."""
    client.post("/api/v1/picks", json=pick_body())
    assert service.grade_game("ncaaf:401752", 21, 23) == 1
    assert service.grade_game("ncaaf:401752", 21, 23) == 0
    assert service.grade_game("ncaaf:401752", 99, 0) == 0    # nor rewrite it


def test_a_postponed_game_voids_pending_picks(client):
    client.post("/api/v1/picks", json=pick_body())
    assert service.void_game("ncaaf:401752") == 1
    assert service.all_picks()[0].result == "void"


# ─── Records ─────────────────────────────────────────────────────────────────

def test_pending_picks_do_not_count_toward_the_record(client):
    client.post("/api/v1/picks", json=pick_body())
    record = client.get("/api/v1/picks/mine").json()["record"]
    assert record["pending"] == 1
    assert record["graded"] == 0
    assert record["win_rate"] is None      # not 0% — nothing has settled


def test_the_record_updates_after_grading(client):
    client.post("/api/v1/picks", json=pick_body())
    service.grade_game("ncaaf:401752", 21, 23)
    record = client.get("/api/v1/picks/mine").json()["record"]
    assert (record["wins"], record["losses"]) == (1, 0)
    assert record["win_rate"] == 1.0
    # The record rounds to two places for display; the pick keeps three.
    assert record["units"] == 0.91


def test_pushes_are_excluded_from_win_rate(client):
    client.post("/api/v1/picks", json=pick_body(line=-2.0, side="home"))
    service.grade_game("ncaaf:401752", 24, 22)   # exactly on the number
    record = client.get("/api/v1/picks/mine").json()["record"]
    assert record["pushes"] == 1
    assert record["win_rate"] is None


# ─── Community + profile ─────────────────────────────────────────────────────

def test_an_empty_game_reports_no_consensus_rather_than_a_fake_split(client):
    body = client.get("/api/v1/picks/game/nfl/999").json()
    assert body["total_picks"] == 0
    assert body["moneyline_split"] == {}


def test_open_picks_stay_private_until_they_lock(client):
    """Nobody should be able to tail or front-run an unstarted pick."""
    client.post("/api/v1/picks", json=pick_body(market="moneyline", side="home",
                                                selection="Florida State"))
    anon = TestClient(app)
    body = anon.get("/api/v1/picks/game/ncaaf/401752").json()
    assert body["total_picks"] == 1        # the count is public
    assert body["recent_analysis"] == []   # the reasoning is not, yet
    assert body["your_picks"] == []


def test_a_public_analyst_profile_shows_a_verified_record(client):
    client.post("/api/v1/picks", json=pick_body())
    service.grade_game("ncaaf:401752", 21, 23)
    body = TestClient(app).get("/api/v1/analysts/joey").json()
    assert body["profile"]["username"] == "joey"
    assert body["record"]["wins"] == 1
    assert "email" not in body["profile"]


def test_an_unknown_analyst_is_a_404():
    assert TestClient(app).get("/api/v1/analysts/nobody").status_code == 404
