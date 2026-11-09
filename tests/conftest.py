import os

import pytest
from fastapi.testclient import TestClient

# Point the app at a throwaway database before it is imported.
os.environ["DATABASE_URL"] = "sqlite:///./test_scissors.sqlite"

from app.database.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app, follow_redirects=False) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)


def pytest_sessionfinish(session, exitstatus):
    engine.dispose()
    if os.path.exists("test_scissors.sqlite"):
        os.remove("test_scissors.sqlite")
