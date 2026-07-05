"""Live-conditions engine tests — weather and lineup adjustments."""
from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.main import app
from src.data import lineups
from src.ingest.weather import WeatherReport
from src.predict.adjustments import (
    nfl_weather_adjustments,
    soccer_lineup_adjustments,
    soccer_weather_adjustments,
)
from src.predict.soccer import predict_match

client = TestClient(app)


def _weather(**kw) -> WeatherReport:
    defaults = dict(
        venue="Test Stadium", temperature_c=20.0, temperature_f=68.0,
        precipitation_prob=0, wind_speed_kmh=5.0, condition="Clear",
        wmo_code=0, is_indoor=False,
    )
    defaults.update(kw)
    return WeatherReport(**defaults)


# ─── Weather → soccer ─────────────────────────────────────────────────────────

def test_calm_weather_no_adjustments() -> None:
    assert soccer_weather_adjustments(_weather()) == []


def test_indoor_venue_ignores_weather() -> None:
    w = _weather(wind_speed_kmh=50, precipitation_prob=90, is_indoor=True)
    assert soccer_weather_adjustments(w) == []


def test_high_wind_reduces_both_xg() -> None:
    adj = soccer_weather_adjustments(_weather(wind_speed_kmh=35))
    assert len(adj) == 1
    assert adj[0].home_xg_mult < 1.0
    assert adj[0].away_xg_mult < 1.0


def test_heavy_rain_bigger_cut_than_drizzle() -> None:
    heavy = soccer_weather_adjustments(_weather(wmo_code=65, condition="Heavy rain"))
    light = soccer_weather_adjustments(_weather(wmo_code=61, condition="Light rain"))
    assert heavy[0].home_xg_mult < light[0].home_xg_mult


def test_weather_lowers_over_probability() -> None:
    """The point of live weather: totals must actually move."""
    base = predict_match("FRA", "ENG", 2004, 1975)
    stormy = predict_match(
        "FRA", "ENG", 2004, 1975,
        adjustments=soccer_weather_adjustments(
            _weather(wind_speed_kmh=35, wmo_code=65, condition="Heavy rain"),
        ),
    )
    assert stormy.totals.over_2_5 < base.totals.over_2_5 - 0.03
    assert stormy.model_probs.home_xg < base.model_probs.home_xg


# ─── Weather → NFL ────────────────────────────────────────────────────────────

def test_nfl_wind_cuts_total() -> None:
    adj = nfl_weather_adjustments(_weather(wind_speed_kmh=40))   # ~25 mph
    assert len(adj) == 1
    assert adj[0].home_pts_delta < 0
    assert adj[0].away_pts_delta < 0


def test_nfl_dome_no_weather() -> None:
    assert nfl_weather_adjustments(_weather(wind_speed_kmh=60, is_indoor=True)) == []


# ─── Lineups ──────────────────────────────────────────────────────────────────

def test_striker_out_cuts_own_xg() -> None:
    adj = soccer_lineup_adjustments("ARG", "CPV", ["L. Messi"], [])
    assert len(adj) == 1
    assert adj[0].home_xg_mult < 1.0
    assert adj[0].away_xg_mult == 1.0     # a striker doesn't help the opponent score


def test_defender_out_raises_opponent_xg() -> None:
    adj = soccer_lineup_adjustments("NED", "ESP", ["V. van Dijk"], [])
    assert adj[0].home_xg_mult == 1.0
    assert adj[0].away_xg_mult > 1.0


def test_store_status_flows_into_adjustments() -> None:
    lineups.set_status("soccer", "ESP", "Rodri", "out")
    try:
        adj = soccer_lineup_adjustments("ESP", "TUR")
        assert any("Rodri" in a.label for a in adj)
    finally:
        lineups.reset_team("soccer", "ESP")
    assert soccer_lineup_adjustments("ESP", "TUR") == []


def test_doubtful_is_half_impact() -> None:
    lineups.set_status("soccer", "ARG", "L. Messi", "out")
    full = soccer_lineup_adjustments("ARG", "CPV")[0].home_xg_mult
    lineups.set_status("soccer", "ARG", "L. Messi", "doubtful")
    half = soccer_lineup_adjustments("ARG", "CPV")[0].home_xg_mult
    lineups.reset_team("soccer", "ARG")
    assert (1 - full) > (1 - half) > 0
    assert abs((1 - full) / 2 - (1 - half)) < 1e-9


# ─── Lineup API endpoints ─────────────────────────────────────────────────────

def test_lineup_get_endpoint() -> None:
    resp = client.get("/api/v1/lineups/soccer/ARG")
    assert resp.status_code == 200
    players = resp.json()
    assert any(p["name"] == "L. Messi" for p in players)
    assert all(p["status"] == "fit" for p in players)


def test_lineup_set_and_reset() -> None:
    resp = client.post(
        "/api/v1/lineups/nfl/KC",
        json={"player": "P. Mahomes", "status": "out"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "out"

    # Prediction reflects it immediately
    pred = client.post(
        "/api/v1/predict/nfl",
        json={"home": "KC", "away": "SF", "apply_weather": False},
    ).json()
    assert any("Mahomes" in c["label"] for c in pred["conditions"])
    assert pred["home_win_prob"] < pred["base_home_win_prob"]

    resp = client.delete("/api/v1/lineups/nfl/KC")
    assert resp.status_code == 200
    pred2 = client.post(
        "/api/v1/predict/nfl",
        json={"home": "KC", "away": "SF", "apply_weather": False},
    ).json()
    assert pred2["conditions"] == []


def test_lineup_unknown_player_404() -> None:
    resp = client.post(
        "/api/v1/lineups/soccer/ARG",
        json={"player": "Nobody Real", "status": "out"},
    )
    assert resp.status_code == 404


def test_lineup_invalid_status_422() -> None:
    resp = client.post(
        "/api/v1/lineups/soccer/ARG",
        json={"player": "L. Messi", "status": "injured-ish"},
    )
    assert resp.status_code == 422


# ─── Request-level what-if + market odds ──────────────────────────────────────

def test_soccer_predict_missing_player_and_odds() -> None:
    resp = client.post("/api/v1/predict/soccer", json={
        "home": "ARG", "away": "CPV",
        "apply_weather": False,
        "missing_home": ["L. Messi"],
        "odds": {"format": "decimal", "home": 1.30, "draw": 5.50, "away": 9.00},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert any("Messi" in c["label"] for c in data["conditions"])
    # Baseline shows what the number was before conditions
    assert data["base_probs"]["home_win"] > data["model_probs"]["home_win"]
    # Edges computed with ratings
    assert len(data["edges"]) == 3
    assert all(e["rating"] in ("A", "B", "C", "-") for e in data["edges"])
    assert "over_by_line" in data["totals"]
    assert data["fair_odds"]["home"] >= 1.0


def test_best_bets_endpoint() -> None:
    from unittest.mock import patch
    from src.ingest.espn import Scoreboard

    empty = Scoreboard(league="none", games=[], fetched_at="x", ok=False)
    with patch("src.api.routes.predictions.fetch_scoreboard", return_value=empty), \
         patch("src.api.routes.predictions.fetch_league_markets", return_value=[]):
        resp = client.get("/api/v1/best-bets")
    assert resp.status_code == 200
    data = resp.json()
    assert "bets" in data
    for b in data["bets"]:
        assert b["rating"] in ("A", "B", "C")
        assert 0 <= b["model_prob"] <= 1
