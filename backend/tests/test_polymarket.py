"""Polymarket Gamma parsing + game matching tests."""
from __future__ import annotations

from src.ingest.polymarket import PolyMarket, _parse_event, match_game


def test_parse_event_json_string_fields() -> None:
    ev = {
        "slug": "mlb-nyy-bos-2026-07-04",
        "title": "Yankees vs. Red Sox",
        "volume": "50000",
        "markets": [{
            "outcomes": '["Yankees", "Red Sox"]',
            "outcomePrices": '["0.58", "0.42"]',
            "volume": "50000",
        }],
    }
    m = _parse_event(ev)
    assert m is not None
    assert m.outcomes == ["Yankees", "Red Sox"]
    assert abs(sum(m.prices) - 1.0) < 1e-9
    assert m.volume_usd == 50000.0
    assert m.url.endswith(m.slug)


def test_parse_event_skips_non_binary() -> None:
    assert _parse_event({"slug": "x", "title": "y", "markets": [
        {"outcomes": '["A","B","C"]', "outcomePrices": '["0.3","0.3","0.4"]'},
    ]}) is None


def test_match_game_team_outcomes() -> None:
    markets = [PolyMarket(
        slug="s", title="Yankees vs. Red Sox",
        outcomes=["Yankees", "Red Sox"], prices=[0.58, 0.42],
        volume_usd=1000.0, url="u",
    )]
    res = match_game(markets, "New York Yankees", "Boston Red Sox")
    assert res is not None and abs(res["home_prob"] - 0.58) < 1e-9
    # Reversed orientation flips the probability
    res2 = match_game(markets, "Boston Red Sox", "New York Yankees")
    assert res2 is not None and abs(res2["home_prob"] - 0.42) < 1e-9


def test_match_game_yes_no_market() -> None:
    markets = [PolyMarket(
        slug="s", title="Will the Chiefs beat the Bills?",
        outcomes=["Yes", "No"], prices=[0.64, 0.36],
        volume_usd=5.0, url="u",
    )]
    res = match_game(markets, "Kansas City Chiefs", "Buffalo Bills")
    assert res is not None and abs(res["home_prob"] - 0.64) < 1e-9


def test_match_game_no_match() -> None:
    markets = [PolyMarket(
        slug="s", title="Yankees vs. Red Sox",
        outcomes=["Yankees", "Red Sox"], prices=[0.5, 0.5],
        volume_usd=0.0, url="u",
    )]
    assert match_game(markets, "Los Angeles Dodgers", "San Diego Padres") is None
