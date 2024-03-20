from fastapi import Request, HTTPException, Depends, APIRouter, status, Form
from fastapi.responses import RedirectResponse, FileResponse, HTMLResponse


from typing import Annotated

from validators import url as validate_url
from sqlalchemy.orm import Session


from ..templates import templates
from ..utils import generate_short_url, generate_qr_code
from ..database.db import get_db
from ..database.models import URL, Click

url_router = APIRouter(
    tags=["URLs"]
)


@url_router.get("/url")
async def index(request: Request):
    from ..main import templates
    # Render the index.html template
    return templates.TemplateResponse("short.html", {"request": request})


@url_router.post("/shorten")
async def shorten_url(
        request: Request,
        long_url: Annotated[str, Form()],
        custom_url: str = Form(None),
        db: Session = Depends(get_db)
):
    if not validate_url(long_url):
        raise HTTPException(status_code=400, detail="URL is not valid")

    if custom_url:
        existing_url = db.query(URL).filter(URL.short_url == custom_url).first()
        if existing_url:
            raise HTTPException(status_code=400, detail="Custom link already in use")
        short_url = custom_url
    else:
        short_url = generate_short_url()

    # Create a new URL record
    url_link = URL(
        long_url=long_url,
        short_url=short_url,
        clicks=0  # Assuming initial click count is 0
    )

    db.add(url_link)
    db.commit()
    db.refresh(url_link)


    return templates.TemplateResponse("shortened.html", {"request": request, "short_url": short_url})


@url_router.get("/urls", response_class=HTMLResponse)
async def all_urls(request: Request, db: Session = Depends(get_db)):
    urls = db.query(URL).all()

    return templates.TemplateResponse("history.html", {"request": request, "urls": urls})

    # return urls


@url_router.get("/download-qrcode")
async def download_qr_code_form(request: Request):
    return templates.TemplateResponse("download_qrcode.html", {"request": request})


@url_router.get("/qrcode")
async def download_qr_code(url: str):
    qr_code_path = generate_qr_code(url)
    return FileResponse(
        qr_code_path,
        media_type="image/png",
        headers={"Content-Disposition": "attachment; filename=qr_code.png"}
    )


@url_router.get("/{short_url}")
async def redirect_to_long_url(short_url: str, db: Session = Depends(get_db)):
    original_url = db.query(URL).filter(URL.short_url == short_url).first()
    if original_url:
        original_url.clicks += 1
        clicks = Click(url_id=original_url.id)
        db.add(clicks)
        db.commit()
        db.refresh(clicks)
        return RedirectResponse(original_url.long_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    else:
        raise HTTPException(status_code=404, detail="URL not found")


@url_router.get("/analytics/{short_url}", response_class=HTMLResponse)
async def get_url_analytics(request: Request, short_url: str, db: Session = Depends(get_db)):
    db_url = db.query(URL).filter(URL.short_url == short_url).first()
    click_data = db.query(Click).all()
    if db_url:
        # Render analytics page with total click count
        return templates.TemplateResponse(
            "analytics.html",
            {
                "request": request,
                "short_url": short_url,
                "clicks": db_url.clicks,
                "click_data": click_data
            }
        )
    else:
        raise HTTPException(status_code=404, detail="Short URL not found")
