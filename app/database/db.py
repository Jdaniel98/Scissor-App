from collections.abc import AsyncIterator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from ..config import get_settings

settings = get_settings()
IS_SQLITE = settings.database_url.startswith("sqlite")

engine = create_async_engine(
    settings.async_database_url,
    pool_pre_ping=not IS_SQLITE,
    connect_args={"timeout": 15} if IS_SQLITE else {},
)

if IS_SQLITE:

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _record):  # type: ignore[no-untyped-def]
        # WAL lets readers and the writer work at once; busy_timeout waits out short locks.
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=15000")
        cursor.close()


SessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
