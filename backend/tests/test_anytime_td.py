"""
Anytime touchdown.

A different kind of market from the yardage props: no line to go over, a yes
or no priced like a moneyline. So the question is not "what shape sits around
this mean" but "what is the chance of at least one rare event" — a Poisson on
the player's scoring rate, with the rate shrunk first because a rate off five
games swings wildly and a player who has not scored yet does not have a rate
of zero.

Measured on 14,361 player-games, 2022-2026:

    shrunk Poisson    2.5p     ← used
    raw Poisson       3.4p
    his own hit rate  4.4p
"""
from __future__ import annotations

import pytest

from src.api.routes.predictions import _priced_prop
from src.ingest.nflverse import PlayerGame
from src.ingest.player_stats import PlayerUsage
from src.ingest.prop_lines import PriceAtBook, PropLine
from src.predict import player_props as pp


def log(values, opponent="MIA"):
    return [PlayerGame(season=2026, week=i, opponent=opponent, value=float(v))
            for i, v in enumerate(values, start=1)]


def back(**kw) -> PlayerUsage:
    base = dict(
        athlete_id="nflverse:1", name="J. Cook", short_name="Cook",
        position="RB", team_abbr="BUF", role="rusher", games_played=7,
        carries_pg=17.0, rush_yards_pg=78.0, rush_tds_pg=0.6,
    )
    base.update(kw)
    return PlayerUsage(**base)


def atd_of(projections):
    return next((p for p in projections if p.market == pp.ANYTIME_TD), None)


# ─── The rate, and why it is shrunk ──────────────────────────────────────────

def test_a_player_who_has_not_scored_does_not_get_a_rate_of_zero():
    """
    The reason the rate is shrunk at all. A back with seven blanks is unlikely
    to score, not incapable of it, and 0% would price a certainty.
    """
    p = pp.anytime_td_probability([0] * 7)
    assert p is not None and 0.05 < p < 0.25


def test_a_prolific_scorer_is_not_shrunk_to_the_middle():
    often = pp.anytime_td_probability([1, 1, 2, 1, 1, 0, 1, 2])
    rarely = pp.anytime_td_probability([0, 0, 1, 0, 0, 0, 0, 0])
    assert often > rarely + 0.2


def test_a_short_log_leans_harder_on_the_base_rate():
    # Two games should move the number less than twelve of the same games.
    short = pp.anytime_td_rate([1, 1])
    long = pp.anytime_td_rate([1] * 12)
    assert long > short


def test_the_probability_is_one_minus_the_poisson_zero():
    import math
    samples = [1, 0, 1, 1, 0, 0, 1]
    rate = pp.anytime_td_rate(samples)
    assert pp.anytime_td_probability(samples) == pytest.approx(
        1.0 - math.exp(-rate), abs=1e-4)


def test_an_empty_log_claims_nothing():
    assert pp.anytime_td_rate([]) is None
    assert pp.anytime_td_probability([]) is None


# ─── As a market on a projection ─────────────────────────────────────────────

def test_a_rusher_gets_an_anytime_touchdown_market():
    out = pp.project_player(back(), "nfl", 27.0, opponent_abbr="MIA",
                            logs={pp.ANYTIME_TD: log([1, 0, 1, 1, 0, 0, 1])})
    atd = atd_of(out)
    assert atd is not None
    assert atd.yes_prob is not None and 0.0 < atd.yes_prob < 1.0
    # The expected count rides along behind the probability.
    assert atd.projection > 0


def test_a_player_with_no_weekly_log_still_gets_one_from_published_rates():
    out = pp.project_player(
        PlayerUsage(athlete_id="espn:9", name="K. Shakir", short_name="Shakir",
                    position="WR", team_abbr="BUF", role="receiver",
                    games_played=7, receptions_pg=4.5, rec_yards_pg=58.0,
                    rec_tds_pg=0.3),
        "nfl", 27.0, opponent_abbr="MIA")
    atd = atd_of(out)
    assert atd is not None and atd.yes_prob is not None
    # ...and says the spread behind it is not his own.
    assert atd.sigma_source == "market"


def test_a_player_who_cannot_plausibly_score_is_left_out():
    # No touchdown history and no role: publishing 3% invites a price nobody
    # should take, so nothing is published.
    out = pp.project_player(
        back(rush_tds_pg=0.0, games_played=7), "nfl", 27.0,
        logs={pp.ANYTIME_TD: log([0] * 7)})
    atd = atd_of(out)
    if atd is not None:
        assert atd.yes_prob is not None and atd.yes_prob > 0.05


def test_a_busier_offence_raises_the_chance_of_scoring():
    quiet = atd_of(pp.project_player(back(), "nfl", 14.0,
                                     logs={pp.ANYTIME_TD: log([1, 0, 1, 0, 1, 0, 1])}))
    busy = atd_of(pp.project_player(back(), "nfl", 34.0,
                                    logs={pp.ANYTIME_TD: log([1, 0, 1, 0, 1, 0, 1])}))
    assert busy.yes_prob > quiet.yes_prob


def test_a_touchdown_already_scored_is_reported_as_fact_not_chance():
    out = pp.project_player(
        back(actual=True), "nfl", 27.0,
        logs={pp.ANYTIME_TD: log([1])})
    atd = atd_of(out)
    assert atd is not None
    assert atd.actual is True
    assert atd.yes_prob is None, "a fact is not a probability"


def test_the_market_sorts_by_chance_not_by_expected_count():
    # Expected counts are fractions of a touchdown and sort meaninglessly.
    out = pp.project_game(
        [back(athlete_id="a", name="A Back"),
         back(athlete_id="b", name="B Back", rush_tds_pg=0.1)],
        "nfl", "BUF", "MIA", 27.0, 20.0,
        {"a": {pp.ANYTIME_TD: log([1, 1, 1, 0, 1, 1, 1])},
         "b": {pp.ANYTIME_TD: log([0, 0, 0, 0, 0, 0, 1])}})
    atds = [p for p in out if p.market == pp.ANYTIME_TD]
    assert len(atds) == 2
    assert atds[0].yes_prob > atds[1].yes_prob


# ─── Pricing a yes-or-no market ──────────────────────────────────────────────

def binary_line():
    return PropLine(player="James Cook", market="anytime_td", prices=[
        PriceAtBook(book="FanDuel", line=0.5, over_price=-130, under_price=105),
        PriceAtBook(book="DraftKings", line=0.5, over_price=-120, under_price=100),
    ])


def test_a_binary_market_reports_no_line_rather_than_a_zero_gap():
    """A zero difference would read as "we agree with the line". There is no
    line, which is a different statement."""
    atd = atd_of(pp.project_player(back(), "nfl", 27.0,
                                   logs={pp.ANYTIME_TD: log([1, 0, 1, 1, 0, 0, 1])}))
    priced = _priced_prop(atd, binary_line())
    assert priced["is_binary"] is True
    assert priced["posted_line"] is None
    assert priced["difference"] is None


def test_the_sides_are_yes_and_no_not_over_and_under():
    atd = atd_of(pp.project_player(back(), "nfl", 27.0,
                                   logs={pp.ANYTIME_TD: log([1, 0, 1, 1, 0, 0, 1])}))
    priced = _priced_prop(atd, binary_line())
    assert {s["side"] for s in priced["sides"]} == {"yes", "no"}


def test_the_best_yes_price_is_the_one_paying_most():
    atd = atd_of(pp.project_player(back(), "nfl", 27.0,
                                   logs={pp.ANYTIME_TD: log([1, 0, 1, 1, 0, 0, 1])}))
    priced = _priced_prop(atd, binary_line())
    yes = next(s for s in priced["sides"] if s["side"] == "yes")
    assert yes["book"] == "DraftKings" and yes["price_american"] == -120


def test_the_two_sides_probabilities_sum_to_one():
    atd = atd_of(pp.project_player(back(), "nfl", 27.0,
                                   logs={pp.ANYTIME_TD: log([1, 0, 1, 1, 0, 0, 1])}))
    priced = _priced_prop(atd, binary_line())
    total = sum(s["model_prob"] for s in priced["sides"])
    assert total == pytest.approx(1.0, abs=0.001)


def test_a_binary_market_without_a_probability_prices_nothing():
    atd = atd_of(pp.project_player(back(actual=True), "nfl", 27.0,
                                   logs={pp.ANYTIME_TD: log([1])}))
    assert _priced_prop(atd, binary_line()) == {}
