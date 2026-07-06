"""Guards against the soccer/MLB 'too many unders + underdogs' bias returning."""
from __future__ import annotations

from src.predict.baseball import predict_mlb_game
from src.predict.soccer import predict_match


def test_soccer_even_match_is_not_under_biased() -> None:
    r = predict_match("A", "B", 1800, 1800, use_styles=False)
    p, t = r.model_probs, r.totals
    total_xg = p.home_xg + p.away_xg
    assert 2.5 <= total_xg <= 2.95            # real average ~2.7, not the old ~2.1
    assert 0.45 <= t.over_2_5 <= 0.56          # coin-flip-ish, not the old 0.36
    assert p.draw < 0.31                       # draws no longer over-weighted


def test_soccer_favourite_is_not_under_rated() -> None:
    r = predict_match("A", "B", 1950, 1720, use_styles=False)   # +230 Elo home
    p = r.model_probs
    assert p.home_win - p.away_win > 0.20      # a clear favourite reads as one
    assert p.home_win > 0.45


def test_soccer_big_mismatch_not_overconfident() -> None:
    # The recalibration must sharpen favourites without making them absurd.
    r = predict_match("A", "B", 2082, 1490, use_styles=False)   # +592 Elo
    assert r.model_probs.home_win < 0.80


def test_soccer_styles_are_net_neutral() -> None:
    # Style multipliers must only redistribute scoring, never shave totals
    # across the board (that was re-introducing an under-lean).
    from src.data.world_cup import TEAMS, get_style
    atts = [get_style(c)[0] for c in TEAMS]
    defs = [get_style(c)[1] for c in TEAMS]
    assert abs(sum(atts) / len(atts) - 1.0) < 0.02
    assert abs(sum(defs) / len(defs) - 1.0) < 0.02


def test_soccer_styled_even_match_not_under_biased() -> None:
    # With styles applied (as the live model runs), an average matchup must
    # still land on the league total, not below it.
    r = predict_match("A", "B", 1850, 1850, use_styles=True)
    total = r.model_probs.home_xg + r.model_probs.away_xg
    assert 2.5 <= total <= 2.95
    assert 0.45 <= r.totals.over_2_5 <= 0.56


def test_mlb_favourite_not_compressed_to_a_coin_flip() -> None:
    # KC/MIN carry no park factor or style override → pure rating effect.
    r = predict_mlb_game("KC", "MIN", 1545, 1455)              # +90 Elo home fav
    assert r.home_win_prob > 0.55
    assert 8.4 <= r.total_points_estimate <= 9.4               # ~real run environment
