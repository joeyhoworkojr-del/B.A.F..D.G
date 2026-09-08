"""
The expected-points model and the predictive live projection.

The point of this model is that the number moves *before* the score does, so
these tests are mostly about ordering: better game states must be worth more,
and the projection must respond to the state rather than only to the
scoreboard. The absolute values are checked against published NFL
expected-points figures at the anchors the curve is calibrated to.
"""
from __future__ import annotations

import pytest

from src.predict import expected_points as ep
from src.predict.expected_points import GameState
from src.predict.gridiron import live_projection
from src.track import win_history


# ── the curve ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("yard_line,expected,tolerance", [
    (20, 0.6, 0.25),    # own 20, 1st & 10
    (50, 2.0, 0.25),    # midfield
    (80, 4.2, 0.35),    # opponent's 20
    (99, 6.0, 0.5),     # goal line
])
def test_first_and_ten_matches_published_values(yard_line, expected, tolerance):
    assert ep.expected_points(GameState(yard_line, 1, 10)) == pytest.approx(expected, abs=tolerance)


def test_field_position_is_worth_more_the_closer_it_gets():
    values = [ep.expected_points(GameState(y, 1, 10)) for y in (10, 30, 50, 70, 90)]
    assert values == sorted(values)


def test_being_pinned_on_your_own_goal_line_is_worth_less_than_nothing():
    assert ep.expected_points(GameState(1, 1, 10)) < 0


def test_a_later_down_is_worth_less_at_the_same_spot():
    at_opp_20 = [ep.expected_points(GameState(80, d, 10)) for d in (1, 2, 3, 4)]
    assert at_opp_20 == sorted(at_opp_20, reverse=True)


def test_distance_matters_within_a_down():
    short = ep.expected_points(GameState(80, 3, 1))
    long = ep.expected_points(GameState(80, 3, 15))
    assert short > long


def test_the_specs_headline_comparison():
    """Own 20 on 3rd & 12 must be worth far less than opp 5 on 1st & goal."""
    backed_up = ep.expected_points(GameState(20, 3, 12))
    goal_line = ep.expected_points(GameState(95, 1, 5))
    assert goal_line - backed_up > 4.0


def test_first_and_goal_beats_fourth_and_goal_from_the_same_spot():
    assert ep.expected_points(GameState(95, 1, 5)) > ep.expected_points(GameState(95, 4, 5))


def test_goal_to_go_is_harsher_than_the_same_distance_at_midfield():
    """
    5 yards to go from the 5 is the whole remaining field; 5 to go from
    midfield is half a series. The first must cost more.
    """
    goal_to_go_cost = (
        ep.expected_points(GameState(95, 1, 5)) - ep.expected_points(GameState(95, 4, 5))
    )
    midfield_cost = (
        ep.expected_points(GameState(50, 1, 5)) - ep.expected_points(GameState(50, 4, 5))
    )
    assert goal_to_go_cost > midfield_cost


def test_fourth_down_in_range_is_floored_by_the_field_goal():
    """4th & 12 on the opponent's 20 is a routine three points, not a disaster."""
    assert ep.expected_points(GameState(80, 4, 12)) > 2.0


def test_field_goal_probability_falls_with_distance():
    close = ep.field_goal_probability(97)     # ~20 yards
    medium = ep.field_goal_probability(80)    # ~37 yards
    far = ep.field_goal_probability(55)       # ~62 yards
    assert close > medium > far
    assert close > 0.9
    assert far < 0.3


def test_college_kickers_are_modelled_as_less_reliable_from_distance():
    assert ep.field_goal_probability(65, "ncaaf") < ep.field_goal_probability(65, "nfl")


def test_possession_value_is_about_zero_after_a_touchback():
    assert ep.possession_value(GameState(25, 1, 10)) == pytest.approx(0.0, abs=0.01)


def test_an_unusable_state_is_worth_nothing_rather_than_guessed():
    assert ep.possession_value(GameState(-5)) == 0.0
    assert ep.possession_value(GameState(140)) == 0.0
    assert ep.describe(GameState(-5)) == ""


def test_goal_to_go_and_red_zone_are_derived_not_asserted():
    assert GameState(95, 1, 5).goal_to_go is True
    assert GameState(95, 1, 5).red_zone is True
    assert GameState(50, 1, 10).goal_to_go is False
    assert GameState(50, 1, 10).red_zone is False
    # 1st & 10 at the opponent's 15 is in the red zone but not goal to go.
    assert GameState(85, 1, 10).red_zone is True
    assert GameState(85, 1, 10).goal_to_go is False


def test_describe_states_the_situation_without_predicting_the_outcome():
    text = ep.describe(GameState(95, 1, 5))
    assert "1st & goal" in text
    assert "expected points" in text
    for hype in ("will score", "guaranteed", "certain", "lock"):
        assert hype not in text.lower()


# ── the live projection ──────────────────────────────────────────────────────

def _live(**kw):
    base = dict(
        league="nfl", home_score=17, away_score=21, period=3, clock_seconds=400,
        pregame_margin=1.5, total_estimate=45.0, home_share=0.52,
        possession_home=True,
    )
    base.update(kw)
    return live_projection(**base)


def test_the_projection_moves_before_the_score_does():
    """
    The whole point. Same score, same clock, same possession — only the field
    position differs, and the probability must differ with it.
    """
    backed_up = _live(yard_line=20, down=3, distance=12)
    goal_line = _live(yard_line=95, down=1, distance=5)
    assert goal_line["home_win"] - backed_up["home_win"] > 0.20


def test_a_drive_advancing_raises_the_probability_step_by_step():
    steps = [
        _live(yard_line=25, down=1, distance=10),
        _live(yard_line=50, down=1, distance=10),
        _live(yard_line=80, down=1, distance=10),
        _live(yard_line=95, down=1, distance=5),
    ]
    probs = [s["home_win"] for s in steps]
    assert probs == sorted(probs)


def test_the_same_state_matters_more_late_than_early():
    """
    Five expected points barely register in the first quarter and are close to
    decisive in the fourth. That falls out of the shrinking margin sigma.
    """
    early = _live(period=1, clock_seconds=720, home_score=0, away_score=0,
                  yard_line=95, down=1, distance=5)["home_win"]
    early_neutral = _live(period=1, clock_seconds=720, home_score=0, away_score=0,
                          yard_line=25, down=1, distance=10)["home_win"]
    late = _live(period=4, clock_seconds=120, home_score=0, away_score=0,
                 yard_line=95, down=1, distance=5)["home_win"]
    late_neutral = _live(period=4, clock_seconds=120, home_score=0, away_score=0,
                         yard_line=25, down=1, distance=10)["home_win"]
    assert (late - late_neutral) > (early - early_neutral)


def test_possession_by_the_away_team_moves_the_number_the_other_way():
    home_ball = _live(possession_home=True, yard_line=95, down=1, distance=5)
    away_ball = _live(possession_home=False, yard_line=95, down=1, distance=5)
    assert home_ball["home_win"] > away_ball["home_win"]


def test_without_field_position_it_is_the_scoreboard_model_and_says_so():
    out = _live(yard_line=None, down=None, distance=None)
    assert out["state_aware"] is False
    assert out["drive_value"] == 0.0
    assert out["drive_note"] == ""
    # And still returns a usable projection rather than failing.
    assert 0.0 < out["home_win"] < 1.0


def test_a_nonsense_yard_line_falls_back_rather_than_being_believed():
    out = _live(yard_line=250, down=1, distance=10)
    assert out["state_aware"] is False
    assert out["drive_value"] == 0.0


def test_the_projected_score_credits_the_drive_to_whoever_has_the_ball():
    home_ball = _live(possession_home=True, yard_line=95, down=1, distance=5)
    away_ball = _live(possession_home=False, yard_line=95, down=1, distance=5)
    assert home_ball["proj_home"] > away_ball["proj_home"]
    assert away_ball["proj_away"] > home_ball["proj_away"]


def test_red_zone_and_goal_to_go_are_reported_for_the_ui():
    out = _live(yard_line=95, down=1, distance=5)
    assert out["red_zone"] is True
    assert out["goal_to_go"] is True


def test_probability_stays_a_probability_in_every_state():
    for y in range(0, 101, 5):
        for d in (1, 2, 3, 4):
            out = _live(yard_line=y, down=d, distance=10)
            assert 0.0 <= out["home_win"] <= 1.0
            assert out["home_win"] + out["away_win"] == pytest.approx(1.0)


# ── the timeline ─────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clean_history():
    win_history.reset()
    yield
    win_history.reset()


def _point(**kw):
    base = dict(league="nfl", event_id="1", home_win=0.5, home_score=0, away_score=0)
    base.update(kw)
    win_history.record(**base)


def test_readings_are_recorded_in_order():
    _point(home_win=0.50)
    _point(home_win=0.62)
    _point(home_win=0.71)
    points = win_history.series("nfl", "1")
    assert [p["home_win"] for p in points] == [0.5, 0.62, 0.71]


def test_an_unchanged_reading_is_not_stored_twice():
    """The board is polled far faster than the number moves."""
    for _ in range(20):
        _point(home_win=0.50)
    assert len(win_history.series("nfl", "1")) == 1


def test_a_score_change_is_always_recorded_and_flagged():
    _point(home_win=0.50, home_score=0, away_score=0)
    _point(home_win=0.50, home_score=7, away_score=0)
    points = win_history.series("nfl", "1")
    assert len(points) == 2
    assert points[1]["scored"] is True
    assert points[0]["scored"] is False


def test_swing_reports_the_journey_not_just_the_current_number():
    _point(home_win=0.50)
    _point(home_win=0.72)
    _point(home_win=0.61)
    swing = win_history.swing("nfl", "1")
    assert swing["opening_home_win"] == 0.5
    assert swing["current_home_win"] == 0.61
    assert swing["change"] == pytest.approx(0.11)
    assert swing["high"] == 0.72
    assert swing["low"] == 0.5


def test_a_game_with_one_reading_has_no_swing_yet():
    _point(home_win=0.50)
    assert win_history.swing("nfl", "1") is None


def test_games_are_kept_separate():
    _point(event_id="1", home_win=0.4)
    _point(event_id="2", home_win=0.9)
    assert win_history.series("nfl", "1")[0]["home_win"] == 0.4
    assert win_history.series("nfl", "2")[0]["home_win"] == 0.9
    assert win_history.series("ncaaf", "1") == []


def test_a_series_is_capped_but_keeps_its_opening_anchor():
    _point(home_win=0.10)
    for i in range(win_history.MAX_POINTS_PER_GAME + 50):
        _point(home_win=0.20 + (i % 90) * 0.005)
    points = win_history.series("nfl", "1")
    assert len(points) <= win_history.MAX_POINTS_PER_GAME
    assert points[0]["home_win"] == 0.10


def test_recording_never_raises_on_bad_input():
    win_history.record(league="nfl", event_id="x", home_win=float("nan"),
                       home_score=0, away_score=0)
    win_history.record(league="nfl", event_id="y", home_win=0.5,
                       home_score=None, away_score=0)   # type: ignore[arg-type]


def test_nobody_in_possession_is_not_read_as_the_away_team_having_the_ball():
    """
    Between plays the feed publishes no possession. Passing False there would
    mean "the away team has it" and would move the projection the wrong way, so
    the route passes None and the possession term drops out entirely.
    """
    none_ball = _live(possession_home=None, yard_line=95, down=1, distance=5)
    assert none_ball["state_aware"] is False
    assert none_ball["drive_value"] == 0.0

    away_ball = _live(possession_home=False, yard_line=95, down=1, distance=5)
    assert away_ball["state_aware"] is True
    assert none_ball["home_win"] > away_ball["home_win"]


def test_drive_value_is_signed_from_the_home_teams_point_of_view():
    """
    Every other number in this payload is home-relative. An unsigned magnitude
    would render as a gain on a home-centric card while the opponent marched.
    """
    home_ball = _live(possession_home=True, yard_line=95, down=1, distance=5)
    away_ball = _live(possession_home=False, yard_line=95, down=1, distance=5)
    assert home_ball["drive_value"] > 0
    assert away_ball["drive_value"] < 0
    assert home_ball["drive_value"] == pytest.approx(-away_ball["drive_value"])

    # A bad spot is negative for whoever is in it.
    home_pinned = _live(possession_home=True, yard_line=5, down=3, distance=15)
    assert home_pinned["drive_value"] < 0
