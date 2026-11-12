import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent

# Point the app at a throwaway database before it is imported. Set TEST_DATABASE_URL to run
# the suite against Postgres instead (CI does).
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite:///./test_scissors.sqlite")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.database.db import engine  # noqa: E402
from app.main import app  # noqa: E402


def alembic_config() -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    return config


@pytest.fixture()
def migrated_db() -> Iterator[Config]:
    """A database built by the migrations, exactly as production gets it."""
    config = alembic_config()
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield config
    command.downgrade(config, "base")


@pytest.fixture()
def client(migrated_db: Config) -> Iterator[TestClient]:
    with TestClient(app, follow_redirects=False) as test_client:
        yield test_client


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    engine.dispose()
    if TEST_DATABASE_URL.startswith("sqlite"):
        Path("test_scissors.sqlite").unlink(missing_ok=True)
