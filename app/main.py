from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .database import models
from .database.db import engine
from .routers.url import url_router

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Scissor")

app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
app.include_router(url_router)
