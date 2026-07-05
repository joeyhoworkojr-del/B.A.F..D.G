"""High-altitude home advantage for soccer (Estadio Azteca etc.)."""
from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.main import app
from src.predict.adjustments import soccer_altitude_adjustments

client = TestClient(app)

AZTECA = "Estadio Azteca, CDMX"


def test_acclimatized_side_gains_at_altitude() -> None:
    adj = soccer_altitude_adjustments(AZTECA, "MEX", "FRA", "Mexico", "France")
    assert len(adj) == 1
    a = adj[0]
    assert a.source == "altitude"
    assert a.home_xg_mult > 1.0      # Mexico (acclimatized) boosted
    assert a.away_xg_mult < 1.0      # France (sea level) suppressed
    assert "2,240" in a.label


def test_two_altitude_nations_cancel() -> None:
    # Mexico (2,240 m) vs Ecuador (Quito, 2,850 m): both used to thin air,
    # so there is no differential altitude effect — only the host edge (elsewhere).
    assert soccer_altitude_adjustments(AZTECA, "MEX", "ECU") == []


def test_sea_level_venue_has_no_altitude_effect() -> None:
    assert soccer_altitude_adjustments("MetLife Stadium, NJ", "MEX", "FRA") == []


def test_two_lowland_sides_both_suppressed() -> None:
    adj = soccer_altitude_adjustments(AZTECA, "SUI", "DZA")
    assert len(adj) == 1
    assert adj[0].home_xg_mult < 1.0 and adj[0].away_xg_mult < 1.0


def test_high_altitude_visitor_not_penalized() -> None:
    # Bolivia (La Paz, 3,640 m) visiting Azteca is fully acclimatized.
    adj = soccer_altitude_adjustments(AZTECA, "MEX", "BOL")
    assert adj == []


def test_predict_endpoint_applies_altitude_condition() -> None:
    with patch("src.api.routes.predictions.fetch_weather", return_value=None):
        resp = client.post("/api/v1/predict/soccer", json={
            "home": "MEX", "away": "FRA", "neutral": True,
            "venue": AZTECA, "apply_weather": True, "apply_lineups": False,
        })
    assert resp.status_code == 200
    data = resp.json()
    assert any(c["source"] == "altitude" for c in data["conditions"])
    # Altitude lifts Mexico's number vs the pre-conditions baseline.
    assert data["model_probs"]["home_win"] > data["base_probs"]["home_win"]


def test_norway_is_selectable_and_haaland_resolves() -> None:
    resp = client.post("/api/v1/predict/soccer", json={
        "home": "NOR", "away": "BRA", "apply_weather": False, "apply_lineups": False,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["home_team"]["name"] == "Norway"
    assert any(p["name"] == "E. Haaland" for p in data["player_props"])
