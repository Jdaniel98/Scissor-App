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


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("sqlite:///./scissors.sqlite", "sqlite+aiosqlite:///./scissors.sqlite"),
        ("postgresql://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
    ],
)
def test_async_database_url(given, expected):
    assert Settings(database_url=given).async_database_url == expected


def test_public_hosts_are_normalised():
    assert Settings(public_hosts=" Sciss.OR, ,www.sciss.or ").public_host_set == {
        "sciss.or",
        "www.sciss.or",
    }
