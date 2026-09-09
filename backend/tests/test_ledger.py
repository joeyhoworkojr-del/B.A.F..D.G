"""Prediction ledger + accuracy scorecard tests."""
from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.main import app
from src.track import ledger

client = TestClient(app)


def _snap(eid: str = "nfl:1", model: float = 0.70, book: float = 0.60, crowd: float = 0.65) -> None:
    ledger.record_pregame(
        event_id=eid, league="nfl", kickoff="2026-07-04T20:00Z",
        home="Chiefs", away="Bills",
        model_home_prob=model, model_total=47.0,
        book_home_prob=book, crowd_home_prob=crowd,
        market_spread=-3.5, market_total=47.5,
    )


def test_snapshot_grade_and_brier() -> None:
    _snap()
    assert ledger.grade("nfl:1", 27, 20) is True     # home won
    s = ledger.accuracy_summary()
    assert s["overall"]["games_graded"] == 1
    assert abs(s["overall"]["model"]["brier"] - (0.70 - 1) ** 2) < 1e-9
    assert abs(s["overall"]["book"]["brier"] - (0.60 - 1) ** 2) < 1e-9
    assert s["overall"]["model"]["winner_hit_rate"] == 1.0
    assert s["by_league"]["nfl"]["games_graded"] == 1


def test_pregame_upsert_frozen_after_grading() -> None:
    _snap(model=0.70)
    _snap(model=0.75)                                 # line moved pre-game → updates
    ledger.grade("nfl:1", 20, 27)                     # away won
    _snap(model=0.99)                                 # post-grade snapshot must NOT overwrite
    rows = ledger.recent_graded()
    assert len(rows) == 1
    assert abs(rows[0]["model_home_prob"] - 0.75) < 1e-9
    assert rows[0]["home_won"] == 0


def test_tie_is_not_graded() -> None:
    _snap(eid="cfl:9")
    assert ledger.grade("cfl:9", 24, 24) is False
    assert ledger.accuracy_summary()["overall"]["games_graded"] == 0
    assert ledger.accuracy_summary()["pending"] == 1


def test_grade_without_snapshot_is_noop() -> None:
    assert ledger.grade("mlb:404", 5, 3) is False


def test_accuracy_endpoint_shape() -> None:
    _snap()
    ledger.grade("nfl:1", 30, 10)
    resp = client.get("/api/v1/accuracy")
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall"]["games_graded"] == 1
    assert data["overall"]["model"]["n"] == 1
    assert len(data["recent"]) == 1
    assert "note" in data
    perf = data["performance"]
    assert perf["total_picks"] == 1 and perf["win_rate"] == 1.0
    assert perf["profit_units"] is not None and perf["profit_units"] > 0
    assert len(perf["series"]) == 1


def test_performance_units_math() -> None:
    # Model picks home (0.70) at book fair 0.60 → win pays 1/0.6 − 1 = 0.6667
    _snap(eid="nfl:10", model=0.70, book=0.60)
    ledger.grade("nfl:10", 30, 10)
    # Model picks home (0.55) at book 0.65 → home loses → −1 unit
    _snap(eid="nfl:11", model=0.55, book=0.65)
    ledger.grade("nfl:11", 10, 30)
    perf = ledger.performance()
    assert perf["total_picks"] == 2
    assert abs(perf["profit_units"] - (1 / 0.6 - 1 - 1)) < 0.01
    assert perf["win_rate"] == 0.5
    assert len(perf["series"]) == 2


def test_performance_settles_on_consensus_pick() -> None:
    # Raw model leans home (0.65) but the market-anchored consensus leans away
    # (home 0.40). The consensus pick (away) — what the product recommends —
    # should drive win rate and P/L; the raw model is kept only for Brier.
    ledger.record_pregame(
        event_id="nfl:c1", league="nfl", kickoff="2026-07-04T20:00Z",
        home="Chiefs", away="Bills", model_home_prob=0.65,
        book_home_prob=0.45, consensus_home_prob=0.40,
    )
    ledger.grade("nfl:c1", 10, 24)          # away won
    perf = ledger.performance()
    assert perf["win_rate"] == 1.0          # consensus picked away, away won
    assert perf["profit_units"] > 0


def test_page_view_never_writes_a_prediction() -> None:
    """Reading the slate must not snapshot — that is the scheduler's job."""
    from src.ingest.espn import Scoreboard, _parse_event
    from tests.test_espn_today import SAMPLE_EVENT, _patch_poly

    pre = {**SAMPLE_EVENT, "status": {"type": {"state": "pre", "shortDetail": "8:15 PM"}}}
    board_pre = Scoreboard(league="nfl", games=[_parse_event("nfl", pre)], fetched_at="x")
    with patch("src.api.routes.predictions.fetch_scoreboard", return_value=board_pre), _patch_poly():
        assert client.get("/api/v1/today/nfl").status_code == 200
    assert ledger.accuracy_summary()["pending"] == 0     # nothing recorded


def test_scheduled_snapshot_records_then_grades() -> None:
    """The server-side job snapshots pre-game; a later final grades it."""
    import asyncio

    from src.api.routes.predictions import snapshot_pregame
    from src.ingest.espn import Scoreboard, _parse_event
    from tests.test_espn_today import SAMPLE_EVENT, _patch_poly

    pre = {**SAMPLE_EVENT, "status": {"type": {"state": "pre", "shortDetail": "8:15 PM"}}}
    board_pre = Scoreboard(league="nfl", games=[_parse_event("nfl", pre)], fetched_at="x")
    with patch("src.api.routes.predictions.fetch_scoreboard", return_value=board_pre), _patch_poly():
        assert asyncio.run(snapshot_pregame("nfl")) == 1
    assert ledger.accuracy_summary()["pending"] == 1

    row = ledger.get_snapshot("nfl:401547401")
    assert row is not None
    assert row["model_version"]                      # provenance is recorded
    assert row["book_source"] == "ESPN BET"

    post = {**SAMPLE_EVENT, "status": {"type": {"state": "post", "shortDetail": "Final"}}}
    board_post = Scoreboard(league="nfl", games=[_parse_event("nfl", post)], fetched_at="x")
    with patch("src.api.routes.predictions.fetch_scoreboard", return_value=board_post), _patch_poly():
        assert client.get("/api/v1/today/nfl").status_code == 200

    summary = ledger.accuracy_summary()
    assert summary["overall"]["games_graded"] == 1
    # Sample game: KC 21-17 → home won; book prob was recorded no-vig
    row = ledger.recent_graded()[0]
    assert row["home_won"] == 1
    assert row["book_home_prob"] is not None and 0.5 < row["book_home_prob"] < 0.75
    assert row["closing_spread"] == -3.5              # line frozen at grade time


def test_newer_model_cannot_rewrite_an_open_prediction() -> None:
    ledger.record_pregame(
        event_id="nfl:v1", league="nfl", kickoff="2026-07-04T20:00Z",
        home="Chiefs", away="Bills", model_home_prob=0.61, model_version="v1",
    )
    ledger.record_pregame(
        event_id="nfl:v1", league="nfl", kickoff="2026-07-04T20:00Z",
        home="Chiefs", away="Bills", model_home_prob=0.99, model_version="v2",
    )
    row = ledger.get_snapshot("nfl:v1")
    assert row["model_home_prob"] == 0.61 and row["model_version"] == "v1"


def test_accuracy_summary_declares_a_pregame_scope():
    """
    Two different things get called "the model's accuracy". The summary has to
    say which one it is measuring, so the UI can label them apart.
    """
    summary = ledger.accuracy_summary()
    assert summary["scope"] == "pregame"
    assert summary["live_record_available"] is False
    assert "not" in summary["live_note"].lower()


def test_graded_rows_report_the_model_versions_behind_them():
    ledger.reset()
    ledger.record_pregame(
        event_id="nfl:900", league="nfl", kickoff="2026-09-05T18:00:00+00:00",
        home="KC", away="BUF", model_home_prob=0.6,
        model_version="test-1.0",
    )
    ledger.grade("nfl:900", home_score=24, away_score=20)
    assert ledger.accuracy_summary()["model_versions"] == ["test-1.0"]


# ── the Results page must survive rows written by an older schema ───────────

def test_performance_skips_a_row_it_cannot_settle_rather_than_raising():
    """
    A durable store accumulates rows across schema changes. One row written
    before `consensus_home_prob` existed used to raise KeyError here — and
    because this was the only ledger call /accuracy did not guard, that took
    the entire Results page down with a 500.
    """
    from unittest.mock import patch
    from src.track import ledger as ledger_mod

    legacy = {"model_home_prob": 0.6, "home_won": 1, "book_home_prob": 0.55,
              "graded_at": "2026-01-01"}
    unsettleable = {"graded_at": "2026-01-02"}

    class FakeStore:
        def rows(self, graded=True):
            return [legacy, unsettleable]

    with patch.object(ledger_mod, "_get_store", lambda: FakeStore()):
        result = ledger_mod.performance()

    assert result["total_picks"] == 1          # the unsettleable row is skipped
    assert result["win_rate"] == 1.0           # and not counted in the denominator
    assert result["profit_units"] is not None


def test_performance_returns_an_empty_record_when_storage_fails():
    """A page whose job is showing the record should show an empty one, not 500."""
    from unittest.mock import patch
    from src.track import ledger as ledger_mod

    class BrokenStore:
        def rows(self, graded=True):
            raise RuntimeError("storage is unreachable")

    with patch.object(ledger_mod, "_get_store", lambda: BrokenStore()):
        result = ledger_mod.performance()

    assert result["total_picks"] == 0
    assert result["series"] == []


def test_the_accuracy_endpoint_survives_a_ratings_failure():
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    from src.api.main import app
    from src.track import ratings as ratings_mod

    with patch.object(ratings_mod, "reconcile", side_effect=RuntimeError("boom")):
        response = TestClient(app).get("/api/v1/accuracy")

    assert response.status_code == 200
    assert "performance" in response.json()


def test_a_row_written_before_a_column_existed_does_not_break_the_record():
    """
    The Results page went blank in production over this.

    A stored row is whatever the build that wrote it wrote. When a later build
    reads a column those rows never had, subscripting raises — and because
    `accuracy_summary` was the one ledger call without a failure guard, a
    single old row took down the whole page whose job is showing the record.
    """
    class PartialStore:
        backend = "redis"
        durable = True

        def rows(self, graded=True):
            return [{
                "league": "nfl", "event_id": "1", "home_won": 1,
                "model_home_prob": 0.6, "model_version": "2026.09.1",
                # book_home_prob and crowd_home_prob simply are not here.
            }]

        def count(self, graded=False):
            return 0

    with patch.object(ledger, "_get_store", lambda: PartialStore()):
        summary = ledger.accuracy_summary()

    # The row that can be scored is scored...
    assert summary["overall"]["games_graded"] == 1
    assert summary["overall"]["model"]["n"] == 1
    # ...and the ones with no data report nothing rather than a made-up zero.
    assert summary["overall"]["book"] is None
    assert summary["overall"]["crowd"] is None


def test_unreadable_storage_says_so_instead_of_reporting_an_empty_record():
    """
    An empty scorecard and an unreadable one look identical, and only one of
    them is a claim about how the model has done.
    """
    class BrokenStore:
        @property
        def backend(self):
            raise RuntimeError("storage is unreachable")

        @property
        def durable(self):
            raise RuntimeError("storage is unreachable")

        def rows(self, graded=True):
            raise RuntimeError("storage is unreachable")

        def count(self, graded=False):
            raise RuntimeError("storage is unreachable")

    with patch.object(ledger, "_get_store", lambda: BrokenStore()):
        summary = ledger.accuracy_summary()

    assert summary["unavailable"] is True
    assert summary["overall"]["games_graded"] == 0
    # The fallback runs precisely when something is already broken, so it must
    # not itself depend on the storage that just failed.
    assert summary["storage_backend"] == "unavailable"
    assert summary["storage_durable"] is False


def test_the_results_endpoint_still_answers_when_storage_is_down():
    class BrokenStore:
        @property
        def backend(self):
            raise RuntimeError("down")

        @property
        def durable(self):
            raise RuntimeError("down")

        def rows(self, graded=True):
            raise RuntimeError("down")

        def count(self, graded=False):
            raise RuntimeError("down")

    with patch.object(ledger, "_get_store", lambda: BrokenStore()):
        response = client.get("/api/v1/accuracy")

    assert response.status_code == 200
    body = response.json()
    assert body["overall"]["games_graded"] == 0
    assert body["performance"]["total_picks"] == 0
    assert body["recent"] == []
