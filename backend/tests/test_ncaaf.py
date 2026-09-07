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


def test_parse_plays_falls_back_to_flat_array() -> None:
    # Some live college summaries only populate a flat top-level `plays` list.
    summary = {
        "drives": {},
        "plays": [
            {"period": {"number": 2}, "clock": {"displayValue": "08:20"}, "text": "Run for 4"},
            {"period": {"number": 2}, "clock": {"displayValue": "07:55"}, "text": "TD run",
             "scoringPlay": True, "homeScore": 14, "awayScore": 7},
        ],
    }
    plays = _parse_plays(summary)
    assert plays[0].text == "TD run" and plays[0].scoring is True   # newest first
    assert len(plays) == 2


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


def test_live_projection_converges_with_the_clock() -> None:
    from src.predict.gridiron import live_projection

    # Home up 24-10 in Q3 with time left → strong but not certain.
    mid = live_projection(
        league="ncaaf", home_score=24, away_score=10, period=3, clock_seconds=312,
        pregame_margin=3.0, total_estimate=55.0, home_share=0.55,
    )
    assert 0.80 < mid["home_win"] < 0.99
    assert mid["proj_home"] > mid["proj_away"]
    assert 0 < mid["time_remaining_pct"] < 50

    # Same lead with seconds left → essentially decided.
    late = live_projection(
        league="ncaaf", home_score=24, away_score=10, period=4, clock_seconds=20,
        pregame_margin=3.0, total_estimate=55.0, home_share=0.55,
    )
    assert late["home_win"] > mid["home_win"]
    assert late["home_win"] > 0.98

    # Trailing team's live win prob is below its pre-game prior.
    behind = live_projection(
        league="nfl", home_score=7, away_score=21, period=3, clock_seconds=200,
        pregame_margin=2.0, total_estimate=45.0, home_share=0.5,
    )
    assert behind["home_win"] < 0.35


def test_today_surfaces_live_win_probability() -> None:
    board = Scoreboard(league="ncaaf", games=[_parse_event("ncaaf", CFB_EVENT)], fetched_at="x")
    with patch("src.api.routes.predictions.fetch_scoreboard", return_value=board), _patch_poly():
        data = client.get("/api/v1/today/ncaaf").json()
    m = data["games"][0]["model"]
    assert m["live"] is True                       # CFB_EVENT is in-progress
    # OSU (home) lead 24-10 in Q3 → live prob well ahead of a coin flip.
    assert m["live_home_win"] > 0.80
    assert m["live_proj_home"] >= 24 and m["live_proj_away"] >= 10
    assert 0 < m["time_remaining_pct"] < 60


def test_fetch_playbyplay_bad_league() -> None:
    import asyncio
    feed = asyncio.get_event_loop().run_until_complete(fetch_playbyplay("nhl", "1"))
    assert feed.ok is False


def _pre_event(eid: str, home_abbr: str, away_abbr: str, spread: float, ou: float) -> dict:
    return {
        "id": eid, "date": "2025-09-06T23:30Z",
        "status": {"type": {"state": "pre", "shortDetail": "Sat 7:30 PM"}},
        "competitions": [{
            "competitors": [
                {"homeAway": "home", "score": None,
                 "team": {"id": "1", "displayName": home_abbr, "abbreviation": home_abbr}},
                {"homeAway": "away", "score": None,
                 "team": {"id": "2", "displayName": away_abbr, "abbreviation": away_abbr}},
            ],
            "odds": [{"provider": {"name": "ESPN BET"}, "spread": spread, "overUnder": ou,
                      "homeTeamOdds": {"moneyLine": -110}, "awayTeamOdds": {"moneyLine": -110}}],
        }],
    }


def test_best_parlay_combines_multiple_legs() -> None:
    # Two strong home favourites with totals → each yields a value leg.
    games = [
        _parse_event("ncaaf", _pre_event("g1", "OSU", "HAW", -38.5, 59.5)),
        _parse_event("ncaaf", _pre_event("g2", "GA", "UNM", -35.0, 55.5)),
    ]
    board = Scoreboard(league="ncaaf", games=games, fetched_at="x")

    async def one_board(league):
        return board if league == "ncaaf" else Scoreboard(league=league, games=[], fetched_at="x")

    with patch("src.api.routes.predictions.fetch_scoreboard", side_effect=one_board), \
         patch("src.api.routes.predictions.fetch_league_markets", return_value=[]):
        d = client.get("/api/v1/best-parlay?max_legs=3").json()

    assert d["leg_count"] >= 2
    # Combined odds/prob are the product of the legs — longer than any single leg.
    assert d["decimal_odds"] > 1.0
    assert 0 < d["model_prob"] < 1
    assert d["american_odds"] != 0
    assert len(d["legs"]) == d["leg_count"]
    # Each leg is a favourite the model likes (>=50%).
    assert all(leg["model_prob"] >= 0.5 for leg in d["legs"])
