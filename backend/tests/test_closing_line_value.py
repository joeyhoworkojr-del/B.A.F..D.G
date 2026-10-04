"""
Closing line value, and the line it is measured from.

CLV was not merely missing, it was zero by construction. `market_spread` is
refreshed on every snapshot, and grading copied that refreshed value into
`closing_spread` — so the "closing" line was the same number as the
"recommended" line, every time, and the difference between them was always
nought.

Fixing it needs two lines kept, not one: the line we recommended at, frozen,
and the line as it stands now, moving. These pin that.
"""
from __future__ import annotations

import pytest

from src.track import ledger


@pytest.fixture(autouse=True)
def clean(tmp_path, monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("LEDGER_PATH", str(tmp_path / "clv.db"))
    ledger.reset()
    yield
    ledger.reset()


def snapshot(*, spread, total, side="home", total_side="over", event="nfl:1"):
    ledger.record_pregame(
        event_id=event, league="nfl", kickoff="2026-10-04T17:00Z",
        home="Buffalo Bills", away="Miami Dolphins",
        model_home_prob=0.63, model_total=48.3,
        book_home_prob=0.62, market_spread=spread, market_total=total,
        home_code="BUF", away_code="MIA",
        consensus_home_prob=0.63, model_version=ledger_version(),
        pick_spread_side=side, pick_total_side=total_side,
    )


def ledger_version():
    from src.api.routes.predictions import MODEL_VERSION
    return MODEL_VERSION


def row(event="nfl:1"):
    return ledger.get_snapshot(event) or {}


# ─── The line we recommended at must not move ────────────────────────────────

def test_the_opening_line_is_frozen_while_the_market_keeps_moving():
    snapshot(spread=-3.5, total=46.5)
    snapshot(spread=-4.0, total=47.0)
    snapshot(spread=-4.5, total=47.5)

    r = row()
    assert r["opening_spread"] == -3.5, "the first line on file is the recommendation"
    assert r["opening_total"] == 46.5
    # ...and the current line is still tracked, because the page shows both.
    assert r["market_spread"] == -4.5
    assert r["market_total"] == 47.5


def test_the_side_taken_is_frozen_with_the_line():
    # A later snapshot that would flip the lean must not rewrite history: the
    # record is of what was recommended, not of what is recommended now.
    snapshot(spread=-3.5, total=46.5, side="home", total_side="over")
    snapshot(spread=-9.0, total=40.0, side="away", total_side="under")
    r = row()
    assert r["pick_spread_side"] == "home"
    assert r["pick_total_side"] == "over"


def test_closing_line_value_is_no_longer_zero_by_construction():
    snapshot(spread=-3.5, total=46.5, side="home")
    snapshot(spread=-4.5, total=47.5, side="home")   # the market moved our way
    assert ledger.grade("nfl:1", 27, 20) is True

    r = row()
    assert r["opening_spread"] == -3.5
    assert r["closing_spread"] == -4.5
    # Backed the home team at -3.5 into a -4.5 close: a point in hand.
    assert ledger.clv_points(r) == 1.0


def test_backing_the_dog_into_the_same_move_loses_that_point():
    snapshot(spread=-3.5, total=46.5, side="away")
    snapshot(spread=-4.5, total=47.5, side="away")
    ledger.grade("nfl:1", 27, 20)
    assert ledger.clv_points(row()) == -1.0


def test_no_opening_line_is_reported_as_unknown_not_as_no_edge():
    # Averaging an unknown in as zero would quietly drag the figure towards
    # "the model finds nothing", which is a different claim from "we cannot
    # tell for this game".
    assert ledger.clv_points({"closing_spread": -4.5, "pick_spread_side": "home"}) is None
    assert ledger.clv_points({"opening_spread": -3.5, "pick_spread_side": "home"}) is None
    assert ledger.clv_points({"opening_spread": -3.5, "closing_spread": -4.5}) is None


# ─── The spread and total records ────────────────────────────────────────────

def test_the_spread_record_is_graded_against_the_line_we_took():
    snapshot(spread=-3.5, total=46.5, side="home", total_side="over")
    snapshot(spread=-7.0, total=52.0, side="home", total_side="over")
    ledger.grade("nfl:1", 24, 20)        # home by 4

    perf = ledger.performance()
    # -3.5 covered by a 4-point win. Grading against the -7 it drifted to
    # would have called the same recommendation a loss.
    assert perf["ats"]["wins"] == 1
    assert perf["ats"]["losses"] == 0


def test_a_push_is_not_a_loss():
    snapshot(spread=-3.0, total=47.0, side="home", total_side="under")
    ledger.grade("nfl:1", 23, 20)        # home by exactly 3, total exactly 43

    perf = ledger.performance()
    assert perf["ats"]["pushes"] == 1
    assert perf["ats"]["wins"] == perf["ats"]["losses"] == 0
    # A push leaves the denominator alone rather than counting against us.
    assert perf["ats"]["win_rate"] is None


def test_the_total_record_is_separate_from_the_spread_record():
    # One call right and the other wrong on the same game. A single blended
    # record would hide which of the two the model is actually good at.
    snapshot(spread=-3.5, total=46.5, side="home", total_side="over")
    ledger.grade("nfl:1", 24, 20)        # home -3.5 covers; total 44 is under

    perf = ledger.performance()
    assert perf["ats"]["wins"] == 1
    assert perf["totals"]["losses"] == 1


def test_clv_reports_its_own_denominator():
    snapshot(spread=-3.5, total=46.5, side="home")
    snapshot(spread=-4.5, total=47.5, side="home")
    ledger.grade("nfl:1", 27, 20)

    perf = ledger.performance()
    assert perf["clv_tracked"] == 1
    assert perf["clv_beat_close"] == 1
    assert perf["avg_clv_points"] == 1.0


def test_an_empty_ledger_claims_nothing():
    perf = ledger.performance()
    assert perf["avg_clv_points"] is None
    assert perf["clv_tracked"] == 0
    assert perf["ats"]["win_rate"] is None
    assert perf["totals"]["win_rate"] is None
