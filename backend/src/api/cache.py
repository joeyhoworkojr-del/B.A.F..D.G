"""
A short-lived, single-flight cache for responses that are the same for everyone.

The board, the slate and the week ahead do not depend on who is asking — the
personalisation on top of them happens in the browser, from the session. So N
people loading the homepage at kickoff were N identical fan-outs to ESPN and
the odds feed, each one recomputing the same answer.

Two properties matter, and the second is the one that saves a Saturday:

  * a result is reused for a few seconds, which is shorter than the feeds
    update anyway, so nothing on screen gets older than it already was; and
  * concurrent callers who miss share one computation rather than starting
    one each — the difference between a traffic spike costing one upstream
    fetch and it costing a hundred.

Deliberately not Redis. This is a micro-cache measured in seconds, and a
network hop to save a network hop is not a saving.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Optional

log = logging.getLogger(__name__)

# Long enough to collapse a burst, short enough that a live score is never
# stale in a way a reader would notice: the scoreboard behind it does not move
# faster than this.
DEFAULT_TTL_SECONDS = 8.0

_entries: dict[str, tuple[float, Any]] = {}
_locks: dict[str, asyncio.Lock] = {}


def _lock_for(key: str) -> asyncio.Lock:
    lock = _locks.get(key)
    if lock is None:
        lock = _locks[key] = asyncio.Lock()
    return lock


def peek(key: str, ttl: float = DEFAULT_TTL_SECONDS) -> Optional[Any]:
    hit = _entries.get(key)
    if hit and time.monotonic() - hit[0] < ttl:
        return hit[1]
    return None


async def cached(
    key: str,
    build: Callable[[], Awaitable[Any]],
    ttl: float = DEFAULT_TTL_SECONDS,
) -> Any:
    """
    Return a cached result, or build one — but only ever build it once at a time.

    A caller that arrives while a build is running waits for that build rather
    than starting a second one, then re-checks the cache.
    """
    hit = peek(key, ttl)
    if hit is not None:
        return hit

    async with _lock_for(key):
        # Someone else may have finished it while this coroutine waited.
        hit = peek(key, ttl)
        if hit is not None:
            return hit
        result = await build()
        _entries[key] = (time.monotonic(), result)
        return result


def clear() -> None:
    _entries.clear()
    _locks.clear()
