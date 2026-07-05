"""Self-correcting Elo ratings — updates from graded results and feeds back."""
from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.main import app
from src.track import ledger, ratings

client = TestClient(app)


def test_underdog_win_raises_its_rating() -> None:
    # Away side (1500) upsets the home favourite (1700) → away rating up, home down.
    change = ratings.record_result("nfl", "AAA", "BBB", 1700, 1500, 10, 27)
    assert change < 0                              # home lost ground
    assert ratings.get_delta("nfl", "AAA") < 0
    assert ratings.get_delta("nfl", "BBB") > 0
    # Symmetric, zero-sum swing
    assert abs(ratings.get_delta("nfl", "AAA") + ratings.get_delta("nfl", "BBB")) < 1e-9


def test_expected_result_barely_moves_rating() -> None:
    # Big favourite wins by a little → small change.
    small = ratings.record_result("nfl", "AAA", "BBB", 1900, 1500, 21, 20)
    # Upset by the same margin moves it far more.
    ratings.reset()
    big = abs(ratings.record_result("nfl", "AAA", "BBB", 1500, 1900, 21, 20))
    assert big > abs(small)


def test_delta_is_capped() -> None:
    for _ in range(200):
        ratings.record_result("mlb", "AAA", "BBB", 1500, 1900, 20, 0)
    assert ratings.get_delta("mlb", "AAA") <= ratings.DELTA_CAP + 1e-9


def test_tie_does_not_move_ratings() -> None:
    assert ratings.record_result("nfl", "AAA", "BBB", 1600, 1600, 17, 17) == 0.0
    assert ratings.get_delta("nfl", "AAA") == 0.0


def test_adjust_applies_delta() -> None:
    ratings.record_result("nfl", "KC", "DEN", 1500, 1700, 30, 10)  # KC big upset win
    assert ratings.adjust("nfl", "KC", 1600) > 1600


def test_reconcile_folds_graded_games_once() -> None:
    ledger.record_pregame(
        event_id="nfl:500", league="nfl", kickoff="2026-01-01T00:00Z",
        home="Chiefs", away="Broncos", model_home_prob=0.6,
        home_code="KC", away_code="DEN", home_elo=1600, away_elo=1550,
    )
    ledger.grade("nfl:500", 34, 10)          # Chiefs win big
    assert ratings.reconcile() == 1          # applied
    assert ratings.reconcile() == 0          # idempotent — not applied twice
    assert ratings.get_delta("nfl", "KC") > 0
    assert ratings.get_delta("nfl", "DEN") < 0


def test_ratings_form_endpoint() -> None:
    ratings.record_result("cfl", "SSK", "TOR", 1500, 1660, 40, 12)
    resp = client.get("/api/v1/ratings/cfl/form")
    assert resp.status_code == 200
    data = resp.json()
    assert data["league"] == "cfl"
    codes = {t["code"] for t in data["teams"]}
    assert "SSK" in codes


def test_predictions_use_learned_rating() -> None:
    """After a team is boosted, its predicted win probability rises."""
    base = client.post("/api/v1/predict/nfl", json={
        "home": "KC", "away": "DEN", "apply_weather": False, "apply_lineups": False,
    }).json()["home_win_prob"]

    # Teach the model KC is on a heater.
    for _ in range(6):
        ratings.record_result("nfl", "KC", "DEN", 1600, 1600, 35, 10)

    after = client.post("/api/v1/predict/nfl", json={
        "home": "KC", "away": "DEN", "apply_weather": False, "apply_lineups": False,
    }).json()["home_win_prob"]
    assert after > base
