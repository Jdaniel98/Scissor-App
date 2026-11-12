import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine

ROOT = Path(__file__).resolve().parent.parent

# Point the app at throwaway stores before it is imported. TEST_DATABASE_URL runs the suite
# on Postgres and TEST_REDIS_URL on Redis (CI does both); otherwise SQLite and memory.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite:///./test_scissors.sqlite")
TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL", "")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["REDIS_URL"] = TEST_REDIS_URL
# Generous limits so ordinary tests never trip them; rate-limit tests lower them.
os.environ["RATE_LIMIT_CREATE"] = "1000/minute"
os.environ["RATE_LIMIT_MANAGE"] = "1000/minute"
os.environ["RATE_LIMIT_QR"] = "1000/minute"

from app.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402


def alembic_config() -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", get_settings().database_url)
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
def sync_engine(migrated_db: Config) -> Iterator[Engine]:
    """A plain synchronous engine for tests to inspect the database directly."""
    engine = create_engine(get_settings().database_url)
    yield engine
    engine.dispose()


@pytest.fixture()
def client(migrated_db: Config) -> Iterator[TestClient]:
    with TestClient(app, follow_redirects=False) as test_client:
        # Redis outlives a test; start every test with an empty cache and fresh limits.
        test_client.portal.call(app.state.cache.clear)  # type: ignore[union-attr]
        test_client.portal.call(app.state.limiter.reset)  # type: ignore[union-attr]
        yield test_client


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if TEST_DATABASE_URL.startswith("sqlite"):
        for suffix in ("", "-wal", "-shm"):
            Path(f"test_scissors.sqlite{suffix}").unlink(missing_ok=True)
