from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration, read from environment variables or a `.env` file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Any SQLAlchemy URL. Postgres: postgresql+psycopg://user:pass@host:5432/db
    database_url: str = "sqlite:///./scissors.sqlite"

    # Redis is part of the Compose stack now; caching and rate limits arrive in Phase 1.
    redis_url: str = "redis://localhost:6379/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
