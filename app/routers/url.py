"""Server-rendered pages and the redirect itself. The logic lives in services/links.py."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from ..database.db import SessionLocal
from ..deps import Links, get_cache, rate_limit
from ..services.cache import LinkCache
from ..services.errors import LinkNotFound, ServiceError
from ..services.links import LinkService
from ..services.policy import check_destination
from ..templates import templates
from ..utils import generate_qr_code

url_router = APIRouter(tags=["Pages"], include_in_schema=False)


def full_short_link(request: Request, code: str) -> str:
    return str(request.base_url) + code


@url_router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")


@url_router.get("/url", response_class=HTMLResponse)
async def shorten_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "short.html")


@url_router.post(
    "/shorten",
    response_class=HTMLResponse,
    dependencies=[Depends(rate_limit("create", "rate_limit_create"))],
)
async def shorten_url(
    request: Request,
    long_url: Annotated[str, Form()],
    links: Links,
    custom_url: Annotated[str | None, Form()] = None,
) -> HTMLResponse:
    try:
        created = await links.create(long_url, custom_url)
    except ServiceError as exc:
        return templates.TemplateResponse(
            request,
            "short.html",
            {"error": exc.message, "long_url": long_url, "custom_url": custom_url or ""},
            status_code=exc.status_code,
        )
    code = created.link.short_url
    return templates.TemplateResponse(
        request,
        "shortened.html",
        {
            "short_url": code,
            "short_link": full_short_link(request, code),
            "edit_key": created.edit_key,
        },
    )


@url_router.get("/download-qrcode", response_class=HTMLResponse)
async def download_qr_code_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "download_qrcode.html")


@url_router.get("/qrcode", dependencies=[Depends(rate_limit("qr", "rate_limit_qr"))])
async def download_qr_code(url: str) -> Response:
    # The app's own short links are fine to encode here, unlike as a link destination.
    try:
        check_destination(url, own_hosts=set())
    except ServiceError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    return Response(
        content=generate_qr_code(url),
        media_type="image/png",
        headers={"Content-Disposition": "attachment; filename=qr_code.png"},
    )


@url_router.get("/analytics/{short_url}", response_class=HTMLResponse)
async def get_url_analytics(request: Request, short_url: str, links: Links) -> HTMLResponse:
    try:
        link = await links.get(short_url)
    except LinkNotFound as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    return templates.TemplateResponse(
        request,
        "analytics.html",
        {
            "short_url": short_url,
            "short_link": full_short_link(request, short_url),
            "long_url": link.long_url,
            "clicks": link.clicks,
            "click_data": await links.recent_clicks(link),
        },
    )


async def record_click(link_id: int, cache: LinkCache) -> None:
    """Runs after the redirect has been sent, with its own session."""
    async with SessionLocal() as session:
        await LinkService(session, cache, set()).record_click(link_id)


# Must stay last: it matches any single path segment.
@url_router.api_route("/{short_url}", methods=["GET", "HEAD"])
async def redirect_to_long_url(
    request: Request,
    short_url: str,
    links: Links,
    background: BackgroundTasks,
    cache: Annotated[LinkCache, Depends(get_cache)],
) -> RedirectResponse:
    try:
        target = await links.resolve(short_url)
    except LinkNotFound as exc:
        raise HTTPException(status_code=404, detail="URL not found") from exc

    # HEAD comes from link checkers and previewers, not people: answer it, don't count it.
    if request.method == "GET":
        background.add_task(record_click, target.id, cache)

    # 302, not 301: browsers would cache a 301 forever, so later clicks would go
    # uncounted and an edited destination would never take effect.
    return RedirectResponse(target.url, status_code=status.HTTP_302_FOUND)
