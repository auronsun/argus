"""TTLCache behaviour tests."""
from __future__ import annotations

import asyncio

import pytest

from argus.utils.cache import TTLCache


@pytest.mark.asyncio
async def test_cache_hits_within_ttl():
    cache = TTLCache(default_ttl=60.0)
    calls = {"n": 0}

    async def factory():
        calls["n"] += 1
        return calls["n"]

    a = await cache.get_or_set("k", factory)
    b = await cache.get_or_set("k", factory)
    assert a == b == 1
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_cache_misses_after_ttl():
    cache = TTLCache(default_ttl=0.05)
    calls = {"n": 0}

    async def factory():
        calls["n"] += 1
        return calls["n"]

    await cache.get_or_set("k", factory)
    await asyncio.sleep(0.07)
    await cache.get_or_set("k", factory)
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_cache_does_not_store_on_failure():
    cache = TTLCache(default_ttl=60.0)
    state = {"n": 0}

    async def factory():
        state["n"] += 1
        if state["n"] == 1:
            raise RuntimeError("boom")
        return "ok"

    with pytest.raises(RuntimeError):
        await cache.get_or_set("k", factory)
    # The next call must hit the factory again, not return a stale failure.
    out = await cache.get_or_set("k", factory)
    assert out == "ok"
    assert state["n"] == 2


@pytest.mark.asyncio
async def test_cache_dedup_concurrent_misses():
    """Concurrent get_or_set on the same missing key must invoke the factory once."""
    cache = TTLCache(default_ttl=60.0)
    calls = {"n": 0}

    async def factory():
        calls["n"] += 1
        await asyncio.sleep(0.02)
        return "v"

    results = await asyncio.gather(*(cache.get_or_set("k", factory) for _ in range(10)))
    assert results == ["v"] * 10
    assert calls["n"] == 1
