from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routers.url import url_router

# The schema is managed by Alembic: run `alembic upgrade head` before starting the app.
app = FastAPI(title="Scissor")

app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
app.include_router(url_router)
