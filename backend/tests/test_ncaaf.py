"""NCAA college football: market-first model, live situation, play-by-play."""
from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.main import app
from src.data.ncaaf import get_ncaaf_ratings, get_ncaaf_team
from src.ingest.espn import Scoreboard, _parse_event, _parse_plays, fetch_playbyplay, GameFeed
from src.predict.gridiron import LEAGUE_PARAMS

client = TestClient(app)


# ── A live college game with betting lines + an in-game situation ──
CFB_EVENT = {
    "id": "401752" ,
    "date": "2025-09-06T23:30Z",
    "status": {"type": {"state": "in", "shortDetail": "Q3 05:12"},
               "period": 3, "displayClock": "05:12"},
    "competitions": [{
        "situation": {
            "down": 1, "distance": 10, "possession": "194",
            "downDistanceText": "1st & 10", "possessionText": "OSU 42",
            "isRedZone": False,
            "lastPlay": {"text": "Henderson rush for 6 yards to the OSU 42"},
        },
        "competitors": [
            {"homeAway": "home", "score": "24",
             "team": {"id": "194", "displayName": "Ohio State Buckeyes",
                      "abbreviation": "OSU", "logo": "https://logo/osu.png"}},
            {"homeAway": "away", "score": "10",
             "team": {"id": "2483", "displayName": "Marshall Thundering Herd",
                      "abbreviation": "MRSH", "logo": "https://logo/mrsh.png"}},
        ],
        "odds": [{
            "provider": {"name": "ESPN BET"},
            "details": "OSU -38.5", "spread": -38.5, "overUnder": 59.5,
            "homeTeamOdds": {"moneyLine": -20000},
            "awayTeamOdds": {"moneyLine": 5000},
        }],
    }],
}


def _patch_poly():
    return patch("src.api.routes.predictions.fetch_league_markets", return_value=[])


def test_unknown_team_never_raises_and_leans_neutral() -> None:
    t = get_ncaaf_team("ZZZ")            # not in the seed set
    assert t.elo == 1475.0
    off, dfn = get_ncaaf_ratings("ZZZ")
    assert 20 < off < 35 and 20 < dfn < 35


def test_college_has_wider_distributions_than_nfl() -> None:
    assert LEAGUE_PARAMS["ncaaf"]["margin_sigma"] > LEAGUE_PARAMS["nfl"]["margin_sigma"]
    assert LEAGUE_PARAMS["ncaaf"]["total_sigma"] > LEAGUE_PARAMS["nfl"]["total_sigma"]


def test_parse_event_reads_live_situation() -> None:
    g = _parse_event("ncaaf", CFB_EVENT)
    assert g is not None
    assert g.home_abbr == "OSU" and g.away_abbr == "MRSH"
    assert g.period == 3 and g.clock == "05:12"
    assert g.possession_abbr == "OSU"                  # id 194 → home
    assert "1st & 10" in g.down_distance and "OSU 42" in g.down_distance
    assert "Henderson" in g.last_play
    assert g.market_spread == -38.5 and g.market_over_under == 59.5
    assert g.home_logo.endswith("osu.png")


def test_predict_ncaaf_endpoint_known_teams() -> None:
    resp = client.post("/api/v1/predict/ncaaf", json={
        "home": "OSU", "away": "HAW", "apply_weather": False,
    })
    assert resp.status_code == 200
    d = resp.json()
    assert d["home_win_prob"] > 0.85                   # huge mismatch
    assert 45 < d["total_points_estimate"] < 95


def test_predict_ncaaf_unknown_team_maps_without_404() -> None:
    resp = client.post("/api/v1/predict/ncaaf", json={
        "home": "ZZZ", "away": "QQQ", "apply_weather": False,
    })
    assert resp.status_code == 200                     # never 404s on unknowns
    d = resp.json()
    assert 0.4 < d["home_win_prob"] < 0.65             # ~coin flip + home edge


def test_today_ncaaf_projects_market_anchored_score() -> None:
    board = Scoreboard(league="ncaaf", games=[_parse_event("ncaaf", CFB_EVENT)], fetched_at="x")
    with patch("src.api.routes.predictions.fetch_scoreboard", return_value=board), _patch_poly():
        data = client.get("/api/v1/today/ncaaf").json()
    g = data["games"][0]
    assert g["mapped"] is True
    m = g["model"]
    # Heavy home favourite → calibrated prob stays very high, projected score
    # blends toward the market (home well ahead, total near the 59.5 line).
    assert m["calibrated_home_win"] > 0.9
    assert m["proj_home_score"] > m["proj_away_score"]
    assert 40 < (m["proj_home_score"] + m["proj_away_score"]) < 80


def test_parse_plays_newest_first() -> None:
    summary = {
        "drives": {
            "previous": [
                {"team": {"abbreviation": "MRSH"}, "plays": [
                    {"period": {"number": 1}, "clock": {"displayValue": "12:00"},
                     "text": "Kickoff", "homeScore": 0, "awayScore": 0},
                    {"period": {"number": 1}, "clock": {"displayValue": "10:30"},
                     "text": "TD pass", "scoringPlay": True, "homeScore": 0, "awayScore": 7},
                ]},
            ],
            "current": {"team": {"abbreviation": "OSU"}, "plays": [
                {"period": {"number": 3}, "clock": {"displayValue": "05:12"},
                 "text": "Henderson rush for 6", "homeScore": 24, "awayScore": 10},
            ]},
        }
    }
    plays = _parse_plays(summary)
    assert plays[0].text == "Henderson rush for 6"      # newest first
    assert plays[0].team_abbr == "OSU"
    assert any(p.scoring for p in plays)


def test_play_by_play_endpoint() -> None:
    feed = GameFeed(league="ncaaf", event_id="401752", ok=True,
                    plays=_parse_plays({"drives": {"previous": [
                        {"team": {"abbreviation": "OSU"}, "plays": [
                            {"period": {"number": 3}, "clock": {"displayValue": "05:12"},
                             "text": "Henderson rush", "homeScore": 24, "awayScore": 10}]}]}}),
                    fetched_at="x")

    async def fake_feed(league, event_id, limit=40):
        return feed
    with patch("src.api.routes.live.fetch_playbyplay", side_effect=fake_feed):
        resp = client.get("/api/v1/live/pbp/ncaaf/401752")
    assert resp.status_code == 200
    d = resp.json()
    assert d["plays"][0]["text"] == "Henderson rush"
    assert d["plays"][0]["home_score"] == 24


def test_fetch_playbyplay_bad_league() -> None:
    import asyncio
    feed = asyncio.get_event_loop().run_until_complete(fetch_playbyplay("nhl", "1"))
    assert feed.ok is False
