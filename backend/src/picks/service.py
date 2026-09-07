"""
Pick submission, locking and grading.

Every integrity rule is enforced here, server-side. The frontend is never
trusted for identity, for whether an event has started, or for what a line was
when a pick was made.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from src.picks import grading
from src.picks.models import (
    COLLECTION, MAX_REASONING, Pick, PickError, validate_confidence,
    validate_market,
)
from src.store.documents import get_docs

log = logging.getLogger(__name__)

USER_INDEX = "picks_by_user"
GAME_INDEX = "picks_by_game"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso() -> str:
    return _now().isoformat(timespec="seconds")


def _save(pick: Pick) -> Pick:
    get_docs().put(COLLECTION, pick.id, pick.to_doc())
    return pick


def get(pick_id: str) -> Optional[Pick]:
    doc = get_docs().get(COLLECTION, pick_id)
    return Pick.from_doc(doc) if doc else None


def all_picks() -> list[Pick]:
    return [Pick.from_doc(d) for d in get_docs().list(COLLECTION)]


def for_user(user_id: str) -> list[Pick]:
    picks = [p for p in all_picks() if p.user_id == user_id]
    picks.sort(key=lambda p: p.created_at, reverse=True)
    return picks


def for_game(game_id: str) -> list[Pick]:
    return [p for p in all_picks() if p.game_id == game_id]


def submit(*, user_id: str, username: str, league: str, event_id: str,
           home: str, away: str, kickoff: str, market: str, side: str,
           selection: str, line: Optional[float] = None,
           price_american: Optional[int] = None, odds_source: str = "",
           confidence: Any = 60, reasoning: str = "") -> Pick:
    """
    Record a prediction.

    Refuses after kickoff and refuses a duplicate on the same game and market,
    so a user cannot hedge both sides after the fact and claim whichever won.
    """
    market, side = validate_market(market, side)
    confidence = validate_confidence(confidence)
    game_id = f"{league.lower()}:{event_id}"

    probe = Pick.new(
        user_id=user_id, username=username, game_id=game_id,
        league=league.lower(), event_id=str(event_id), home=home, away=away,
        market=market, side=side, selection=selection, line=line,
        price_american=price_american, odds_source=odds_source,
        confidence=confidence, reasoning=(reasoning or "")[:MAX_REASONING],
        kickoff=kickoff,
    )
    if probe.is_locked():
        raise PickError("This game has already started.")

    for existing in for_user(user_id):
        if existing.game_id == game_id and existing.market == market:
            raise PickError(f"You've already made a {market} pick on this game.")

    return _save(probe)


def update(pick: Pick, *, side: Optional[str] = None,
           selection: Optional[str] = None, confidence: Any = None,
           reasoning: Optional[str] = None) -> Pick:
    """
    Edit before kickoff only.

    After the event starts the record is immutable — that is what makes it
    worth publishing.
    """
    if pick.is_locked():
        raise PickError("This pick is locked — the game has started.")
    if side is not None:
        _, pick.side = validate_market(pick.market, side)
    if selection is not None:
        pick.selection = str(selection)[:120]
    if confidence is not None:
        pick.confidence = validate_confidence(confidence)
    if reasoning is not None:
        pick.reasoning = str(reasoning)[:MAX_REASONING]
    pick.updated_at = _iso()
    return _save(pick)


def delete(pick: Pick) -> None:
    """Withdraw before kickoff. A locked pick can never be deleted."""
    if pick.is_locked():
        raise PickError("This pick is locked — the game has started.")
    get_docs().delete(COLLECTION, pick.id)


def grade_game(game_id: str, home_score: int, away_score: int) -> int:
    """
    Settle every pending pick on a finished game.

    Idempotent: an already-graded pick is skipped, so a feed that reports the
    same final twice — or a retry after a timeout — cannot double-count a
    result or move anyone's record twice.
    """
    graded = 0
    for pick in for_game(game_id):
        if pick.graded:
            continue
        result = grading.settle(pick.market, pick.side, pick.line,
                                home_score, away_score)
        pick.result = result
        pick.units = grading.units_for(result, pick.price_american)
        pick.graded_at = _iso()
        pick.final_home, pick.final_away = home_score, away_score
        _save(pick)
        graded += 1
    return graded


def void_game(game_id: str, reason: str = "") -> int:
    """Postponed or cancelled: pending picks are voided, never lost."""
    voided = 0
    for pick in for_game(game_id):
        if pick.graded:
            continue
        pick.result = "void"
        pick.units = 0.0
        pick.graded_at = _iso()
        _save(pick)
        voided += 1
    return voided


def record_for(user_id: str) -> dict:
    """A user's verified record. Pending picks never count toward it."""
    picks = for_user(user_id)
    graded = [p for p in picks if p.graded and p.result != "void"]
    wins = sum(1 for p in graded if p.result == "win")
    losses = sum(1 for p in graded if p.result == "loss")
    pushes = sum(1 for p in graded if p.result == "push")
    units = round(sum(p.units for p in graded), 2)
    settled = wins + losses            # pushes are not a decision either way
    staked = len(graded)

    return {
        "picks": len(picks),
        "pending": sum(1 for p in picks if not p.graded),
        "graded": len(graded),
        "wins": wins, "losses": losses, "pushes": pushes,
        "win_rate": round(wins / settled, 4) if settled else None,
        "units": units,
        "roi_pct": round(units / staked * 100, 2) if staked else None,
        "avg_confidence": (
            round(sum(p.confidence for p in graded) / len(graded), 1)
            if graded else None
        ),
    }
