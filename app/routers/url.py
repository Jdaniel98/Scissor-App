from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session
from validators import url as validate_url

from ..database.db import get_db
from ..database.models import URL, Click
from ..templates import templates
from ..utils import generate_qr_code, generate_short_url, is_valid_custom_code

MAX_CODE_ATTEMPTS = 10

url_router = APIRouter(tags=["URLs"])


def full_short_link(request: Request, code: str) -> str:
    return str(request.base_url) + code


@url_router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html")


@url_router.get("/url", response_class=HTMLResponse)
async def shorten_form(request: Request):
    return templates.TemplateResponse(request, "short.html")


@url_router.post("/shorten", response_class=HTMLResponse)
async def shorten_url(
    request: Request,
    long_url: Annotated[str, Form()],
    custom_url: Annotated[Optional[str], Form()] = None,
    db: Session = Depends(get_db),
):
    if not validate_url(long_url):
        raise HTTPException(status_code=400, detail="URL is not valid")

    custom_url = (custom_url or "").strip()
    if custom_url:
        if not is_valid_custom_code(custom_url):
            raise HTTPException(
                status_code=400,
                detail="Custom link must be 3-32 letters, digits, hyphens or underscores, and not a reserved name",
            )
        if db.query(URL).filter(URL.short_url == custom_url).first():
            raise HTTPException(status_code=400, detail="Custom link already in use")
        short_url = custom_url
    else:
        for _ in range(MAX_CODE_ATTEMPTS):
            short_url = generate_short_url()
            if not db.query(URL).filter(URL.short_url == short_url).first():
                break
        else:
            raise HTTPException(status_code=503, detail="Could not generate a free short link; try again")

    db.add(URL(long_url=long_url, short_url=short_url, clicks=0))
    db.commit()

    return templates.TemplateResponse(
        request,
        "shortened.html",
        {"short_url": short_url, "short_link": full_short_link(request, short_url)},
    )


@url_router.get("/urls", response_class=HTMLResponse)
async def all_urls(request: Request, db: Session = Depends(get_db)):
    urls = db.query(URL).order_by(URL.created_at.desc()).all()
    return templates.TemplateResponse(request, "history.html", {"urls": urls})


@url_router.get("/download-qrcode", response_class=HTMLResponse)
async def download_qr_code_form(request: Request):
    return templates.TemplateResponse(request, "download_qrcode.html")


@url_router.get("/qrcode")
async def download_qr_code(url: str):
    if not validate_url(url):
        raise HTTPException(status_code=400, detail="URL is not valid")
    return Response(
        content=generate_qr_code(url),
        media_type="image/png",
        headers={"Content-Disposition": "attachment; filename=qr_code.png"},
    )


@url_router.get("/analytics/{short_url}", response_class=HTMLResponse)
async def get_url_analytics(request: Request, short_url: str, db: Session = Depends(get_db)):
    db_url = db.query(URL).filter(URL.short_url == short_url).first()
    if not db_url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    click_data = (
        db.query(Click).filter(Click.url_id == db_url.id).order_by(Click.created_at.desc()).all()
    )
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
@url_router.get("/{short_url}")
async def redirect_to_long_url(short_url: str, db: Session = Depends(get_db)):
    original_url = db.query(URL).filter(URL.short_url == short_url).first()
    if not original_url:
        raise HTTPException(status_code=404, detail="URL not found")

    original_url.clicks += 1
    db.add(Click(url_id=original_url.id))
    db.commit()
    return RedirectResponse(original_url.long_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
