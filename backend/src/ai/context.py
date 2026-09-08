"""
The only data Edge AI can see.

The assistant does not query the database. It calls the functions in this
module, each of which returns a small, explicit record assembled from the same
code paths that render the site. That boundary is the whole security design:
there is no query the model can write, no table it can name, and no row it can
reach that a page could not already show the person asking.

Two rules shape every function here:

  1. A missing value is reported as missing. Absent data is returned as
     `available: false` with a reason, never as a zero, a blank or an omission
     the model might fill in from its own training.
  2. Nothing personal crosses the boundary unless it belongs to the person
     asking. `get_user_performance` takes the caller's own id from the session
     and cannot be pointed at anyone else.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

log = logging.getLogger(__name__)

# Leagues the product actually models. A question about anything else is
# answered with "not covered" rather than with a guess.
LEAGUES = ("nfl", "ncaaf")

# Caps on what one answer may pull in, so a single question cannot drag the
# whole board into a prompt.
MAX_GAMES = 12
MAX_PLAYERS = 20
MAX_PICKS = 20
MAX_NEWS = 8
MAX_LEADERBOARD = 15


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _unavailable(what: str, why: str) -> dict:
    """
    The shape every function returns when it has nothing.

    Explicit rather than empty, because "no data" and "zero" mean different
    things and the model must not confuse them.
    """
    return {"available": False, "what": what, "reason": why, "as_of": _now()}


async def get_game_context(league: str, event_id: str) -> dict:
    """The full picture for one game: teams, status, model, market, edges."""
    league = (league or "").lower()
    if league not in LEAGUES:
        return _unavailable("game", f"StatEdge covers {' and '.join(LEAGUES).upper()} only")

    from src.api.routes.predictions import game_detail
    from fastapi import HTTPException
    try:
        detail = await game_detail(league, event_id)
    except HTTPException as exc:
        return _unavailable("game", str(exc.detail))
    except Exception as exc:
        log.warning("Edge AI game context failed: %s", type(exc).__name__)
        return _unavailable("game", "the game feed is temporarily unreachable")

    game = detail.get("game") or {}
    model = detail.get("model") or {}
    return {
        "available": True,
        "league": league,
        "event_id": event_id,
        "status": detail.get("status"),
        "home": {"name": game.get("home"), "abbr": game.get("home_abbr"),
                 "score": game.get("home_score")},
        "away": {"name": game.get("away"), "abbr": game.get("away_abbr"),
                 "score": game.get("away_score")},
        "kickoff": game.get("kickoff"),
        "detail": game.get("detail"),
        "model": {
            "home_win_probability": model.get("calibrated_home_win") or model.get("home_win_prob"),
            "projected_home_score": model.get("proj_home_score") or model.get("home_expected"),
            "projected_away_score": model.get("proj_away_score") or model.get("away_expected"),
            "projected_total": model.get("total_estimate"),
            "market_anchored": model.get("market_anchored"),
        } if model else None,
        "market": {
            "spread": game.get("market_spread"),
            "total": game.get("market_over_under"),
            "book": game.get("market_provider"),
        },
        "edges": [
            {"market": e.get("market"), "selection": e.get("selection"),
             "model_probability": e.get("model_prob"), "grade": e.get("grade")}
            for e in (detail.get("edges") or [])[:6]
        ],
        "model_version": detail.get("model_version"),
        "source": detail.get("source"),
        "feed_ok": detail.get("source_ok"),
        "fetched_at": detail.get("fetched_at"),
        "as_of": _now(),
    }


async def get_live_game_state(league: str, event_id: str) -> dict:
    """
    Where the game actually is right now, and why the projection has moved.

    This is the function that lets the assistant answer "why did we go to 64%"
    with the reason rather than a restatement of the number.
    """
    context = await get_game_context(league, event_id)
    if not context.get("available"):
        return context
    if context.get("status") != "in":
        return _unavailable("live state", "this game is not in progress")

    from src.api.routes.predictions import game_detail
    detail = await game_detail(league, event_id)
    game = detail.get("game") or {}
    model = detail.get("model") or {}

    from src.track import win_history
    swing = win_history.swing(league, event_id)

    yard_line = game.get("yard_line")
    possession = game.get("possession_abbr") or ""
    field_position = None
    if yard_line is not None and possession:
        to_go = 100 - int(yard_line)
        field_position = {
            "team_with_ball": possession,
            "yards_from_own_goal": yard_line,
            "yards_to_opposing_end_zone": to_go,
            "down": game.get("down"),
            "distance": game.get("distance"),
            "red_zone": bool(model.get("red_zone")),
            "goal_to_go": bool(model.get("goal_to_go")),
            "down_and_distance_text": game.get("down_distance"),
        }

    return {
        "available": True,
        "league": league,
        "event_id": event_id,
        "score": {"home": game.get("home_score"), "away": game.get("away_score"),
                  "home_abbr": game.get("home_abbr"), "away_abbr": game.get("away_abbr")},
        "clock": {"period": game.get("period"), "display": game.get("clock"),
                  "time_remaining_pct": model.get("time_remaining_pct")},
        # None when the feed publishes no field position. The assistant must
        # not describe a situation the feed did not report.
        "field_position": field_position,
        "live_home_win_probability": model.get("live_home_win"),
        "pregame_home_win_probability": model.get("calibrated_home_win") or model.get("home_win_prob"),
        "live_projected_score": {"home": model.get("live_proj_home"),
                                 "away": model.get("live_proj_away")},
        # The expected-points value of the drive in progress, and the sentence
        # the model itself produced for it.
        "possession_value_points": model.get("drive_value"),
        "why_the_projection_moved": model.get("drive_note") or "",
        "uses_field_position": bool(model.get("state_aware")),
        "probability_swing_this_game": swing,
        "last_play": game.get("last_play") or "",
        "as_of": _now(),
    }


async def get_prediction(league: str, event_id: str) -> dict:
    """The model's call on one game, pre-game and live, kept apart."""
    context = await get_game_context(league, event_id)
    if not context.get("available"):
        return context
    live = await get_live_game_state(league, event_id)
    return {
        "available": True,
        "pregame": context.get("model"),
        "live": live if live.get("available") else None,
        "note": (
            "The pre-game projection is frozen at kickoff and is the one the "
            "public record grades. The live projection moves with the game and "
            "is never graded."
        ),
        "as_of": _now(),
    }


async def get_todays_games(league: Optional[str] = None) -> dict:
    """Everything on the board today, with each model call attached."""
    wanted = [league.lower()] if league and league.lower() in LEAGUES else list(LEAGUES)
    from src.api.routes.predictions import today

    games: list[dict] = []
    failures: list[str] = []
    for lg in wanted:
        try:
            board = await today(lg)
        except Exception as exc:
            failures.append(f"{lg}: {type(exc).__name__}")
            continue
        for entry in (board.get("games") or [])[:MAX_GAMES]:
            game = entry.get("game") or {}
            model = entry.get("model") or {}
            games.append({
                "league": lg,
                "event_id": game.get("event_id"),
                "away": game.get("away_abbr"), "home": game.get("home_abbr"),
                "status": game.get("state"), "detail": game.get("detail"),
                "score": {"home": game.get("home_score"), "away": game.get("away_score")},
                "home_win_probability": (
                    model.get("live_home_win") if model.get("live")
                    else model.get("calibrated_home_win") or model.get("home_win_prob")
                ),
                "spread": game.get("market_spread"),
                "total": game.get("market_over_under"),
            })

    if not games:
        return _unavailable("today's games", "; ".join(failures) or "nothing is scheduled today")
    return {"available": True, "games": games[:MAX_GAMES], "as_of": _now(),
            "partial": bool(failures)}


async def get_player_props(league: str, event_id: str) -> dict:
    """Projected player numbers for one game."""
    league = (league or "").lower()
    if league not in LEAGUES:
        return _unavailable("player props", f"StatEdge covers {' and '.join(LEAGUES).upper()} only")
    from src.api.routes.predictions import game_player_props
    try:
        payload = await game_player_props(league, event_id)
    except Exception as exc:
        log.warning("Edge AI props failed: %s", type(exc).__name__)
        return _unavailable("player props", "the player feed is temporarily unreachable")

    projections = (payload.get("projections") or [])[:MAX_PLAYERS]
    if not projections:
        return _unavailable("player props", "no player projections are published for this game")
    return {
        "available": True,
        "league": league, "event_id": event_id,
        "lines_available": payload.get("lines_available", False),
        "lines_note": payload.get("lines_note", ""),
        "projections": [
            {"player": p.get("player"), "team": p.get("team_abbr"),
             "market": p.get("label"), "projection": p.get("projection"),
             "season_average": p.get("season_avg"), "games_played": p.get("games_played"),
             "is_actual_result": p.get("actual", False)}
            for p in projections
        ],
        "as_of": _now(),
    }


async def get_news(league: Optional[str] = None) -> dict:
    """Recent headlines, attributed. Summaries only — never full articles."""
    from src.ingest.news import fetch_news_multi
    leagues = [league.lower()] if league and league.lower() in LEAGUES else list(LEAGUES)
    try:
        feed = await fetch_news_multi(leagues)
    except Exception as exc:
        log.warning("Edge AI news failed: %s", type(exc).__name__)
        return _unavailable("news", "the news feed is temporarily unreachable")

    items = (getattr(feed, "items", None) or [])[:MAX_NEWS]
    if not items:
        return _unavailable("news", "no headlines were returned for these leagues")
    return {
        "available": True,
        "items": [
            {"headline": i.headline, "summary": i.description,
             "published": i.published, "publisher": "ESPN", "url": i.url}
            for i in items
        ],
        "note": (
            "Headlines are ESPN's reporting. Summarise them and attribute them; "
            "do not claim a projection accounts for a story unless the game "
            "context says the model used it."
        ),
        "as_of": _now(),
    }


async def get_community_consensus(league: str, event_id: str) -> dict:
    """How StatEdge users have actually picked one game."""
    # Read the pick service directly rather than the route: the route also
    # returns the viewer's own picks, which needs a request this call does not
    # have and which the assistant has no business seeing for someone else.
    from src.picks import service as picks
    try:
        rows = picks.for_game(f"{(league or '').lower()}:{event_id}")
    except Exception as exc:
        log.warning("Edge AI community failed: %s", type(exc).__name__)
        return _unavailable("community consensus", "the community feed is unavailable")

    if not rows:
        return _unavailable("community consensus", "nobody has published a pick on this game yet")

    by_side: dict[str, int] = {}
    for pick in rows:
        if pick.market == "moneyline":
            by_side[pick.side] = by_side.get(pick.side, 0) + 1
    total = sum(by_side.values())
    return {
        "available": True,
        "total_picks": len(rows),
        # Percentages only once there is something to divide. An empty split is
        # reported as empty rather than as a fabricated 50/50.
        "moneyline_split": (
            {side: round(n / total * 100, 1) for side, n in by_side.items()}
            if total else {}
        ),
        "note": "This is how StatEdge users picked, not a betting handle or a market share.",
        "as_of": _now(),
    }


async def get_leaderboard(league: Optional[str] = None) -> dict:
    """The ranked analysts, with the provisional ones marked."""
    from src.picks import leaderboard
    try:
        rows = leaderboard.standings(league.lower() if league else None)
    except Exception as exc:
        log.warning("Edge AI leaderboard failed: %s", type(exc).__name__)
        return _unavailable("leaderboard", "the leaderboard is unavailable")
    if not rows:
        return _unavailable("leaderboard", "nobody has enough graded picks to be ranked yet")
    return {
        "available": True,
        "standings": [
            {"rank": i + 1, "username": r.username, "display_name": r.display_name,
             "edge_rating": r.edge_rating, "graded": r.graded,
             "wins": r.wins, "losses": r.losses, "pushes": r.pushes,
             "units": r.units, "provisional": r.provisional}
            for i, r in enumerate(rows[:MAX_LEADERBOARD])
        ],
        "note": (
            "Provisional analysts have too few graded picks for the rating to "
            "mean much yet, and are ranked below established ones."
        ),
        "as_of": _now(),
    }


async def get_user_performance(user_id: Optional[str]) -> dict:
    """
    The asking user's own record.

    Takes the id from the session, never from the model. There is no argument
    the assistant could set to read somebody else's account.
    """
    if not user_id:
        return _unavailable("your record", "you are not signed in")
    from src.picks import service as picks
    try:
        record = picks.record_for(user_id)
        mine = [p for p in picks.all_picks() if p.user_id == user_id]
    except Exception as exc:
        log.warning("Edge AI user record failed: %s", type(exc).__name__)
        return _unavailable("your record", "your record is temporarily unavailable")

    if not mine:
        return _unavailable("your record", "you have not published any picks yet")
    mine.sort(key=lambda p: p.created_at, reverse=True)
    return {
        "available": True,
        "record": record,
        "recent_picks": [
            {"league": p.league, "market": p.market, "selection": p.selection,
             "confidence": p.confidence, "graded": p.graded, "result": p.result,
             "units": p.units, "created_at": p.created_at}
            for p in mine[:MAX_PICKS]
        ],
        "as_of": _now(),
    }


async def get_analyst_profile(username: str) -> dict:
    """A public analyst profile and verified record."""
    from src.accounts.service import get_by_username
    from src.picks import service as picks
    user = get_by_username(username or "")
    if user is None:
        return _unavailable("analyst", f"there is no analyst called @{username}")
    if not getattr(user, "profile_public", True):
        return _unavailable("analyst", "that profile is private")
    try:
        record = picks.record_for(user.id)
    except Exception:
        record = None
    return {
        "available": True,
        "username": user.username,
        "display_name": user.display_name or user.username,
        "bio": user.bio,
        "badges": user.badges,
        "record": record,
        "as_of": _now(),
    }
