"""Player prop projections: scaling, honesty about actuals, and empty states."""
from __future__ import annotations

import pytest

from src.ingest import player_stats
from src.ingest.player_stats import PlayerUsage, parse_pool
from src.predict import player_props as pp


def passer(**kw) -> PlayerUsage:
    base = dict(athlete_id="1", name="J. Passer", short_name="J. Passer",
                position="QB", team_abbr="FSU", role="passer", games_played=8,
                pass_yards_pg=260.0, pass_attempts_pg=32.0, pass_tds_pg=2.0)
    base.update(kw)
    return PlayerUsage(**base)


# ─── Environment scaling ─────────────────────────────────────────────────────

def test_no_team_projection_leaves_the_season_average_untouched():
    assert pp.environment_multiplier("ncaaf", None) == 1.0


def test_a_league_average_offence_scores_a_neutral_multiplier():
    assert pp.environment_multiplier("ncaaf", pp.LEAGUE_AVG_TEAM_POINTS["ncaaf"]) == 1.0


def test_a_high_scoring_projection_raises_the_line_but_is_damped():
    mult = pp.environment_multiplier("ncaaf", 41.25)   # +50% on a 27.5 baseline
    assert 1.0 < mult < 1.5, "a 50% team swing must not become a 50% player swing"
    assert mult == pytest.approx(1.225, abs=1e-3)


def test_the_multiplier_is_clamped_at_both_ends():
    assert pp.environment_multiplier("nfl", 200.0) == pp.MULT_CEILING
    assert pp.environment_multiplier("nfl", 1.0) == pp.MULT_FLOOR


# ─── Projections ─────────────────────────────────────────────────────────────

def test_projection_scales_the_season_average():
    [proj] = [p for p in pp.project_player(passer(), "ncaaf", 41.25)
              if p.market == "pass_yards"]
    assert proj.season_avg == 260.0
    assert proj.projection == pytest.approx(318.5, abs=0.1)


def test_a_player_with_too_few_games_is_not_projected():
    assert pp.project_player(passer(games_played=1), "ncaaf", 30.0) == []


def test_a_player_with_no_published_usage_is_not_projected():
    thin = passer(pass_yards_pg=None, pass_attempts_pg=None, pass_tds_pg=None)
    assert pp.project_player(thin, "ncaaf", 30.0) == []


def test_noise_level_counts_are_withheld():
    # 0.1 TDs per game is not a publishable projection.
    quiet = passer(pass_yards_pg=None, pass_attempts_pg=None, pass_tds_pg=0.1)
    assert [p.market for p in pp.project_player(quiet, "ncaaf", 27.5)] == []


def test_an_actual_box_score_line_is_never_rescaled():
    """A number that already happened must be reported, not forecast."""
    actual = passer(actual=True, games_played=1, pass_yards_pg=301.0)
    [proj] = [p for p in pp.project_player(actual, "ncaaf", 45.0)
              if p.market == "pass_yards"]
    assert proj.projection == 301.0
    assert proj.actual is True


def test_each_player_is_scaled_by_their_own_teams_projection():
    home = passer(athlete_id="h", team_abbr="FSU")
    away = passer(athlete_id="a", team_abbr="CLEM")
    out = pp.project_game([home, away], "ncaaf", "FSU", "CLEM",
                          home_points=41.25, away_points=13.75)
    by_team = {p.team_abbr: p.projection for p in out if p.market == "pass_yards"}
    assert by_team["FSU"] > by_team["CLEM"]


def test_a_player_on_an_unknown_team_falls_back_to_the_season_average():
    stray = passer(team_abbr="ZZZ")
    [proj] = [p for p in pp.project_game([stray], "ncaaf", "FSU", "CLEM", 45.0, 10.0)
              if p.market == "pass_yards"]
    assert proj.projection == 260.0


# ─── Over/under probability ──────────────────────────────────────────────────

def test_a_line_at_the_projection_is_a_coin_flip():
    assert pp.over_probability(280.0, 280.0, "pass_yards") == pytest.approx(0.5, abs=1e-6)


def test_over_probability_moves_the_right_way():
    low = pp.over_probability(280.0, 240.5, "pass_yards")
    high = pp.over_probability(280.0, 320.5, "pass_yards")
    assert low > 0.5 > high


def test_unknown_market_has_no_probability():
    assert pp.over_probability(280.0, 250.0, "field_goals") is None


# ─── Ingest parsing ──────────────────────────────────────────────────────────

SUMMARY = {
    "header": {"competitions": [{"competitors": [
        {"homeAway": "home", "team": {"abbreviation": "FSU"}},
        {"homeAway": "away", "team": {"abbreviation": "CLEM"}},
    ]}]},
    "leaders": [{
        "team": {"abbreviation": "FSU"},
        "leaders": [{
            "name": "passingYards",
            "leaders": [{
                "athlete": {"id": "42", "displayName": "T. Castellanos",
                            "shortName": "T. Castellanos", "position": {"abbreviation": "QB"}},
                "statistics": [
                    {"name": "gamesPlayed", "value": 8},
                    {"name": "passingYards", "value": 2080},
                    {"name": "passingAttempts", "value": 256},
                    {"name": "passingTouchdowns", "value": 16},
                ],
            }],
        }],
    }],
}


def test_season_totals_are_normalised_to_per_game():
    pool = parse_pool("ncaaf", "401752", SUMMARY)
    [player] = pool.players
    assert player.pass_yards_pg == 260.0     # 2080 over 8 games
    assert player.pass_attempts_pg == 32.0
    assert player.actual is False


def test_home_and_away_abbreviations_are_read():
    pool = parse_pool("ncaaf", "401752", SUMMARY)
    assert (pool.home_abbr, pool.away_abbr) == ("FSU", "CLEM")


def test_a_boxscore_line_supersedes_the_season_average():
    payload = dict(SUMMARY)
    payload["boxscore"] = {"players": [{
        "team": {"abbreviation": "FSU"},
        "statistics": [{
            "name": "passing", "keys": ["C/ATT", "YDS", "AVG", "TD", "INT"],
            "athletes": [{
                "athlete": {"id": "42", "displayName": "T. Castellanos",
                            "position": {"abbreviation": "QB"}},
                "stats": ["24/38", "301", "7.9", "3", "1"],
            }],
        }],
    }]}
    pool = parse_pool("ncaaf", "401752", payload)
    [player] = [p for p in pool.players if p.role == "passer"]
    assert player.actual is True
    assert player.pass_yards_pg == 301.0
    assert player.pass_attempts_pg == 38.0   # taken from the ATT half of "24/38"


def test_a_malformed_payload_yields_no_players_rather_than_raising():
    pool = parse_pool("ncaaf", "401752", {"leaders": "not-a-list"})
    assert pool.players == []


@pytest.mark.asyncio
async def test_unknown_league_reports_not_ok():
    pool = await player_stats.fetch_player_pool("cricket", "1")
    assert pool.ok is False
