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


def test_today_flow_populates_ledger() -> None:
    """Pre-game slate snapshots; a later final grades it."""
    from src.ingest.espn import Scoreboard, _parse_event
    from tests.test_espn_today import SAMPLE_EVENT, _patch_poly

    pre = {**SAMPLE_EVENT, "status": {"type": {"state": "pre", "shortDetail": "8:15 PM"}}}
    board_pre = Scoreboard(league="nfl", games=[_parse_event("nfl", pre)], fetched_at="x")
    with patch("src.api.routes.predictions.fetch_scoreboard", return_value=board_pre), _patch_poly():
        assert client.get("/api/v1/today/nfl").status_code == 200
    assert ledger.accuracy_summary()["pending"] == 1

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
