import pytest

from app.config import Settings


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("postgres://u:p@host:5432/db", "postgresql+psycopg://u:p@host:5432/db"),
        ("postgresql://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("sqlite:///./scissors.sqlite", "sqlite:///./scissors.sqlite"),
    ],
)
def test_database_url_uses_psycopg(given, expected):
    assert Settings(database_url=given).database_url == expected
