from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from validators import url as validate_url

from ..database.db import get_db
from ..database.models import URL, Click
from ..templates import templates
from ..utils import generate_qr_code, generate_short_url, is_valid_custom_code

MAX_CODE_ATTEMPTS = 10

url_router = APIRouter(tags=["URLs"])

DbSession = Annotated[Session, Depends(get_db)]

# Handlers that touch the database are plain `def`: the session is synchronous, so FastAPI
# runs them in its thread pool instead of blocking the event loop.


def full_short_link(request: Request, code: str) -> str:
    return str(request.base_url) + code


def find_url(db: Session, code: str) -> URL | None:
    return db.scalars(select(URL).where(URL.short_url == code)).first()


def insert_url(db: Session, long_url: str, code: str) -> bool:
    """Insert a link; return False if the code is already taken.

    The unique constraint on `short_url` is the source of truth, so two requests racing for
    the same code can't both succeed and neither gets a 500.
    """
    db.add(URL(long_url=long_url, short_url=code, clicks=0))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return False
    return True


@url_router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")


@url_router.get("/url", response_class=HTMLResponse)
async def shorten_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "short.html")


@url_router.post("/shorten", response_class=HTMLResponse)
def shorten_url(
    request: Request,
    long_url: Annotated[str, Form()],
    db: DbSession,
    custom_url: Annotated[str | None, Form()] = None,
) -> HTMLResponse:
    if not validate_url(long_url):
        raise HTTPException(status_code=400, detail="URL is not valid")

    custom_url = (custom_url or "").strip()
    if custom_url:
        if not is_valid_custom_code(custom_url):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Custom link must be 3-32 letters, digits, hyphens or underscores, "
                    "and not a reserved name"
                ),
            )
        if not insert_url(db, long_url, custom_url):
            raise HTTPException(status_code=400, detail="Custom link already in use")
        short_url = custom_url
    else:
        for _ in range(MAX_CODE_ATTEMPTS):
            short_url = generate_short_url()
            if insert_url(db, long_url, short_url):
                break
        else:
            raise HTTPException(
                status_code=503, detail="Could not generate a free short link; try again"
            )

    return templates.TemplateResponse(
        request,
        "shortened.html",
        {"short_url": short_url, "short_link": full_short_link(request, short_url)},
    )


@url_router.get("/download-qrcode", response_class=HTMLResponse)
async def download_qr_code_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "download_qrcode.html")


@url_router.get("/qrcode")
async def download_qr_code(url: str) -> Response:
    if not validate_url(url):
        raise HTTPException(status_code=400, detail="URL is not valid")
    return Response(
        content=generate_qr_code(url),
        media_type="image/png",
        headers={"Content-Disposition": "attachment; filename=qr_code.png"},
    )


@url_router.get("/analytics/{short_url}", response_class=HTMLResponse)
def get_url_analytics(request: Request, short_url: str, db: DbSession) -> HTMLResponse:
    db_url = find_url(db, short_url)
    if not db_url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    click_data = db.scalars(
        select(Click).where(Click.url_id == db_url.id).order_by(Click.created_at.desc())
    ).all()
    return templates.TemplateResponse(
        request,
        "analytics.html",
        {
            "short_url": short_url,
            "short_link": full_short_link(request, short_url),
            "long_url": db_url.long_url,
            "clicks": db_url.clicks,
            "click_data": click_data,
        },
    )


# Must stay last: it matches any single path segment.
@url_router.api_route("/{short_url}", methods=["GET", "HEAD"])
def redirect_to_long_url(request: Request, short_url: str, db: DbSession) -> RedirectResponse:
    db_url = find_url(db, short_url)
    if not db_url:
        raise HTTPException(status_code=404, detail="URL not found")

    # HEAD comes from link checkers and previewers, not people: answer it, don't count it.
    if request.method == "GET":
        # Increment in SQL so concurrent clicks can't overwrite each other.
        db.execute(
            update(URL).where(URL.id == db_url.id).values(clicks=func.coalesce(URL.clicks, 0) + 1)
        )
        db.add(Click(url_id=db_url.id))
        db.commit()

    return RedirectResponse(db_url.long_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
