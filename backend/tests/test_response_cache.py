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


def test_the_result_is_rebuilt_once_it_is_older_than_the_ttl():
    calls = {"n": 0}

    async def build():
        calls["n"] += 1
        return calls["n"]

    async def run():
        first = await cache.cached("k", build, ttl=0.01)
        await asyncio.sleep(0.02)
        second = await cache.cached("k", build, ttl=0.01)
        return first, second

    first, second = asyncio.run(run())
    assert (first, second) == (1, 2)


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
