"""Tiny async-safe TTL cache used to throttle external data calls.

Designed for one process; not a substitute for Redis. The intent is to
collapse bursts of identical requests (e.g. multiple panels on the Stock
page asking for the same quote) and to soften flaky upstreams without
hiding real errors — failures are not cached.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable


class TTLCache:
    """Per-key TTL cache. Concurrent requests for the same missing key
    deduplicate on a key-scoped lock so the upstream call only fires once."""

    def __init__(self, default_ttl: float = 60.0, max_entries: int = 4096):
        self.default_ttl = default_ttl
        self.max_entries = max_entries
        self._store: dict[str, tuple[float, Any]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock(self, key: str) -> asyncio.Lock:
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock

    def _maybe_evict(self) -> None:
        if len(self._store) <= self.max_entries:
            return
        # Drop a random ~10% of entries; cheap and prevents unbounded growth.
        to_drop = len(self._store) // 10 or 1
        for k in list(self._store)[:to_drop]:
            self._store.pop(k, None)
            self._locks.pop(k, None)

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[Any]],
        ttl: float | None = None,
    ) -> Any:
        ttl = self.default_ttl if ttl is None else ttl
        now = time.monotonic()
        hit = self._store.get(key)
        if hit and hit[0] > now:
            return hit[1]

        async with self._lock(key):
            hit = self._store.get(key)
            if hit and hit[0] > time.monotonic():
                return hit[1]
            value = await factory()  # exceptions propagate; nothing cached on failure
            self._store[key] = (time.monotonic() + ttl, value)
            self._maybe_evict()
            return value

    def invalidate(self, key: str | None = None) -> None:
        if key is None:
            self._store.clear()
            self._locks.clear()
        else:
            self._store.pop(key, None)
            self._locks.pop(key, None)
