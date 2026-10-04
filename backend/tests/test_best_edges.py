"""
The Best Edges scan.

Two things make this page worth having rather than another list of picks.

It ranks by expected value, not by probability. A 90% favourite priced at 92%
is a worse bet than a 55% call at even money; ranking by probability puts the
bad one on top, which is how a tipping site ends up recommending heavy
favourites all season and calling the hit rate a track record.

And it is built from the board the homepage already has, so the two cannot
show different numbers for the same game.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes import predictions as pred
from src.ingest.espn import LiveGame, Scoreboard
from src.predict import priors

client = TestClient(app)


def game(event_id, league="nfl", *, home, away, home_abbr, away_abbr,
         hours=20, spread=None, total=None, home_ml=None, away_ml=None,
         state="pre"):
    return LiveGame(
        league=league, event_id=str(event_id), home=home, away=away,
        home_abbr=home_abbr, away_abbr=away_abbr,
        home_score=None, away_score=None, state=state, detail="",
        kickoff=(datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat(),
        market_spread=spread, market_over_under=total,
        market_home_ml=home_ml, market_away_ml=away_ml,
        market_provider="ESPN BET",
    )


def board_of(nfl=(), ncaaf=()):
    async def scoreboard(league):
        return Scoreboard(league=league, games=[], fetched_at="now", ok=True)

    async def upcoming(league, days=7):
        return Scoreboard(league=league, games=list(nfl if league == "nfl" else ncaaf),
                          fetched_at="now", ok=True)

    async def markets(league):
        return []

    return patch.multiple(pred, fetch_scoreboard=scoreboard,
                          fetch_upcoming=upcoming, fetch_league_markets=markets)


@pytest.fixture(autouse=True)
def seeded_priors():
    priors._priors["nfl"] = priors.LeaguePriors(
        league="nfl", ok=True, source="nflverse-epa", fetched_at="now",
        teams={
            c: priors.TeamPrior(code=c, points=p, games=5, source="nflverse-epa")
            for c, p in (("BUF", 6.1), ("MIA", -2.3), ("KC", 5.0),
                         ("NE", -4.0), ("SF", 4.2), ("DAL", 1.0))
        },
    )
    yield
    priors.reset()


BUF = dict(home="Buffalo Bills", away="Miami Dolphins",
           home_abbr="BUF", away_abbr="MIA")
DAL = dict(home="Dallas Cowboys", away="San Francisco 49ers",
           home_abbr="DAL", away_abbr="SF")


def fetch(**params):
    q = "&".join(f"{k}={v}" for k, v in params.items())
    return client.get(f"/api/v1/edges?{q}" if q else "/api/v1/edges").json()


def test_it_ranks_by_expected_value_not_by_probability():
    games = [
        game(1, **BUF, spread=-3.5, total=46.5, home_ml=-175, away_ml=150),
        game(2, **DAL, spread=1.5, total=44.0, home_ml=105, away_ml=-125),
    ]
    with board_of(nfl=games):
        body = fetch(limit=20)

    evs = [e["ev_per_unit"] for e in body["edges"]]
    assert evs == sorted(evs, reverse=True), evs
    # And a high-probability row is not automatically above a high-EV one.
    probs = [e["model_prob"] for e in body["edges"]]
    assert probs != sorted(probs, reverse=True) or len(probs) < 2


def test_every_row_keeps_probability_break_even_ev_and_confidence_apart():
    with board_of(nfl=[game(1, **BUF, spread=-3.5, total=46.5,
                            home_ml=-175, away_ml=150)]):
        body = fetch()

    assert body["edges"], "a priced game should produce rows"
    for e in body["edges"]:
        assert e["model_prob"] is not None
        assert e["break_even_prob"] is not None
        assert e["ev_per_unit"] is not None
        assert e["confidence"] in ("low", "medium", "high")
    assert "not by how likely" in body["ranking"]


def test_break_even_comes_from_the_price_alone():
    with board_of(nfl=[game(1, **BUF, spread=-3.5, home_ml=-175, away_ml=150)]):
        body = fetch(market="spread")

    for e in body["edges"]:
        # Both sides of a -110 spread need the same rate to break even, whatever
        # the model thinks of them.
        assert round(e["break_even_prob"], 3) == 0.524


def test_an_assumed_price_is_flagged_as_assumed():
    """
    ESPN publishes a spread with no price. Pricing it at -110 is reasonable;
    presenting that as a quote a book actually offered is not.
    """
    with board_of(nfl=[game(1, **BUF, spread=-3.5, total=46.5,
                            home_ml=-175, away_ml=150)]):
        body = fetch()

    by_market = {e["market"]: e for e in body["edges"]}
    assert by_market["spread"]["assumed_price"] is True
    assert by_market["total"]["assumed_price"] is True
    if "moneyline" in by_market:
        assert by_market["moneyline"]["assumed_price"] is False


def test_rows_carry_the_fair_line_against_the_market_line():
    with board_of(nfl=[game(1, **BUF, spread=-3.5, home_ml=-175, away_ml=150)]):
        body = fetch(market="spread")

    row = next(e for e in body["edges"] if e["market"] == "spread")
    assert row["fair_label"].startswith("BUF ")
    assert row["market_label_spread"] == "BUF -3.5"
    assert row["edge_points"] is not None


def test_rows_carry_the_first_few_reasons():
    with board_of(nfl=[game(1, **BUF, spread=-3.5, home_ml=-175, away_ml=150)]):
        body = fetch()
    assert all(isinstance(e["why"], list) for e in body["edges"])
    assert any(e["why"] for e in body["edges"])


# ─── Filters ─────────────────────────────────────────────────────────────────

def test_filtering_by_league():
    nfl = [game(1, **BUF, spread=-3.5, home_ml=-175, away_ml=150)]
    with board_of(nfl=nfl):
        assert {e["league"] for e in fetch(league="nfl")["edges"]} == {"nfl"}
        assert fetch(league="ncaaf")["edges"] == []


def test_filtering_by_market():
    with board_of(nfl=[game(1, **BUF, spread=-3.5, total=46.5,
                            home_ml=-175, away_ml=150)]):
        assert {e["market"] for e in fetch(market="total")["edges"]} == {"total"}


def test_filtering_by_minimum_expected_value():
    with board_of(nfl=[game(1, **BUF, spread=-3.5, total=46.5,
                            home_ml=-175, away_ml=150)]):
        loose = fetch(min_ev=0)
        tight = fetch(min_ev=0.08)

    assert len(tight["edges"]) <= len(loose["edges"])
    assert all(e["ev_per_unit"] >= 0.08 for e in tight["edges"])


def test_filtering_by_kickoff_window():
    soon = game(1, **BUF, hours=3, spread=-3.5, home_ml=-175, away_ml=150)
    later = game(2, **DAL, hours=70, spread=1.5, home_ml=105, away_ml=-125)
    with board_of(nfl=[soon, later]):
        body = fetch(hours=6)
    assert {e["event_id"] for e in body["edges"]} == {"1"}


def test_a_game_already_under_way_is_not_offered_as_an_edge():
    # An edge you can no longer take is not an edge.
    with board_of(nfl=[game(1, **BUF, hours=-1, state="in",
                            spread=-3.5, home_ml=-175, away_ml=150)]):
        assert fetch()["edges"] == []


def test_filters_that_match_nothing_say_so_rather_than_looking_broken():
    with board_of(nfl=[game(1, **BUF, spread=-3.5, home_ml=-175, away_ml=150)]):
        body = fetch(min_ev=0.95)
    assert body["edges"] == []
    assert "clears these filters" in body["note"]
    assert body["scanned"] > 0


def test_an_empty_board_is_distinguished_from_filters_matching_nothing():
    with board_of():
        body = fetch()
    assert body["edges"] == []
    assert body["scanned"] == 0
    assert "nothing to rank" in body["note"]


def test_the_scan_reuses_the_board_rather_than_refetching_the_slate():
    """
    The numbers on this page and on the homepage have to be the same numbers.
    The old scan ran its own pass over the feeds, which meant they could drift
    apart between two requests seconds either side of a cache expiry.
    """
    calls = {"n": 0}
    real = pred._build_board

    async def counted(days):
        calls["n"] += 1
        return await real(days)

    games = [game(1, **BUF, spread=-3.5, home_ml=-175, away_ml=150)]
    with board_of(nfl=games), patch.object(pred, "_build_board", counted):
        client.get("/api/v1/board")
        client.get("/api/v1/edges")
        client.get("/api/v1/edges?market=spread")

    assert calls["n"] == 1, f"the board was rebuilt {calls['n']} times"
