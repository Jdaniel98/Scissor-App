"""FastAPI dependencies shared by the HTML pages and the API."""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .database.db import get_session
from .services.cache import LinkCache
from .services.links import LinkService
from .services.ratelimit import RateLimiter


def get_cache(request: Request) -> LinkCache:
    cache: LinkCache = request.app.state.cache
    return cache


def get_limiter(request: Request) -> RateLimiter:
    limiter: RateLimiter = request.app.state.limiter
    return limiter


def own_hosts(request: Request) -> set[str]:
    hosts = set(get_settings().public_host_set)
    if request.url.hostname:
        hosts.add(request.url.hostname.lower())
    return hosts


def get_link_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    cache: Annotated[LinkCache, Depends(get_cache)],
) -> LinkService:
    return LinkService(session, cache, own_hosts(request))


Links = Annotated[LinkService, Depends(get_link_service)]


def client_ip(request: Request) -> str:
    # Behind a proxy, uvicorn's --proxy-headers puts the forwarded client address here.
    return request.client.host if request.client else "unknown"


def rate_limit(scope: str, setting: str) -> Callable[[Request], Awaitable[None]]:
    """A dependency that counts the request against `setting` (a Settings field name)."""

    async def dependency(request: Request) -> None:
        rule: str = getattr(get_settings(), setting)
        await get_limiter(request).hit(rule, scope, client_ip(request))

    return dependency
