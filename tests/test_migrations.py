from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from app.database.db import Base


def test_migrations_match_models(sync_engine):
    with sync_engine.connect() as connection:
        context = MigrationContext.configure(connection)
        assert compare_metadata(context, Base.metadata) == []


def test_clicks_url_id_is_indexed(sync_engine):
    indexes = inspect(sync_engine).get_indexes("clicks")
    assert any(index["column_names"] == ["url_id"] for index in indexes)


def test_urls_has_edit_key_hash(sync_engine):
    columns = {column["name"] for column in inspect(sync_engine).get_columns("urls")}
    assert "edit_key_hash" in columns
