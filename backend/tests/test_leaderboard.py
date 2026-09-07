"""Edge Rating and leaderboard ranking, including the sample-size guard."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.picks import leaderboard, service
from src.store import documents


def iso(hours: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat(timespec="seconds")


@pytest.fixture(autouse=True)
def clean_store(tmp_path, monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("LEDGER_PATH", str(tmp_path / "lb.db"))
    documents.reset_docs()
    yield
    documents.reset_docs()


def make_analyst(username: str) -> TestClient:
    c = TestClient(app)
    c.post("/api/v1/auth/register", json={
        "username": username, "email": f"{username}@example.com",
        "password": "a-strong-passphrase"})
    return c


def publish_and_grade(client: TestClient, event_id: str, win: bool) -> None:
    client.post("/api/v1/picks", json={
        "league": "ncaaf", "event_id": event_id, "home": "A", "away": "B",
        "kickoff": iso(2), "market": "moneyline", "side": "home",
        "selection": "A", "price_american": -110, "confidence": 65,
    })
    service.grade_game(f"ncaaf:{event_id}", *(27, 24) if win else (24, 27))


# ─── Edge Rating ─────────────────────────────────────────────────────────────

def test_no_history_scores_neutral():
    assert leaderboard.rate(units=0.0, graded=0) == leaderboard.BASELINE


def test_profit_raises_the_rating_and_losses_lower_it():
    assert leaderboard.rate(units=10.0, graded=30) > leaderboard.BASELINE
    assert leaderboard.rate(units=-10.0, graded=30) < leaderboard.BASELINE


def test_a_small_sample_moves_the_rating_less_than_a_large_one():
    """A hot start should register without owning the rating."""
    hot_start = leaderboard.rate(units=3.0, graded=3)
    established = leaderboard.rate(units=30.0, graded=30)   # same ROI per pick
    assert established > hot_start


def test_the_rating_is_bounded():
    assert 0.0 <= leaderboard.rate(units=-999.0, graded=50) <= 100.0
    assert 0.0 <= leaderboard.rate(units=999.0, graded=50) <= 100.0


# ─── Ranking ─────────────────────────────────────────────────────────────────

def test_an_analyst_with_no_graded_picks_is_absent():
    c = make_analyst("newcomer")
    c.post("/api/v1/picks", json={
        "league": "ncaaf", "event_id": "1", "home": "A", "away": "B",
        "kickoff": iso(3), "market": "moneyline", "side": "home",
        "selection": "A", "confidence": 60})
    assert leaderboard.standings() == []


def test_a_short_record_is_marked_provisional():
    publish_and_grade(make_analyst("rookie"), "1", win=True)
    [standing] = leaderboard.standings()
    assert standing.provisional is True
    assert standing.graded == 1


def test_provisional_analysts_rank_below_established_ones():
    """5-0 must not outrank a proven record."""
    rookie = make_analyst("rookie")
    publish_and_grade(rookie, "1", win=True)

    veteran = make_analyst("veteran")
    for i in range(leaderboard.MIN_GRADED + 2):
        publish_and_grade(veteran, f"v{i}", win=i % 3 != 0)   # a winning record

    table = leaderboard.standings()
    assert table[0].username == "veteran"
    assert table[0].provisional is False
    assert table[-1].username == "rookie"


def test_the_endpoint_reports_only_real_analysts():
    publish_and_grade(make_analyst("solo"), "1", win=True)
    body = TestClient(app).get("/api/v1/leaderboard").json()
    assert body["count"] == 1
    assert body["standings"][0]["username"] == "solo"
    assert body["min_graded"] == leaderboard.MIN_GRADED


def test_an_empty_leaderboard_is_empty_rather_than_invented():
    body = TestClient(app).get("/api/v1/leaderboard").json()
    assert body["count"] == 0
    assert body["standings"] == []


def test_a_private_profile_is_left_out_of_the_table():
    private = make_analyst("hidden")
    publish_and_grade(private, "1", win=True)
    private.patch("/api/v1/auth/profile", json={"profile_public": False})
    assert leaderboard.standings() == []


def test_the_league_filter_narrows_the_table():
    publish_and_grade(make_analyst("cfbonly"), "1", win=True)
    assert len(leaderboard.standings("ncaaf")) == 1
    assert leaderboard.standings("nfl") == []


def test_a_profile_carries_its_leaderboard_position():
    publish_and_grade(make_analyst("ranked"), "1", win=True)
    body = TestClient(app).get("/api/v1/analysts/ranked").json()
    assert body["standing"]["rank"] == 1
    assert body["standing"]["provisional"] is True


def test_followers_are_not_part_of_the_rating():
    """Popularity and predictive skill are different things."""
    import inspect
    source = inspect.getsource(leaderboard.rate)
    assert "follow" not in source.lower()
