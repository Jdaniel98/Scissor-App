from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration, read from environment variables or a `.env` file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Any SQLAlchemy URL. Postgres: postgresql+psycopg://user:pass@host:5432/db
    database_url: str = "sqlite:///./scissors.sqlite"

    # Redis for the redirect cache and rate limits. Empty = keep both in process memory,
    # which is fine for local runs and tests but not for more than one server.
    redis_url: str = ""

    # Rate limits per client IP, in the `limits` notation ("20/minute", "1000/day").
    rate_limit_create: str = "20/minute"
    rate_limit_manage: str = "60/minute"
    rate_limit_qr: str = "60/minute"

    # Seconds a code-to-URL mapping stays in the redirect cache.
    redirect_cache_ttl: int = 86400

    # Extra hostnames this app is served on (comma-separated), besides the one a request
    # arrives on. Links pointing at any of them are refused, so the app can't loop on itself.
    public_hosts: str = ""

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, url: str) -> str:
        """Point plain Postgres URLs at the psycopg 3 driver this app installs.

        Hosts such as Render hand out `postgres://` or `postgresql://` URLs, which SQLAlchemy
        would otherwise route to psycopg2.
        """
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url.removeprefix(prefix)
        return url

    @property
    def async_database_url(self) -> str:
        """The same database through an asyncio driver (psycopg 3 does both)."""
        if self.database_url.startswith("sqlite://"):
            return "sqlite+aiosqlite://" + self.database_url.removeprefix("sqlite://")
        return self.database_url

    @property
    def public_host_set(self) -> set[str]:
        return {h.strip().lower() for h in self.public_hosts.split(",") if h.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
