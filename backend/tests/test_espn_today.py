"""ESPN scoreboard parsing + Today auto-predictions with market comparison."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.ingest.espn import Scoreboard, _parse_event

client = TestClient(app)


SAMPLE_EVENT = {
    "id": "401547401",
    "date": "2026-07-04T20:15Z",
    "status": {"type": {"state": "in", "shortDetail": "Q3 5:21"}},
    "competitions": [{
        "competitors": [
            {"homeAway": "home", "score": "21",
             "team": {"displayName": "Kansas City Chiefs", "abbreviation": "KC"}},
            {"homeAway": "away", "score": "17",
             "team": {"displayName": "Buffalo Bills", "abbreviation": "BUF"}},
        ],
        "odds": [{
            "provider": {"name": "ESPN BET"},
            "details": "KC -3.5",
            "spread": -3.5,
            "overUnder": 47.5,
            "homeTeamOdds": {"moneyLine": -180},
            "awayTeamOdds": {"moneyLine": 150},
        }],
    }],
}


def test_parse_event_scores_and_market() -> None:
    g = _parse_event("nfl", SAMPLE_EVENT)
    assert g is not None
    assert g.home_abbr == "KC" and g.away_abbr == "BUF"
    assert g.home_score == 21 and g.away_score == 17
    assert g.state == "in" and g.detail == "Q3 5:21"
    assert g.market_spread == -3.5
    assert g.market_over_under == 47.5
    assert g.market_home_ml == -180 and g.market_away_ml == 150
    assert g.market_provider == "ESPN BET"


def test_parse_event_malformed_returns_none() -> None:
    assert _parse_event("nfl", {"competitions": []}) is None


def _mock_board(league: str = "nfl") -> Scoreboard:
    return Scoreboard(
        league=league,
        games=[_parse_event(league, SAMPLE_EVENT)],
        fetched_at="2026-07-04T20:20:00+00:00",
    )


@pytest.mark.parametrize("bad", ["nhl", "xfl"])
def test_today_unknown_league_404(bad: str) -> None:
    assert client.get(f"/api/v1/today/{bad}").status_code == 404


def _patch_poly(markets=None):
    return patch("src.api.routes.predictions.fetch_league_markets",
                 return_value=markets or [])


def test_today_predicts_slate_and_compares_market() -> None:
    with patch("src.api.routes.predictions.fetch_scoreboard", return_value=_mock_board()), _patch_poly():
        resp = client.get("/api/v1/today/nfl")
    assert resp.status_code == 200
    data = resp.json()
    assert data["league"] == "nfl"
    assert data["market_source"] == "ESPN BET"
    assert len(data["games"]) == 1

    g = data["games"][0]
    assert g["mapped"] is True
    m = g["model"]
    assert abs(m["home_win_prob"] + m["away_win_prob"] - 1.0) < 1e-6
    # Model evaluated AT the market lines
    assert m["total_line"] == 47.5
    # Market comparison covers ML + total + spread (2 sides each)
    markets = {e["market"] for e in g["edges"]}
    assert any("Moneyline" in mk for mk in markets)
    assert any("Total" in mk for mk in markets)
    assert any("Spread" in mk for mk in markets)
    for e in g["edges"]:
        assert e["rating"] in ("A", "B", "C", "-")


def test_today_unmapped_team_included_without_model() -> None:
    ev = {**SAMPLE_EVENT}
    ev["competitions"] = [{
        "competitors": [
            {"homeAway": "home", "score": None,
             "team": {"displayName": "Mystery Team", "abbreviation": "ZZZ"}},
            {"homeAway": "away", "score": None,
             "team": {"displayName": "Buffalo Bills", "abbreviation": "BUF"}},
        ],
    }]
    board = Scoreboard(league="nfl", games=[_parse_event("nfl", ev)], fetched_at="x")
    with patch("src.api.routes.predictions.fetch_scoreboard", return_value=board), _patch_poly():
        data = client.get("/api/v1/today/nfl").json()
    assert data["games"][0]["mapped"] is False
    assert data["games"][0]["model"] is None


def test_today_includes_polymarket_crowd() -> None:
    from src.ingest.polymarket import PolyMarket

    crowd = PolyMarket(
        slug="nfl-kc-buf",
        title="Chiefs vs. Bills",
        outcomes=["Chiefs", "Bills"],
        prices=[0.62, 0.38],
        volume_usd=1_250_000.0,
        url="https://polymarket.com/event/nfl-kc-buf",
    )
    with patch("src.api.routes.predictions.fetch_scoreboard", return_value=_mock_board()), \
         _patch_poly([crowd]):
        data = client.get("/api/v1/today/nfl").json()
    g = data["games"][0]
    pm = g["polymarket"]
    assert pm is not None
    assert abs(pm["home_prob"] - 0.62) < 1e-9      # Chiefs are home in the sample
    assert pm["volume_usd"] == 1_250_000.0
    assert "polymarket.com" in pm["url"]
    assert any("crowd" in e["market"].lower() for e in g["edges"])


def test_live_scores_endpoint_shape() -> None:
    async def fake_all():
        return {"nfl": _mock_board("nfl"), "wc": _mock_board("wc"),
                "cfl": _mock_board("cfl"), "mlb": _mock_board("mlb")}
    with patch("src.api.routes.live.fetch_all_scoreboards", side_effect=fake_all):
        resp = client.get("/api/v1/live/scores")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data["boards"]) >= {"nfl", "wc", "cfl", "mlb"}
    assert data["boards"]["nfl"]["games"][0]["home_abbr"] == "KC"
    assert data["fetched_at"]


def test_is_current_filters_stale_games() -> None:
    """Yesterday's finals must not pollute today's board (the CFL bug)."""
    from datetime import datetime, timezone
    from src.ingest.espn import LiveGame, is_current

    now = datetime(2026, 7, 5, 16, 0, tzinfo=timezone.utc)   # Sat 12:00 ET

    def game(state: str, kickoff: str) -> LiveGame:
        return LiveGame(
            league="cfl", event_id="1", home="A", away="B",
            home_abbr="A", away_abbr="B", home_score=None, away_score=None,
            state=state, detail="", kickoff=kickoff,
        )

    assert is_current(game("post", "2026-07-03T23:00Z"), now) is False   # Thursday final
    assert is_current(game("post", "2026-07-05T17:00Z"), now) is True    # today's final
    assert is_current(game("in", "2026-07-01T00:00Z"), now) is True      # live always shows
    assert is_current(game("pre", "2026-07-06T17:00Z"), now) is True     # tomorrow
    assert is_current(game("pre", "2026-07-08T17:00Z"), now) is False    # 3 days out
    assert is_current(game("pre", ""), now) is True                      # unparseable → keep


def test_today_drops_stale_finals_but_still_grades_them() -> None:
    """A finished game from a previous day is graded, then hidden."""
    from src.track import ledger

    stale_final = {
        **SAMPLE_EVENT,
        "id": "9001",
        "date": "2020-01-02T20:00Z",
        "status": {"type": {"state": "post", "shortDetail": "Final"}},
    }
    ledger.record_pregame(
        event_id="nfl:9001", league="nfl", kickoff="2020-01-02T20:00Z",
        home="Kansas City Chiefs", away="Buffalo Bills",
        model_home_prob=0.7,
    )
    board = Scoreboard(league="nfl",
                       games=[_parse_event("nfl", stale_final)], fetched_at="x")
    with patch("src.api.routes.predictions.fetch_scoreboard", return_value=board), _patch_poly():
        data = client.get("/api/v1/today/nfl").json()
    assert data["games"] == []                                  # hidden from the slate
    assert ledger.accuracy_summary()["overall"]["games_graded"] == 1   # but settled


def test_cfl_predict_endpoint() -> None:
    resp = client.post("/api/v1/predict/cfl", json={
        "home": "SSK", "away": "TOR", "apply_weather": False,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["home_win_prob"] > 0.5          # SSK clearly stronger
    assert 40 < data["total_points_estimate"] < 62   # CFL scoring environment


def test_mlb_predict_endpoint_with_qb_analog() -> None:
    resp = client.post("/api/v1/predict/mlb", json={
        "home": "PIT", "away": "CHC", "apply_weather": False,
        "missing_home": ["P. Skenes"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert any("Skenes" in c["label"] for c in data["conditions"])
    assert data["home_win_prob"] < data["base_home_win_prob"]
