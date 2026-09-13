"""
Quarterback change as a points adjustment.

Two things matter as much as the arithmetic. It must stay silent when the
usual starter is playing — otherwise it nudges every projection instead of the
ones that have actually changed — and it must not double-count a quarterback
whose play is already baked into his team's rating.
"""
from __future__ import annotations

import pytest

from src.predict import quarterback as qb

STATS = """player_name,position,season_type,team,attempts,passing_epa
D.Maye,QB,REG,NE,492,166.0
J.Backup,QB,REG,NE,40,-30.0
C.Ward,QB,REG,TEN,540,-26.0
A.Average,QB,REG,BUF,500,17.0
"""

DEPTH = """dt,team,player_name,pos_abb,pos_rank
2026-09-01T00:00:00Z,NE,Drake Maye,QB,1
2026-09-01T00:00:00Z,NE,Josh Backup,QB,2
2026-09-01T00:00:00Z,TEN,Cam Ward,QB,1
2026-09-01T00:00:00Z,BUF,Andy Average,QB,1
"""


@pytest.fixture
def feeds():
    return (
        qb.parse_qb_ratings(STATS),
        qb.parse_expected_starters(STATS),
        qb.parse_depth_chart_starters(DEPTH),
    )


def test_nothing_is_claimed_when_the_usual_starter_is_playing(feeds):
    ratings, expected, depth = feeds
    # NE's rating was earned with Maye and Maye is starting. Adding his value
    # on top would count the same player twice.
    assert qb.compute_change("NE", ratings, expected, depth) is None
    assert qb.compute_change("TEN", ratings, expected, depth) is None


def test_a_backup_starting_is_a_downgrade_worth_points(feeds):
    ratings, expected, depth = feeds
    depth = {**depth, "NE": qb._norm("Josh Backup")}
    change = qb.compute_change("NE", ratings, expected, depth)
    assert change is not None
    assert change.points < 0
    assert "Backup" in change.detail or "backup" in change.detail
    assert change.expected == qb._norm("D.Maye")


def test_the_swing_is_capped_however_extreme_the_arithmetic(feeds):
    ratings, expected, depth = feeds
    wild = {**ratings, qb._norm("J.Backup"): qb.QbRating(
        name="j.backup", team="NE", attempts=600, points=-99.0)}
    depth = {**depth, "NE": qb._norm("Josh Backup")}
    change = qb.compute_change("NE", wild, expected, depth)
    assert change is not None
    assert change.points >= -qb.MAX_SWING_POINTS


def test_an_unrated_arm_is_treated_as_below_average_not_as_neutral(feeds):
    ratings, expected, depth = feeds
    depth = {**depth, "NE": "n.obody"}
    change = qb.compute_change("NE", ratings, expected, depth)
    assert change is not None and change.points < 0


def test_a_team_with_no_established_starter_claims_nothing(feeds):
    ratings, _expected, depth = feeds
    # Nobody has thrown enough for "replaced" to mean anything.
    assert qb.compute_change("NE", ratings, {}, depth) is None


def test_ratings_are_shrunk_so_a_hot_handful_of_throws_leads_nothing():
    stats = STATS + "M.Fluke,QB,REG,GB,35,28.0\n"
    ratings = qb.parse_qb_ratings(stats)
    fluke = ratings[qb._norm("M.Fluke")]
    maye = ratings[qb._norm("D.Maye")]
    # Raw EPA per attempt has the 35-attempt man far clear of everyone; after
    # shrinkage the season-long starter is ahead, which is the point.
    assert fluke.points < maye.points


def test_ratings_are_expressed_in_points_of_margin_and_stay_plausible():
    ratings = qb.parse_qb_ratings(STATS)
    for r in ratings.values():
        assert -12.0 < r.points < 12.0, (r.name, r.points)


def test_only_first_string_rows_are_kept_from_a_depth_chart():
    assert qb.is_first_string_qb({"pos_abb": "QB", "pos_rank": "1"})
    assert not qb.is_first_string_qb({"pos_abb": "QB", "pos_rank": "2"})
    assert not qb.is_first_string_qb({"pos_abb": "RB", "pos_rank": "1"})


def test_the_newest_depth_chart_wins():
    chart = (
        "dt,team,player_name,pos_abb,pos_rank\n"
        "2026-08-01T00:00:00Z,NE,Old Guy,QB,1\n"
        "2026-09-01T00:00:00Z,NE,New Guy,QB,1\n"
    )
    assert qb.parse_depth_chart_starters(chart)["NE"] == qb._norm("New Guy")


def test_a_name_matches_across_the_two_feeds_that_spell_it_differently():
    # Weekly stats say "D.Maye"; depth charts say "Drake Maye".
    assert qb._norm("D.Maye") == qb._norm("Drake Maye")


# ─── Never in front of a page render ──────────────────────────────────────────

def test_a_cold_cache_answers_immediately_instead_of_downloading(monkeypatch):
    """
    The regression that made the site slow on a Saturday.

    A board asks for this once per NFL game and every deploy starts cold. With
    no guard, eight concurrent requests each downloaded the same several
    megabytes — seventeen seconds instead of four, on a 512 MB machine.
    """
    import asyncio

    calls = {"n": 0}

    async def never_finishes():
        calls["n"] += 1
        await asyncio.sleep(30)

    qb.reset_cache()
    monkeypatch.setattr(qb, "_load", never_finishes)

    async def run():
        return await asyncio.wait_for(
            asyncio.gather(*(qb.changes_for("KC", "BAL") for _ in range(8))),
            timeout=2.0,
        )

    results = asyncio.run(run())
    # Every caller is answered without waiting on the feed...
    assert results == [(None, None)] * 8
    # ...and they did not each start their own download.
    assert calls["n"] <= 1


def test_stale_data_keeps_being_served_while_it_refreshes(monkeypatch):
    import asyncio
    import time as _time

    ratings = qb.parse_qb_ratings(STATS)
    expected = qb.parse_expected_starters(STATS)
    depth = {**qb.parse_depth_chart_starters(DEPTH), "NE": qb._norm("Josh Backup")}

    qb.reset_cache()
    # Present, but older than the TTL.
    qb._cache["qb"] = (_time.monotonic() - qb.TTL_SECONDS - 1, (ratings, expected, depth))

    async def never_finishes():
        await asyncio.sleep(30)

    monkeypatch.setattr(qb, "_load", never_finishes)

    async def run():
        return await asyncio.wait_for(qb.changes_for("NE", "TEN"), timeout=2.0)

    home, _away = asyncio.run(run())
    # Out-of-date beats nothing at all, and it still does not block.
    assert home is not None and home.points < 0


def test_a_season_that_exists_but_is_empty_is_not_used():
    """
    A season's file is published the day the season opens.

    In September 2026 it held six quarterbacks and nobody with enough attempts
    to have established anything — and taking the newest file that merely
    existed silently switched the adjustment off for months.
    """
    opening_week = (
        "player_name,position,season_type,team,attempts,passing_epa\n"
        "A.Rookie,QB,REG,NE,12,3.0\n"
    )
    assert len(qb.parse_expected_starters(opening_week)) < qb.MIN_ESTABLISHED_TEAMS
    # Where a full season clears the bar comfortably.
    full = "".join(
        f"Q{i}.Starter,QB,REG,T{i},400,20.0\n" for i in range(qb.MIN_ESTABLISHED_TEAMS)
    )
    header = "player_name,position,season_type,team,attempts,passing_epa\n"
    assert len(qb.parse_expected_starters(header + full)) >= qb.MIN_ESTABLISHED_TEAMS
