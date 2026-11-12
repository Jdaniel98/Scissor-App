from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from app.database.db import Base, engine


def test_migrations_match_models(migrated_db):
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        assert compare_metadata(context, Base.metadata) == []


def test_clicks_url_id_is_indexed(migrated_db):
    indexes = inspect(engine).get_indexes("clicks")
    assert any(index["column_names"] == ["url_id"] for index in indexes)
