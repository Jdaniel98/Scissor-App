"""Cache of short code -> destination, so redirects skip the database."""

import json
import time
from dataclasses import dataclass
from typing import Protocol

from redis.asyncio import Redis


@dataclass(frozen=True)
class CachedLink:
    id: int
    url: str


class LinkCache(Protocol):
    async def get(self, code: str) -> CachedLink | None: ...
    async def set(self, code: str, link: CachedLink) -> None: ...
    async def delete(self, code: str) -> None: ...
    async def clear(self) -> None: ...
    async def close(self) -> None: ...


def _key(code: str) -> str:
    return f"scissor:link:{code}"


class RedisLinkCache:
    def __init__(self, redis_url: str, ttl: int) -> None:
        self._redis = Redis.from_url(redis_url, decode_responses=True)
        self._ttl = ttl

    async def get(self, code: str) -> CachedLink | None:
        raw = await self._redis.get(_key(code))
        if raw is None:
            return None
        data = json.loads(raw)
        return CachedLink(id=int(data["id"]), url=str(data["url"]))

    async def set(self, code: str, link: CachedLink) -> None:
        payload = json.dumps({"id": link.id, "url": link.url})
        await self._redis.set(_key(code), payload, ex=self._ttl)

    async def delete(self, code: str) -> None:
        await self._redis.delete(_key(code))

    async def clear(self) -> None:
        async for key in self._redis.scan_iter(match=_key("*")):
            await self._redis.delete(key)

    async def close(self) -> None:
        await self._redis.aclose()


class MemoryLinkCache:
    """For local runs and tests. Each process has its own copy, so not for production."""

    def __init__(self, ttl: int) -> None:
        self._items: dict[str, tuple[float, CachedLink]] = {}
        self._ttl = ttl

    async def get(self, code: str) -> CachedLink | None:
        item = self._items.get(code)
        if item is None:
            return None
        expires_at, link = item
        if expires_at < time.monotonic():
            self._items.pop(code, None)
            return None
        return link

    async def set(self, code: str, link: CachedLink) -> None:
        self._items[code] = (time.monotonic() + self._ttl, link)

    async def delete(self, code: str) -> None:
        self._items.pop(code, None)

    async def clear(self) -> None:
        self._items.clear()

    async def close(self) -> None:
        self._items.clear()


def build_cache(redis_url: str, ttl: int) -> LinkCache:
    if redis_url:
        return RedisLinkCache(redis_url, ttl)
    return MemoryLinkCache(ttl)
