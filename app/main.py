from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api.errors import install_error_handlers
from .api.v1 import router as api_v1_router
from .config import get_settings
from .database.db import engine
from .routers.url import url_router
from .services.cache import build_cache
from .services.ratelimit import RateLimiter


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.cache = build_cache(settings.redis_url, settings.redirect_cache_ttl)
    app.state.limiter = RateLimiter(settings.redis_url)
    yield
    await app.state.cache.close()
    await engine.dispose()


# The schema is managed by Alembic: run `alembic upgrade head` before starting the app.
app = FastAPI(
    title="Scissor",
    version="1.0.0",
    summary="Short links with click stats and QR codes.",
    description=(
        "Create a link with `POST /api/v1/links`. The response includes an `edit_key`, "
        "shown once: send it as `Authorization: Bearer <edit_key>` to edit, delete or "
        "read stats for that link. Errors always look like "
        '`{"error": {"code": ..., "message": ...}}`.'
    ),
    lifespan=lifespan,
)

install_error_handlers(app)
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
app.include_router(api_v1_router)
app.include_router(url_router)
