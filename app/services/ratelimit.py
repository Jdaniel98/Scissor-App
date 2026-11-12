"""Per-IP rate limits, stored in Redis (or memory when no Redis is configured)."""

import math
import time

from limits import parse
from limits.aio.storage import Storage
from limits.aio.strategies import MovingWindowRateLimiter
from limits.storage import storage_from_string


class RateLimited(Exception):
    def __init__(self, retry_after: int) -> None:
        super().__init__("Too many requests")
        self.retry_after = retry_after


class RateLimiter:
    def __init__(self, redis_url: str) -> None:
        uri = "async+" + redis_url if redis_url else "async+memory://"
        options = {"implementation": "redispy"} if redis_url else {}
        storage = storage_from_string(uri, **options)
        assert isinstance(storage, Storage)
        self.storage = storage
        self._limiter = MovingWindowRateLimiter(storage)

    async def hit(self, rule: str, scope: str, client: str) -> None:
        """Count one request; raise RateLimited when `client` is over `rule` for `scope`."""
        item = parse(rule)
        if await self._limiter.hit(item, scope, client):
            return
        reset_at, _remaining = await self._limiter.get_window_stats(item, scope, client)
        raise RateLimited(retry_after=max(1, math.ceil(reset_at - time.time())))

    async def reset(self) -> None:
        await self.storage.reset()
