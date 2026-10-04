"""
Player projections, tuned against the weekly data we already ingest.

The change that matters is the spread. The over/under probability comes
entirely out of it, and it used to be one number per market for every player
alive — so a possession receiver who catches five every week and a deep threat
who alternates between two and nine were treated as the same bet. They have
the same average and nothing else in common.
"""
from __future__ import annotations

import pytest

from src.ingest.nflverse import PlayerGame
from src.ingest.player_stats import PlayerUsage
from src.predict import player_props as pp
from src.predict import priors


def passer(**kw) -> PlayerUsage:
    base = dict(
        athlete_id="nflverse:1", name="J. Allen", short_name="Allen",
        position="QB", team_abbr="BUF", role="passer", games_played=8,
        pass_yards_pg=255.0, pass_attempts_pg=32.0, pass_tds_pg=1.9,
    )
    base.update(kw)
    return PlayerUsage(**base)


def receiver(**kw) -> PlayerUsage:
    base = dict(
        athlete_id="nflverse:2", name="A Receiver", short_name="Rec",
        position="WR", team_abbr="BUF", role="receiver", games_played=8,
        receptions_pg=5.0, rec_yards_pg=70.0, rec_tds_pg=0.5,
    )
    base.update(kw)
    return PlayerUsage(**base)


def log(values, opponent="MIA"):
    return [
        PlayerGame(season=2026, week=i, opponent=opponent, value=float(v))
        for i, v in enumerate(values, start=1)
    ]


# ─── The spread is the player's own, where there is enough of it ─────────────

def test_two_players_with_the_same_average_are_not_the_same_bet():
    steady = [5, 5, 6, 4, 5, 5, 6, 5]
    volatile = [2, 9, 1, 8, 3, 9, 2, 7]
    assert sum(steady) == sum(volatile), "same mean, so only the spread differs"

    s_sigma, s_src, _ = pp.sigma_for(5.0, "receptions", steady)
    v_sigma, v_src, _ = pp.sigma_for(5.0, "receptions", volatile)

    assert v_sigma > s_sigma * 1.5
    assert s_src == v_src == "player"

    # And that reaches the output, which is the whole point.
    steady_over = pp.over_probability(5.0, 6.5, "receptions", steady)
    volatile_over = pp.over_probability(5.0, 6.5, "receptions", volatile)
    assert volatile_over > steady_over * 2


def test_a_short_log_leaves_the_market_prior_in_charge():
    """
    A standard deviation off two games is mostly noise. It should barely move
    the number, and should say that the prior is still doing the work.
    """
    sigma, source, games = pp.sigma_for(5.0, "receptions", [5, 5])
    prior = 5.0 * pp._REL_SIGMA["receptions"]
    assert source == "market"
    assert games == 2
    assert abs(sigma - prior) < prior * 0.4


def test_no_log_at_all_falls_back_to_the_prior_exactly():
    sigma, source, games = pp.sigma_for(5.0, "receptions", None)
    assert source == "market"
    assert games == 0
    assert sigma == pytest.approx(5.0 * pp._REL_SIGMA["receptions"])


def test_a_lucky_run_of_identical_games_cannot_collapse_the_spread():
    """
    Eight identical games is a real possibility for a low-volume market, and a
    zero spread would turn every line into a near certainty.
    """
    sigma, _, _ = pp.sigma_for(5.0, "receptions", [5] * 8)
    assert sigma >= 5.0 * pp.SIGMA_REL_FLOOR
    prob = pp.over_probability(5.0, 6.5, "receptions", [5] * 8)
    assert prob is not None and prob < 0.5
    assert prob > 0.0001, "a floored spread still leaves real uncertainty"


def test_an_unknown_market_has_no_spread_and_claims_no_probability():
    sigma, source, _ = pp.sigma_for(5.0, "hat_tricks", [1, 2, 3])
    assert sigma is None and source == "none"
    assert pp.over_probability(5.0, 6.5, "hat_tricks", [1, 2, 3]) is None


# ─── Recent form ─────────────────────────────────────────────────────────────

def test_recent_form_pulls_the_projection_toward_the_current_role():
    rising = log([180, 190, 200, 300, 310, 320, 330])
    out = pp.project_player(passer(), "nfl", None, logs={"pass_yards": rising})
    yards = next(p for p in out if p.market == "pass_yards")

    assert yards.recent_avg is not None and yards.recent_avg > yards.season_avg
    assert yards.projection > yards.season_avg
    # ...but nowhere near all the way, because three good games is a small
    # sample and one blowout should not own a projection.
    assert yards.projection < yards.recent_avg
    assert 0 < yards.form_weight <= pp.FORM_MAX_WEIGHT


def test_no_log_means_the_season_average_stands_untouched():
    out = pp.project_player(passer(), "nfl", None)
    yards = next(p for p in out if p.market == "pass_yards")
    assert yards.recent_avg is None
    assert yards.form_weight == 0.0
    assert yards.projection == pytest.approx(yards.season_avg, abs=0.05)


def test_a_box_score_already_played_is_never_rescaled():
    """An actual is a fact. Scaling it by form or an opponent would be fiction."""
    out = pp.project_player(
        passer(actual=True), "nfl", 35.0,
        opponent_abbr="MIA", logs={"pass_yards": log([100, 120, 140])},
    )
    yards = next(p for p in out if p.market == "pass_yards")
    assert yards.actual is True
    assert yards.projection == pytest.approx(yards.season_avg, abs=0.05)
    assert yards.environment_mult == 1.0
    assert yards.opponent_mult == 1.0


# ─── Opponent ────────────────────────────────────────────────────────────────

def test_a_missing_opponent_rating_is_said_rather_than_assumed_average():
    priors.reset()
    mult, note = pp.opponent_multiplier("nfl", "MIA")
    assert mult == 1.0
    assert "no play-by-play rating" in note


def test_college_props_say_the_opponent_is_not_modelled():
    priors.reset()
    mult, note = pp.opponent_multiplier("ncaaf", "AUB")
    assert mult == 1.0
    assert "not modelled" in note


def test_a_tougher_defence_shades_the_projection_down():
    priors._priors["nfl"] = priors.LeaguePriors(
        league="nfl", ok=True, source="nflverse-epa", fetched_at="now",
        teams={
            c: priors.TeamPrior(code=c, points=p, games=6, source="nflverse-epa")
            for c, p in (("MIA", 9.0), ("NE", -9.0), ("BUF", 4.0))
        },
    )
    try:
        tough, tough_note = pp.opponent_multiplier("nfl", "MIA")
        soft, _ = pp.opponent_multiplier("nfl", "NE")
        assert tough < 1.0 < soft
        assert "tougher than average" in tough_note
        # Bounded: a good defence does not halve a receiver's yardage.
        assert tough >= pp.OPPONENT_FLOOR and soft <= pp.OPPONENT_CEILING
    finally:
        priors.reset()


def test_an_unknown_opponent_code_changes_nothing():
    mult, note = pp.opponent_multiplier("nfl", "")
    assert mult == 1.0 and "unknown" in note


# ─── The evidence is carried, not just the conclusion ────────────────────────

def test_the_game_log_rides_along_so_the_number_can_be_checked():
    games = log([210, 240, 255, 260, 300])
    out = pp.project_player(passer(), "nfl", 27.0, logs={"pass_yards": games})
    yards = next(p for p in out if p.market == "pass_yards")

    assert len(yards.game_log) == 5
    assert yards.game_log[0] == {"season": 2026, "week": 1, "opponent": "MIA", "value": 210.0}
    assert yards.sigma is not None
    assert yards.sigma_source == "market"      # five games is not yet enough
    assert yards.sigma_games == 5


def test_a_projection_reports_both_multipliers_it_applied():
    out = pp.project_player(receiver(), "nfl", 31.0, opponent_abbr="MIA")
    rec = next(p for p in out if p.market == "rec_yards")
    assert rec.environment_mult > 1.0, "a 31-point projection is a busy offence"
    assert rec.opponent_mult == 1.0        # no ratings loaded in this test
    assert rec.opponent_abbr == "MIA"


def test_a_player_with_too_few_games_is_omitted_rather_than_estimated():
    assert pp.project_player(passer(games_played=1), "nfl", 27.0) == []
