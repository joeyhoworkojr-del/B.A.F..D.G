"""
The micro-cache in front of the boards.

Its job is not really to save repeated work over time — a few seconds of TTL
barely does that. Its job is to collapse a *burst*: when a hundred people open
the homepage at kickoff, that must cost one upstream fetch, not a hundred.
"""
from __future__ import annotations

import asyncio

import pytest

from src.api import cache


@pytest.fixture(autouse=True)
def _clean():
    cache.clear()
    yield
    cache.clear()


def test_a_second_caller_reuses_the_first_result():
    calls = {"n": 0}

    async def build():
        calls["n"] += 1
        return {"v": calls["n"]}

    async def run():
        a = await cache.cached("k", build)
        b = await cache.cached("k", build)
        return a, b

    a, b = asyncio.run(run())
    assert a == b == {"v": 1}
    assert calls["n"] == 1


def test_a_burst_of_concurrent_callers_causes_one_build():
    """The property that matters. Without it, a spike multiplies the load it
    causes upstream by the number of people in it."""
    calls = {"n": 0}

    async def slow_build():
        calls["n"] += 1
        await asyncio.sleep(0.05)     # a real feed takes time
        return {"built": calls["n"]}

    async def run():
        return await asyncio.gather(*(cache.cached("k", slow_build) for _ in range(50)))

    results = asyncio.run(run())
    assert calls["n"] == 1, f"{calls['n']} builds for 50 concurrent callers"
    assert all(r == {"built": 1} for r in results)


def test_a_stale_result_is_served_at_once_and_refreshed_behind_the_reader():
    """
    "It does not load straight away" is what waiting for a rebuild looks like.
    A result a few seconds past its TTL is not worth making someone wait for,
    so it is handed over immediately and replaced in the background.
    """
    calls = {"n": 0}

    async def build():
        calls["n"] += 1
        return calls["n"]

    async def run():
        first = await cache.cached("k", build, ttl=0.01)
        await asyncio.sleep(0.02)
        # Stale now — but answered without a wait, from the old value.
        second = await cache.cached("k", build, ttl=0.01)
        # ...and the refresh it kicked off lands shortly after.
        await asyncio.sleep(0.05)
        third = await cache.cached("k", build, ttl=0.01)
        return first, second, third

    first, second, third = asyncio.run(run())
    assert (first, second) == (1, 1), "a stale value must not block on a rebuild"
    assert third == 2, "the background refresh must actually replace it"


def test_a_value_past_the_stale_window_is_not_served():
    # Stale-while-revalidate is a courtesy for a couple of minutes, not a
    # licence to hand back something from an hour ago.
    import time as _time

    cache._entries["k"] = (
        _time.monotonic() - cache.STALE_WHILE_REVALIDATE_SECONDS - 60, "ancient",
    )
    assert cache.peek("k", ttl=cache.DEFAULT_TTL_SECONDS) is None
    assert cache.peek(
        "k", ttl=cache.DEFAULT_TTL_SECONDS + cache.STALE_WHILE_REVALIDATE_SECONDS,
    ) is None


def test_keeping_a_key_warm_rebuilds_it_without_anyone_asking():
    # The whole point: nobody should ever be the reader who pays for a cold
    # cache after a deploy or a quiet spell.
    calls = {"n": 0}

    async def build():
        calls["n"] += 1
        return calls["n"]

    async def run():
        task = asyncio.create_task(cache.keep_warm("k", build, every=0.01))
        await asyncio.sleep(0.05)
        task.cancel()
        return cache.peek("k", ttl=1.0)

    value = asyncio.run(run())
    assert value is not None, "the key was never built"
    assert calls["n"] >= 2, "it built once and stopped rather than looping"


def test_different_keys_do_not_share_a_result():
    async def run():
        return (
            await cache.cached("nfl", lambda: _value("nfl")),
            await cache.cached("ncaaf", lambda: _value("ncaaf")),
        )

    async def _value(v):
        return v

    assert asyncio.run(run()) == ("nfl", "ncaaf")


def test_a_failed_build_is_not_cached_as_a_result():
    # Caching a failure would turn one bad upstream moment into several
    # seconds of everyone seeing it.
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("feed down")
        return "good"

    async def run():
        with pytest.raises(RuntimeError):
            await cache.cached("k", flaky)
        return await cache.cached("k", flaky)

    assert asyncio.run(run()) == "good"
