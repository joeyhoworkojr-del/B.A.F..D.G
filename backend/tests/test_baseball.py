"""MLB Poisson-grid engine tests."""
from __future__ import annotations

from src.predict.adjustments import Adjustment
from src.predict.baseball import expected_runs, predict_mlb_game


def test_probabilities_complement() -> None:
    p = predict_mlb_game("LAD", "COL", 1625, 1400)
    assert abs(p.home_win_prob + p.away_win_prob - 1.0) < 1e-9
    assert abs(p.over_prob + p.under_prob - 1.0) < 1e-9


def test_better_team_favoured() -> None:
    p = predict_mlb_game("LAD", "CHW", 1625, 1425)
    assert p.home_win_prob > 0.60


def test_home_edge_exists() -> None:
    # Use a park-factor-neutral home team so only the home bump differs
    h, _ = expected_runs("DET", "CLE")
    h_neutral, _ = expected_runs("DET", "CLE", neutral_site=True)
    assert h > h_neutral


def test_coors_inflates_totals() -> None:
    coors = predict_mlb_game("COL", "SD", 1400, 1570)
    sea = predict_mlb_game("SEA", "SD", 1565, 1570)
    assert coors.total_points_estimate > sea.total_points_estimate + 1.5


def test_totals_sane_range() -> None:
    p = predict_mlb_game("NYY", "BOS", 1590, 1545)
    assert 7.0 < p.total_points_estimate < 12.5
    assert p.total_line is not None and p.total_line > 0


def test_ace_out_shifts_win_prob() -> None:
    base = predict_mlb_game("PIT", "CHC", 1470, 1565)
    ace_out = predict_mlb_game(
        "PIT", "CHC", 1470, 1565,
        adjustments=[Adjustment(
            label="ace out", detail="", source="lineup", away_xg_mult=1.0,
            home_xg_mult=1.0, home_pts_delta=0.0, away_pts_delta=0.9,
        )],
    )
    assert ace_out.home_win_prob < base.home_win_prob - 0.03


def test_over_by_line_decreasing() -> None:
    p = predict_mlb_game("CIN", "COL", 1510, 1400)
    lines = sorted(float(k) for k in p.over_by_line)
    probs = [p.over_by_line[f"{ln}"] for ln in lines]
    assert all(a >= b for a, b in zip(probs, probs[1:]))
