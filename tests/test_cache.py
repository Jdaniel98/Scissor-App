import asyncio
import os

import pytest

from app.services.cache import CachedLink, MemoryLinkCache, RedisLinkCache, build_cache

REDIS_URL = os.environ.get("TEST_REDIS_URL", "")
needs_redis = pytest.mark.skipif(not REDIS_URL, reason="set TEST_REDIS_URL to test Redis")


async def round_trip(cache) -> None:
    await cache.clear()
    assert await cache.get("abc") is None
    await cache.set("abc", CachedLink(id=7, url="https://example.com"))
    assert await cache.get("abc") == CachedLink(id=7, url="https://example.com")
    await cache.delete("abc")
    assert await cache.get("abc") is None
    await cache.set("x", CachedLink(id=1, url="https://example.org"))
    await cache.clear()
    assert await cache.get("x") is None
    await cache.close()


def test_memory_cache_round_trip():
    asyncio.run(round_trip(MemoryLinkCache(ttl=60)))


def test_memory_cache_expires(monkeypatch):
    cache = MemoryLinkCache(ttl=10)
    now = [1000.0]
    monkeypatch.setattr("app.services.cache.time.monotonic", lambda: now[0])

    async def check() -> None:
        await cache.set("abc", CachedLink(id=1, url="https://example.com"))
        now[0] += 11
        assert await cache.get("abc") is None

    asyncio.run(check())


@needs_redis
def test_redis_cache_round_trip():
    asyncio.run(round_trip(RedisLinkCache(REDIS_URL, ttl=60)))


def test_build_cache_picks_backend():
    assert isinstance(build_cache("", 60), MemoryLinkCache)
    assert isinstance(build_cache("redis://localhost:6379/0", 60), RedisLinkCache)
