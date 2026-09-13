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


# How long a result may still be served after it has gone stale, while a fresh
# one is built behind it. Waiting for a rebuild is the difference between a
# board that is there and a board that appears a moment later, and a result a
# few seconds past its TTL is not worth making someone wait for.
STALE_WHILE_REVALIDATE_SECONDS = 120.0

_refreshing: set[asyncio.Task] = set()


def _store(key: str, value: Any) -> None:
    _entries[key] = (time.monotonic(), value)


def _revalidate(key: str, build: Callable[[], Awaitable[Any]]) -> None:
    """Rebuild behind a stale answer, once."""
    if _lock_for(key).locked():
        return

    async def run():
        async with _lock_for(key):
            try:
                _store(key, await build())
            except Exception as exc:      # a failed refresh keeps the old value
                log.warning("cache refresh for %s failed: %s", key, type(exc).__name__)

    try:
        task = asyncio.get_running_loop().create_task(run())
    except RuntimeError:
        return
    _refreshing.add(task)
    task.add_done_callback(_refreshing.discard)


async def cached(
    key: str,
    build: Callable[[], Awaitable[Any]],
    ttl: float = DEFAULT_TTL_SECONDS,
) -> Any:
    """
    Return a cached result, or build one — but only ever build it once at a time.

    Fresh is served as is. Slightly stale is served immediately and refreshed
    behind the reader, because a board that is already there beats a board that
    is a few seconds newer. Only a completely cold key waits, and callers who
    arrive during that wait share the one build rather than starting their own.
    """
    hit = peek(key, ttl)
    if hit is not None:
        return hit

    stale = peek(key, ttl + STALE_WHILE_REVALIDATE_SECONDS)
    if stale is not None:
        _revalidate(key, build)
        return stale

    async with _lock_for(key):
        # Someone else may have finished it while this coroutine waited.
        hit = peek(key, ttl)
        if hit is not None:
            return hit
        result = await build()
        _store(key, result)
        return result


async def keep_warm(
    key: str,
    build: Callable[[], Awaitable[Any]],
    every: float,
) -> None:
    """
    Rebuild a key on a loop so no reader is ever the one who pays for it.

    A cold cache is the whole of "it does not load straight away": the first
    person after a deploy, a restart, or a quiet spell waits for the feeds
    while everyone after them does not. Each machine keeps its own, so each
    machine warms its own.
    """
    while True:
        try:
            async with _lock_for(key):
                _store(key, await build())
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.warning("cache warm for %s failed: %s", key, type(exc).__name__)
        await asyncio.sleep(every)


def clear() -> None:
    _entries.clear()
    _locks.clear()
