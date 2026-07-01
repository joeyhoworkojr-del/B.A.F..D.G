"""API integration tests using FastAPI test client."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "database_reachable" in data


def test_list_soccer_teams() -> None:
    resp = client.get("/api/v1/teams/soccer")
    assert resp.status_code == 200
    teams = resp.json()
    assert len(teams) >= 48
    codes = {t["code"] for t in teams}
    assert "ARG" in codes
    assert "MEX" in codes


def test_list_nfl_teams() -> None:
    resp = client.get("/api/v1/teams/nfl")
    assert resp.status_code == 200
    teams = resp.json()
    assert len(teams) == 32
    codes = {t["code"] for t in teams}
    assert "KC" in codes
    assert "SF" in codes


def test_soccer_predict_arg_cpv() -> None:
    resp = client.post("/api/v1/predict/soccer", json={"home": "ARG", "away": "CPV"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["home_team"]["code"] == "ARG"
    assert data["away_team"]["code"] == "CPV"
    # Argentina should be clear favourite (>50%) but soccer keeps upsets real
    assert data["blended_probs"]["home_win"] > 0.50
    assert data["blended_probs"]["home_win"] > data["blended_probs"]["away_win"]
    # Probabilities sum to 1
    total = (
        data["blended_probs"]["home_win"]
        + data["blended_probs"]["draw"]
        + data["blended_probs"]["away_win"]
    )
    assert abs(total - 1.0) < 0.01
    # Simulation present and ARG leads
    assert "simulation" in data
    assert data["simulation"]["home_wins"] > data["simulation"]["away_wins"]


def test_soccer_predict_close_game_fra_eng() -> None:
    resp = client.post("/api/v1/predict/soccer", json={"home": "FRA", "away": "ENG"})
    assert resp.status_code == 200
    data = resp.json()
    hw = data["blended_probs"]["home_win"]
    aw = data["blended_probs"]["away_win"]
    # FRA vs ENG is genuinely close; neither should be above 60%
    assert hw < 0.65
    assert aw < 0.65


def test_soccer_predict_mex_ecu_has_player_props() -> None:
    resp = client.post(
        "/api/v1/predict/soccer",
        json={"home": "MEX", "away": "ECU", "neutral": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    props = data["player_props"]
    assert len(props) > 0
    # All props between 0 and 1
    for p in props:
        assert 0 < p["anytime_scorer"] < 1
        assert p["two_plus_goals"] < p["anytime_scorer"]


def test_soccer_predict_knockout_advance_probs() -> None:
    resp = client.post(
        "/api/v1/predict/soccer",
        json={"home": "BRA", "away": "COL", "knockout": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    sim = data["simulation"]
    assert abs(sim["home_advance"] + sim["away_advance"] - 1.0) < 0.02


def test_soccer_predict_unknown_team_404() -> None:
    resp = client.post("/api/v1/predict/soccer", json={"home": "XXX", "away": "ARG"})
    assert resp.status_code == 404


def test_nfl_predict_kc_sf() -> None:
    resp = client.post("/api/v1/predict/nfl", json={"home": "KC", "away": "SF"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["home_team"]["code"] == "KC"
    total = data["home_win_prob"] + data["away_win_prob"]
    assert abs(total - 1.0) < 0.001
    assert 40 < data["total_points_estimate"] < 60


def test_nfl_predict_unknown_team_404() -> None:
    resp = client.post("/api/v1/predict/nfl", json={"home": "ZZZ", "away": "KC"})
    assert resp.status_code == 404


def test_soccer_rankings_sorted_by_elo() -> None:
    resp = client.get("/api/v1/rankings/soccer")
    assert resp.status_code == 200
    data = resp.json()
    elos = [t["elo"] for t in data["teams"]]
    assert elos == sorted(elos, reverse=True)
    assert data["teams"][0]["code"] == "ARG"   # highest Elo


def test_nfl_rankings_sorted_by_elo() -> None:
    resp = client.get("/api/v1/rankings/nfl")
    assert resp.status_code == 200
    elos = [t["elo"] for t in resp.json()["teams"]]
    assert elos == sorted(elos, reverse=True)


def test_r16_fixtures_endpoint() -> None:
    resp = client.get("/api/v1/fixtures/r16")
    assert resp.status_code == 200
    fixtures = resp.json()
    assert len(fixtures) >= 8
    for f in fixtures:
        assert "home" in f
        assert "away" in f
        assert "venue" in f
