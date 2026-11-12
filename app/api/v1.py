"""Scissor API, version 1. Changing a shape here breaks clients: bump to /api/v2 instead."""

from datetime import date, datetime
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from ..database.models import URL
from ..deps import Links, rate_limit
from ..utils import generate_qr_code, generate_qr_svg
from .errors import ErrorResponse

router = APIRouter(prefix="/api/v1", tags=["Links"])

edit_key_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="EditKey",
    description="The `edit_key` returned once when the link was created.",
)
EditKey = Annotated[HTTPAuthorizationCredentials | None, Depends(edit_key_scheme)]

ERRORS: dict[int | str, dict[str, object]] = {
    status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid URL or code"},
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Edit key missing"},
    status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Edit key wrong"},
    status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "No such link"},
    status.HTTP_409_CONFLICT: {"model": ErrorResponse, "description": "Code already taken"},
    422: {"model": ErrorResponse, "description": "Request body or query is invalid"},
    status.HTTP_429_TOO_MANY_REQUESTS: {"model": ErrorResponse, "description": "Rate limited"},
}


def errors(*codes: int) -> dict[int | str, dict[str, object]]:
    # 422 is always possible, and always in our error format rather than FastAPI's default.
    return {code: ERRORS[code] for code in sorted({*codes, 422})}


# -- schemas ------------------------------------------------------------------------------


class LinkCreate(BaseModel):
    url: str = Field(description="Where the short link should go (http or https).")
    code: str | None = Field(
        default=None,
        description="Custom code: 3-32 letters, digits, hyphens or underscores. "
        "Leave out for a random 6-character code.",
    )


class LinkUpdate(BaseModel):
    url: str = Field(description="New destination for the short link.")


class Link(BaseModel):
    code: str
    short_url: str
    url: str
    created_at: datetime | None


class CreatedLink(Link):
    edit_key: str = Field(
        description="Secret needed to edit, delete or see stats for this link. "
        "Shown only once: store it now."
    )


class DayCount(BaseModel):
    date: date
    clicks: int


class LinkStats(BaseModel):
    code: str
    total_clicks: int
    last_clicked_at: datetime | None
    daily: list[DayCount] = Field(description="Clicks per UTC day for the last 30 days.")


class QRFormat(str, Enum):
    png = "png"
    svg = "svg"


def to_link(request: Request, link: URL) -> Link:
    return Link(
        code=link.short_url,
        short_url=str(request.base_url) + link.short_url,
        url=link.long_url,
        created_at=link.created_at,
    )


def key_of(credentials: HTTPAuthorizationCredentials | None) -> str | None:
    return credentials.credentials if credentials else None


# -- routes -------------------------------------------------------------------------------


@router.post(
    "/links",
    status_code=status.HTTP_201_CREATED,
    response_model=CreatedLink,
    responses=errors(400, 409, 422, 429),
    dependencies=[Depends(rate_limit("create", "rate_limit_create"))],
    summary="Create a short link",
)
async def create_link(body: LinkCreate, request: Request, links: Links) -> CreatedLink:
    created = await links.create(body.url, body.code)
    return CreatedLink(**to_link(request, created.link).model_dump(), edit_key=created.edit_key)


@router.get(
    "/links/{code}",
    response_model=Link,
    responses=errors(404),
    summary="Look up a short link",
)
async def get_link(code: str, request: Request, links: Links) -> Link:
    return to_link(request, await links.get(code))


@router.patch(
    "/links/{code}",
    response_model=Link,
    responses=errors(400, 401, 403, 404, 422, 429),
    dependencies=[Depends(rate_limit("manage", "rate_limit_manage"))],
    summary="Change where a short link goes",
)
async def update_link(
    code: str, body: LinkUpdate, request: Request, links: Links, key: EditKey
) -> Link:
    return to_link(request, await links.update_destination(code, key_of(key), body.url))


@router.delete(
    "/links/{code}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=errors(401, 403, 404, 429),
    dependencies=[Depends(rate_limit("manage", "rate_limit_manage"))],
    summary="Delete a short link and its click history",
)
async def delete_link(code: str, links: Links, key: EditKey) -> Response:
    await links.delete(code, key_of(key))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/links/{code}/stats",
    response_model=LinkStats,
    responses=errors(401, 403, 404, 429),
    dependencies=[Depends(rate_limit("manage", "rate_limit_manage"))],
    summary="Click statistics for a short link",
)
async def link_stats(code: str, links: Links, key: EditKey) -> LinkStats:
    stats = await links.stats(code, key_of(key))
    return LinkStats(
        code=stats.link.short_url,
        total_clicks=stats.total_clicks,
        last_clicked_at=stats.last_clicked_at,
        daily=[DayCount(date=d.day, clicks=d.clicks) for d in stats.daily],
    )


@router.get(
    "/links/{code}/qr",
    responses={
        200: {"content": {"image/png": {}, "image/svg+xml": {}}, "description": "QR code"},
        **errors(404, 422, 429),
    },
    response_class=Response,
    dependencies=[Depends(rate_limit("qr", "rate_limit_qr"))],
    summary="QR code for a short link",
)
async def link_qr(
    code: str, request: Request, links: Links, format: QRFormat = QRFormat.png
) -> Response:
    link = await links.get(code)
    short_url = str(request.base_url) + link.short_url
    if format is QRFormat.svg:
        return Response(generate_qr_svg(short_url), media_type="image/svg+xml")
    return Response(generate_qr_code(short_url), media_type="image/png")
