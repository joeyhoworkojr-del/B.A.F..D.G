"""
Posted player-prop lines, and what happens without them.

A projection of 284 passing yards is interesting; "284 against a posted 267.5,
at -115, best price at FanDuel" is the product. That needs an odds provider,
because ESPN's feeds carry game lines and no player props.

The behaviour that matters most is the absence case. With no key there must be
no lines, no prices and no edge — and the page must say that is why, rather
than showing an empty list that reads as "we looked and there is nothing".
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ingest import prop_lines


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    monkeypatch.delenv(prop_lines.KEY_ENV_VAR, raising=False)
    prop_lines.clear_cache()
    prop_lines._last_fetch.clear()
    yield
    prop_lines.clear_cache()


# ─── Matching a player across three feeds that spell him differently ─────────

def test_the_same_player_keys_the_same_from_every_feed():
    # ESPN publishes "J. Allen", nflverse "J.Allen", a book "Josh Allen".
    keys = {prop_lines.normalise_name(n)
            for n in ("Josh Allen", "J. Allen", "J.Allen", "Allen, Josh")}
    assert len(keys) == 1


def test_generational_suffixes_do_not_split_a_player_in_two():
    assert (prop_lines.normalise_name("Odell Beckham Jr.")
            == prop_lines.normalise_name("O. Beckham"))


def test_different_players_do_not_collide():
    assert (prop_lines.normalise_name("Josh Allen")
            != prop_lines.normalise_name("Keenan Allen"))


def test_an_empty_name_keys_to_nothing_rather_than_matching_everyone():
    assert prop_lines.normalise_name("") == ""
    assert prop_lines.normalise_name("   ") == ""


def test_a_game_is_matched_on_both_teams_however_they_are_spelled():
    event = {"home_team": "Los Angeles Rams", "away_team": "Seattle Seahawks"}
    assert prop_lines._matches(event, "LA Rams", "Seahawks")
    assert not prop_lines._matches(event, "LA Rams", "Cowboys")
    assert not prop_lines._matches(event, "Dallas Cowboys", "Seahawks")


# ─── No key is a statement, not an empty result ──────────────────────────────

@pytest.mark.asyncio
async def test_with_no_key_there_are_no_lines_and_the_note_says_why():
    out = await prop_lines.fetch_prop_lines("nfl", "1", "Buffalo Bills", "Miami Dolphins")
    assert out.ok is False
    assert out.lines == {}
    assert prop_lines.KEY_ENV_VAR in out.note
    assert "no prop edge is claimed" in out.note


def test_the_status_page_says_configured_not_working():
    # A key being set is not the same as lines arriving, and the public page
    # must not let one stand in for the other.
    st = prop_lines.status()
    assert st["requires_key"] is True
    assert st["configured"] is False
    assert st["last_success"] is False
    assert prop_lines.KEY_ENV_VAR in st["last_error"]


# ─── Parsing the provider's shape ────────────────────────────────────────────

def event_payload():
    """One event, two books, documented shape: the player is in `description`
    and Over/Under is in `name`."""
    def outcome(name, player, price, point):
        return {"name": name, "description": player, "price": price, "point": point}
    return {
        "id": "abc", "home_team": "Buffalo Bills", "away_team": "Miami Dolphins",
        "bookmakers": [
            {"key": "fanduel", "title": "FanDuel", "markets": [
                {"key": "player_pass_yds", "outcomes": [
                    outcome("Over", "Josh Allen", -105, 267.5),
                    outcome("Under", "Josh Allen", -115, 267.5),
                ]},
            ]},
            {"key": "draftkings", "title": "DraftKings", "markets": [
                {"key": "player_pass_yds", "outcomes": [
                    outcome("Over", "Josh Allen", -120, 267.5),
                    outcome("Under", "Josh Allen", +100, 267.5),
                ]},
                {"key": "player_receptions", "outcomes": [
                    outcome("Over", "Khalil Shakir", -110, 4.5),
                    outcome("Under", "Khalil Shakir", -110, 4.5),
                ]},
            ]},
        ],
    }


def test_markets_are_mapped_onto_our_own_keys():
    out = prop_lines._parse_event("nfl", event_payload(), wanted=set())
    assert ("allen:j", "pass_yards") in out.lines
    assert ("shakir:k", "receptions") in out.lines


def test_the_best_price_is_the_one_paying_most_on_that_side():
    """
    Compared on American prices across the sign change: +100 beats -105 beats
    -115 beats -120. Getting this backwards would recommend the worst book.
    """
    out = prop_lines._parse_event("nfl", event_payload(), wanted=set())
    line = out.lines[("allen:j", "pass_yards")]

    best_over = line.best_over()
    assert best_over.book == "FanDuel" and best_over.over_price == -105

    best_under = line.best_under()
    assert best_under.book == "DraftKings" and best_under.under_price == 100


def test_the_consensus_line_is_the_median_of_what_is_posted():
    out = prop_lines._parse_event("nfl", event_payload(), wanted=set())
    assert out.lines[("allen:j", "pass_yards")].consensus_line == 267.5


def test_every_book_that_posted_is_named():
    out = prop_lines._parse_event("nfl", event_payload(), wanted=set())
    assert out.books == ["DraftKings", "FanDuel"]


def test_lines_for_players_we_do_not_project_are_counted_not_kept():
    # A quiet mismatch between the two feeds would look like a thin market.
    out = prop_lines._parse_event("nfl", event_payload(), wanted={"allen:j"})
    assert ("shakir:k", "receptions") not in out.lines
    assert out.unmatched > 0


def test_a_market_we_do_not_project_is_ignored_rather_than_half_parsed():
    payload = event_payload()
    payload["bookmakers"][0]["markets"].append(
        {"key": "player_field_goals", "outcomes": [
            {"name": "Over", "description": "Tyler Bass", "price": -110, "point": 1.5}]})
    out = prop_lines._parse_event("nfl", payload, wanted=set())
    assert all(m != "field_goals" for _, m in out.lines)


def test_an_outcome_missing_its_line_or_price_is_skipped():
    payload = {
        "id": "x", "home_team": "A", "away_team": "B",
        "bookmakers": [{"title": "Book", "markets": [{"key": "player_pass_yds",
            "outcomes": [
                {"name": "Over", "description": "Josh Allen", "price": None, "point": 250},
                {"name": "Over", "description": "Josh Allen", "price": -110, "point": None},
                {"name": "Over", "description": "", "price": -110, "point": 250},
            ]}]}],
    }
    assert prop_lines._parse_event("nfl", payload, wanted=set()).lines == {}


# ─── Failure paths ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_an_unreachable_provider_is_reported_as_unreachable(monkeypatch):
    monkeypatch.setenv(prop_lines.KEY_ENV_VAR, "test-key")

    class Boom:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, *a, **k): raise OSError("refused")

    with patch("httpx.AsyncClient", lambda **k: Boom()):
        out = await prop_lines.fetch_prop_lines("nfl", "1", "Buffalo Bills", "Miami Dolphins")

    assert out.ok is False
    assert "unreachable" in out.note
    assert out.lines == {}


@pytest.mark.asyncio
async def test_a_game_the_provider_does_not_list_is_not_an_error(monkeypatch):
    monkeypatch.setenv(prop_lines.KEY_ENV_VAR, "test-key")

    response = MagicMock()
    response.json.return_value = []
    response.raise_for_status.return_value = None
    client = AsyncMock()
    client.get.return_value = response

    with patch("httpx.AsyncClient") as cls:
        cls.return_value.__aenter__.return_value = client
        out = await prop_lines.fetch_prop_lines("nfl", "1", "Buffalo Bills", "Miami Dolphins")

    assert out.ok is True              # the provider answered; it just has nothing
    assert out.lines == {}
    assert "not listing this game" in out.note


@pytest.mark.asyncio
async def test_an_unsupported_league_claims_nothing(monkeypatch):
    monkeypatch.setenv(prop_lines.KEY_ENV_VAR, "test-key")
    out = await prop_lines.fetch_prop_lines("cricket", "1", "A", "B")
    assert out.ok is False and "unsupported league" in out.note
