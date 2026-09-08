"""
Stat Edge's own messages in a game chat.

The rule that matters here is restraint. A model that recalculates every few
seconds could post every few seconds, and a room full of automated noise is
worse than a room with none. So a system message requires all of:

  * a move worth reading — either a big probability swing or a score;
  * a cooling-off period since the last one in that room;
  * something concrete to say about *why*, from the live model's own
    explanation rather than from a template.

Nothing user-controlled reaches these strings. The text is assembled from
numbers and team abbreviations the feed published, which is what makes it safe
to post without moderation.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from src.chat import service
from src.chat.models import game_id as make_game_id

log = logging.getLogger(__name__)

# A swing worth interrupting people for. Below this the number is drifting, not
# moving.
MIN_SWING = 0.10

# Never more often than this in one room, whatever happens.
COOLDOWN_SECONDS = 90.0

# A scoring play is always worth a line, but still not two in a row inside the
# cooldown — a two-point conversion is not a separate event to a reader.
SCORE_COOLDOWN_SECONDS = 25.0

_last_posted: dict[str, float] = {}
_last_probability: dict[str, float] = {}
_last_score: dict[str, tuple[int, int]] = {}


def _pct(value: float) -> str:
    return f"{round(value * 100)}%"


def consider(
    *,
    league: str,
    event_id: str,
    home_abbr: str,
    away_abbr: str,
    home_win: Optional[float],
    home_score: Optional[int],
    away_score: Optional[int],
    drive_note: str = "",
    enabled: bool = True,
) -> Optional[str]:
    """
    Post a message if this update earns one. Returns the text, or None.

    Called from the live prediction path, which runs on every board refresh —
    so the first thing it does is decide to say nothing.
    """
    if not enabled or home_win is None:
        return None

    gid = make_game_id(league, event_id)
    now = time.monotonic()
    previous = _last_probability.get(gid)
    _last_probability[gid] = home_win

    scored = False
    if home_score is not None and away_score is not None:
        before = _last_score.get(gid)
        _last_score[gid] = (home_score, away_score)
        scored = before is not None and before != (home_score, away_score)

    # Nothing to compare against yet: record the baseline and stay quiet.
    if previous is None:
        return None

    swing = home_win - previous
    since_last = now - _last_posted.get(gid, -1e9)
    if scored:
        if since_last < SCORE_COOLDOWN_SECONDS:
            return None
    elif abs(swing) < MIN_SWING or since_last < COOLDOWN_SECONDS:
        return None

    leader = home_abbr if home_win >= 0.5 else away_abbr
    leader_prob = home_win if home_win >= 0.5 else 1 - home_win

    if scored:
        text = (
            f"Score update — {away_abbr} {away_score}, {home_abbr} {home_score}. "
            f"Live projection: {leader} {_pct(leader_prob)}."
        )
    else:
        direction = home_abbr if swing > 0 else away_abbr
        text = (
            f"Live projection moved {_pct(abs(swing))} toward {direction} — "
            f"{_pct(previous)} to {_pct(home_win)} for {home_abbr}."
        )
        if drive_note:
            # The model's own sentence for why, rather than a guess.
            text += f" {drive_note}"

    try:
        service.system_message(league, event_id, text)
    except Exception as exc:                             # pragma: no cover
        log.warning("chat event failed: %s", type(exc).__name__)
        return None

    _last_posted[gid] = now
    return text


def reset() -> None:
    _last_posted.clear()
    _last_probability.clear()
    _last_score.clear()
