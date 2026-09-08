"""
The nflverse and CollegeFootballData feeds, and the priors they drive.

Fixtures are trimmed from the real payloads — the nflverse CSV headers here are
copied from the published 2024 release files, and the CFBD shapes follow the
documented responses. The point of these tests is the failure behaviour: a
missing key, a 404 season, a renamed column and a half-parsed row must all
produce "no data" rather than an exception or an invented number.
"""
from __future__ import annotations

import asyncio

import pytest

from src.data import ncaaf as ncaaf_data
from src.data import nfl as nfl_data
from src.ingest import cfbd, nflverse
from src.predict import priors


# ── nflverse ─────────────────────────────────────────────────────────────────

PLAYER_CSV = (
    "player_id,player_name,player_display_name,position,position_group,season,week,"
    "season_type,team,opponent_team,completions,attempts,passing_yards,passing_tds,"
    "passing_epa,carries,rushing_yards,rushing_tds,rushing_epa,receptions,targets,"
    "receiving_yards,receiving_tds,receiving_epa,target_share\n"
    "00-0023459,A.Rodgers,Aaron Rodgers,QB,QB,2024,1,REG,NYJ,SF,13,21,167,1,3.25,1,-1,0,0,0,0,0,0,,0\n"
    "00-0023459,A.Rodgers,Aaron Rodgers,QB,QB,2024,2,REG,NYJ,TEN,20,31,240,2,6.10,2,4,0,0.5,0,0,0,0,,0\n"
    "00-0036322,G.Wilson,Garrett Wilson,WR,WR,2024,1,REG,NYJ,SF,0,0,0,0,,0,0,0,,7,12,88,1,4.2,0.31\n"
)

TEAM_CSV = (
    "season,week,team,season_type,opponent_team,passing_epa,rushing_epa,"
    "passing_yards,rushing_yards\n"
    "2024,1,NYJ,REG,SF,4.0,2.0,240,110\n"
    "2024,1,SF,REG,NYJ,-1.0,-1.0,180,90\n"
    "2024,2,NYJ,REG,TEN,6.0,0.0,260,120\n"
    "2024,2,TEN,REG,NYJ,-3.0,-1.0,150,70\n"
)


def test_player_weeks_parse_real_headers():
    rows = nflverse.parse_player_weeks(PLAYER_CSV)
    assert len(rows) == 3
    rodgers = [r for r in rows if r.player_id == "00-0023459"]
    assert len(rodgers) == 2
    assert rodgers[0].passing_yards == 167.0
    assert rodgers[0].team == "NYJ"
    # An empty EPA cell stays None. Zero would be a claim the model never made.
    assert rodgers[0].receiving_epa is None


def test_player_form_averages_only_games_played():
    data = nflverse.NflverseData(ok=True, players=nflverse.parse_player_weeks(PLAYER_CSV))
    forms = {f.player_id: f for f in nflverse.player_form(data, team="NYJ")}
    rodgers = forms["00-0023459"]
    assert rodgers.games == 2
    assert rodgers.pass_yards_pg == pytest.approx((167 + 240) / 2)
    wilson = forms["00-0036322"]
    assert wilson.games == 1
    assert wilson.rec_yards_pg == pytest.approx(88.0)


def test_player_form_last_n_uses_recent_games_only():
    data = nflverse.NflverseData(ok=True, players=nflverse.parse_player_weeks(PLAYER_CSV))
    forms = {f.player_id: f for f in nflverse.player_form(data, team="NYJ", last_n=1)}
    assert forms["00-0023459"].pass_yards_pg == pytest.approx(240.0)


def test_team_form_derives_defence_from_the_opponent_side():
    data = nflverse.NflverseData(ok=True, teams=nflverse.parse_team_weeks(TEAM_CSV))
    forms = nflverse.team_form(data, adjust_for_opponent=False)
    # NYJ produced 6.0 and 6.0 EPA; its opponents produced -2.0 and -4.0.
    assert forms["NYJ"].off_epa_per_game == pytest.approx(6.0)
    assert forms["NYJ"].def_epa_per_game == pytest.approx(-3.0)


def test_unparseable_csv_yields_no_rows_rather_than_raising():
    assert nflverse.parse_player_weeks("not,a,known,header\n1,2,3,4\n") == []
    assert nflverse.parse_team_weeks("") == []


def test_missing_season_is_reported_not_raised(monkeypatch):
    nflverse.reset_cache()

    async def missing(path: str):
        return None, "not published yet"

    monkeypatch.setattr(nflverse, "_download_csv", missing)
    data = asyncio.run(nflverse.load_season())
    assert data.ok is False
    assert data.players == [] and data.teams == []
    assert "not published" in data.note


def test_load_season_walks_back_to_a_published_year(monkeypatch):
    nflverse.reset_cache()
    good = nflverse.current_season() - 1

    async def by_year(path: str):
        if str(good) in path:
            return (PLAYER_CSV if "player" in path else TEAM_CSV), "ok"
        return None, "not published yet"

    monkeypatch.setattr(nflverse, "_download_csv", by_year)
    data = asyncio.run(nflverse.load_season())
    assert data.ok is True
    assert data.season == good


# ── CFBD ─────────────────────────────────────────────────────────────────────

def test_cfbd_without_a_key_reports_the_missing_config(monkeypatch):
    monkeypatch.setattr(cfbd, "api_key", lambda: "")
    result = asyncio.run(cfbd.sp_ratings(2024))
    assert result.ok is False
    assert result.configured is False
    assert cfbd.KEY_ENV_VAR in result.note
    assert result.rows == []


def test_cfbd_status_never_contains_the_key(monkeypatch):
    monkeypatch.setattr(cfbd, "api_key", lambda: "super-secret-value")
    report = cfbd.status()
    assert report["configured"] is True
    assert "super-secret-value" not in repr(report)


def test_cfbd_rejected_key_is_reported_as_a_key_problem(monkeypatch):
    cfbd.reset_cache()
    monkeypatch.setattr(cfbd, "api_key", lambda: "bad")

    async def denied(path, params):
        return None, f"{cfbd.KEY_ENV_VAR} rejected (HTTP 401)"

    monkeypatch.setattr(cfbd, "_get", denied)
    result = asyncio.run(cfbd.sp_ratings(2024))
    assert result.ok is False
    assert result.configured is True
    assert "rejected" in result.note


def test_cfbd_reads_both_field_spellings(monkeypatch):
    cfbd.reset_cache()
    monkeypatch.setattr(cfbd, "api_key", lambda: "k")

    async def body(path, params):
        return [
            {"team": "Georgia", "totalPPA": 0.62},
            {"school": "Alabama", "total_ppa": 0.55},
        ], "ok"

    monkeypatch.setattr(cfbd, "_get", body)
    result = asyncio.run(cfbd.returning_production(2024))
    got = {r.team: r.total_ppa for r in result.rows}
    assert got == {"Georgia": pytest.approx(0.62), "Alabama": pytest.approx(0.55)}


def test_cfbd_player_games_flatten_the_category_tree():
    body = [{
        "teams": [{
            "school": "Georgia",
            "categories": [{
                "name": "passing",
                "types": [
                    {"name": "YDS", "athletes": [{"id": "1", "name": "C. Beck", "stat": "310"}]},
                    {"name": "C/ATT", "athletes": [{"id": "1", "name": "C. Beck", "stat": "24/35"}]},
                    {"name": "TD", "athletes": [{"id": "1", "name": "C. Beck", "stat": "3"}]},
                ],
            }],
        }],
    }]
    rows = cfbd.parse_player_games(body)
    assert len(rows) == 1
    beck = rows[0]
    assert beck.passing_yards == 310.0
    assert (beck.completions, beck.attempts) == (24.0, 35.0)
    assert beck.team == "Georgia"


def test_cfbd_player_games_ignore_malformed_entries():
    assert cfbd.parse_player_games([None, {}, {"teams": None}]) == []
    assert cfbd.parse_player_games([{"teams": [{"categories": [{"types": "nope"}]}]}]) == []


# ── priors ───────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clean_priors():
    priors.reset()
    yield
    priors.reset()


def test_no_feed_means_the_static_rating_is_used_unchanged():
    elo, source = priors.prior_elo("nfl", "KC", 1720.0)
    assert elo == 1720.0
    assert source == "static"


def test_a_team_the_feed_does_not_cover_keeps_its_static_rating():
    priors._priors["nfl"] = priors.LeaguePriors(
        league="nfl", ok=True, source="test",
        teams={"KC": priors.TeamPrior("KC", points=5.0, games=17, source="nflverse-epa")},
    )
    elo, source = priors.prior_elo("nfl", "BUF", 1660.0)
    assert (elo, source) == (1660.0, "static")


def test_a_strong_feed_reading_raises_a_rating_within_the_cap():
    static = 1500.0
    priors._priors["nfl"] = priors.LeaguePriors(
        league="nfl", ok=True, source="test",
        teams={"KC": priors.TeamPrior("KC", points=40.0, games=17, source="nflverse-epa")},
    )
    elo, source = priors.prior_elo("nfl", "KC", static)
    per_elo = priors._points_per_elo("nfl")
    assert source == "nflverse-epa"
    assert elo > static
    # However extreme the input, the shift is capped in points of margin.
    assert (elo - static) * per_elo == pytest.approx(priors.MAX_SHIFT_POINTS)


def test_a_weak_feed_reading_lowers_a_rating():
    priors._priors["nfl"] = priors.LeaguePriors(
        league="nfl", ok=True, source="test",
        teams={"CAR": priors.TeamPrior("CAR", points=-12.0, games=17, source="nflverse-epa")},
    )
    elo, _ = priors.prior_elo("nfl", "CAR", 1430.0)
    assert elo < 1430.0


def test_one_game_moves_a_rating_far_less_than_a_full_season():
    def shift(games: int) -> float:
        priors.reset()
        priors._priors["nfl"] = priors.LeaguePriors(
            league="nfl", ok=True, source="test",
            teams={"KC": priors.TeamPrior("KC", points=10.0, games=games, source="nflverse-epa")},
        )
        return priors.prior_elo("nfl", "KC", 1500.0)[0] - 1500.0

    assert shift(1) < shift(6) < shift(17)


def test_a_failed_refresh_keeps_the_last_good_snapshot(monkeypatch):
    good = priors.LeaguePriors(
        league="nfl", ok=True, source="nflverse 2024",
        teams={"KC": priors.TeamPrior("KC", points=5.0, games=17, source="nflverse-epa")},
    )

    async def ok_load():
        return good

    async def failed_load():
        return priors.LeaguePriors(league="nfl", ok=False, note="upstream down")

    async def nothing():
        return priors.LeaguePriors(league="ncaaf", ok=False, note="no key")

    monkeypatch.setattr(priors, "_load_ncaaf", nothing)
    monkeypatch.setattr(priors, "_load_nfl", ok_load)
    asyncio.run(priors.refresh())
    monkeypatch.setattr(priors, "_load_nfl", failed_load)
    asyncio.run(priors.refresh())

    assert priors._priors["nfl"].ok is True
    assert priors.prior_elo("nfl", "KC", 1500.0)[1] == "nflverse-epa"


def test_priors_centre_on_the_teams_actually_matched():
    teams = {
        "KC": priors.TeamPrior("KC", points=12.0, games=17, source="s"),
        "CAR": priors.TeamPrior("CAR", points=6.0, games=17, source="s"),
    }
    centred = priors._centre(teams)
    assert centred["KC"].points == pytest.approx(3.0)
    assert centred["CAR"].points == pytest.approx(-3.0)


def test_nflverse_team_codes_map_onto_this_app_codes():
    # WSH is the only abbreviation the two sources disagree on.
    assert priors._nfl_code("WAS") == "WSH"
    assert priors._nfl_code("WAS") in nfl_data.NFL_TEAMS
    for code in ("KC", "GB", "LA", "LAC", "LV", "JAX"):
        assert priors._nfl_code(code) in nfl_data.NFL_TEAMS


def test_cfbd_school_names_map_onto_every_code_for_that_school():
    # Some schools carry two abbreviations (ESPN has used both for Georgia).
    # Both must receive the prior, or the alias silently runs on stale numbers.
    assert set(priors._ncaaf_codes("Georgia")) == {"GA", "UGA"}
    assert priors._ncaaf_codes("Ohio State") == ["OSU"]
    assert priors._ncaaf_codes("Not A Real School") == []
    for codes in priors._NCAAF_BY_NAME.values():
        for code in codes:
            assert code in ncaaf_data.NCAAF_TEAMS


def test_every_ncaaf_team_is_reachable_by_its_school_name():
    reachable = {c for codes in priors._NCAAF_BY_NAME.values() for c in codes}
    assert reachable == set(ncaaf_data.NCAAF_TEAMS)


def test_ncaaf_priors_need_a_key_and_say_so(monkeypatch):
    monkeypatch.setattr(cfbd, "api_key", lambda: "")
    result = asyncio.run(priors._load_ncaaf())
    assert result.ok is False
    assert cfbd.KEY_ENV_VAR in result.note


def test_status_reports_the_last_load_not_merely_configuration():
    priors._priors["nfl"] = priors.LeaguePriors(
        league="nfl", ok=True, source="nflverse 2024", note="ok",
        fetched_at="2026-09-08T00:00:00+00:00",
        teams={"KC": priors.TeamPrior("KC", points=5.0, games=17, source="nflverse-epa")},
    )
    report = priors.status()
    assert report["leagues"]["nfl"]["ok"] is True
    assert report["leagues"]["nfl"]["teams"] == 1
    assert report["leagues"]["nfl"]["fetched_at"]


# ── strength of schedule ─────────────────────────────────────────────────────

def test_opponent_adjustment_rewards_the_harder_schedule():
    """
    Two offences post identical raw EPA. One did it against the league's best
    defence, the other against its worst. They must not come out equal.
    """
    games = [
        # STRONG_D concedes little to everyone else; WEAK_D concedes plenty.
        ("A", "STRONG_D", 5.0), ("B", "WEAK_D", 5.0),
        ("C", "STRONG_D", -8.0), ("D", "STRONG_D", -7.0),
        ("C", "WEAK_D", 9.0), ("D", "WEAK_D", 8.0),
        ("STRONG_D", "C", 1.0), ("STRONG_D", "D", 1.0), ("STRONG_D", "A", 1.0),
        ("WEAK_D", "C", 1.0), ("WEAK_D", "D", 1.0), ("WEAK_D", "B", 1.0),
    ]
    offense, defence = nflverse.opponent_adjust(games)
    assert offense["A"] > offense["B"]
    # And the defence that conceded less is rated better (lower EPA allowed).
    assert defence["STRONG_D"] < defence["WEAK_D"]


def test_opponent_adjusted_ratings_are_centred_on_zero():
    games = [("A", "B", 6.0), ("B", "A", -2.0), ("A", "C", 4.0),
             ("C", "A", 0.0), ("B", "C", 1.0), ("C", "B", 3.0)]
    offense, defence = nflverse.opponent_adjust(games)
    assert sum(offense.values()) == pytest.approx(0.0, abs=1e-9)
    assert sum(defence.values()) == pytest.approx(0.0, abs=1e-9)


def test_opponent_adjustment_on_no_games_is_empty_not_an_error():
    offense, defence = nflverse.opponent_adjust([])
    assert offense == {} and defence == {}


def test_team_form_marks_whether_it_adjusted_for_opponent():
    data = nflverse.NflverseData(ok=True, teams=nflverse.parse_team_weeks(TEAM_CSV))
    adjusted = nflverse.team_form(data)
    raw = nflverse.team_form(data, adjust_for_opponent=False)
    assert all(f.opponent_adjusted for f in adjusted.values())
    assert not any(f.opponent_adjusted for f in raw.values())


def test_status_flags_a_season_that_is_not_the_current_one(monkeypatch):
    nflverse.reset_cache()
    old = nflverse.current_season() - 1

    async def last_year_only(path: str):
        if str(old) in path:
            return (PLAYER_CSV if "player" in path else TEAM_CSV), "ok"
        return None, "not published yet"

    monkeypatch.setattr(nflverse, "_download_csv", last_year_only)
    asyncio.run(nflverse.load_season())
    report = nflverse.status()
    assert report["current_season"] == nflverse.current_season()
    assert report["loaded"][0]["is_current_season"] is False
    assert str(old) in report["note"]
    nflverse.reset_cache()
