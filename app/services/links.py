"""Everything Scissor does with links. Routes parse input and shape output; this decides."""

import hashlib
import hmac
import re
import secrets
import string
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import URL, Click
from .cache import CachedLink, LinkCache
from .errors import (
    CodeTaken,
    EditKeyInvalid,
    EditKeyRequired,
    InvalidCode,
    LinkNotFound,
    NoFreeCode,
)
from .policy import check_destination

ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 6
MAX_CODE_ATTEMPTS = 10
STATS_DAYS = 30

# Custom links: 3-32 letters, digits, hyphens or underscores
CUSTOM_CODE_PATTERN = re.compile(r"[A-Za-z0-9_-]{3,32}")

# Paths the app serves itself; a short link with one of these names could never be reached
RESERVED_CODES = {
    "api",
    "url",
    "urls",
    "shorten",
    "qrcode",
    "download-qrcode",
    "analytics",
    "static",
    "docs",
    "redoc",
    "openapi.json",
    "favicon.ico",
    "robots.txt",
}


def generate_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def is_valid_custom_code(code: str) -> bool:
    return bool(CUSTOM_CODE_PATTERN.fullmatch(code)) and code.lower() not in RESERVED_CODES


def new_edit_key() -> str:
    return secrets.token_urlsafe(24)


def hash_edit_key(key: str) -> str:
    # Keys are 192 random bits, so a fast hash is enough; nothing here can be brute-forced.
    return hashlib.sha256(key.encode()).hexdigest()


@dataclass(frozen=True)
class CreatedLink:
    link: URL
    edit_key: str


@dataclass(frozen=True)
class DailyClicks:
    day: date
    clicks: int


@dataclass(frozen=True)
class LinkStats:
    link: URL
    total_clicks: int
    last_clicked_at: datetime | None
    daily: list[DailyClicks]


class LinkService:
    def __init__(self, session: AsyncSession, cache: LinkCache, own_hosts: set[str]) -> None:
        self.session = session
        self.cache = cache
        self.own_hosts = own_hosts

    # -- create -------------------------------------------------------------------------

    async def create(self, url: str, custom_code: str | None = None) -> CreatedLink:
        destination = check_destination(url, self.own_hosts)
        edit_key = new_edit_key()
        key_hash = hash_edit_key(edit_key)

        custom_code = (custom_code or "").strip()
        if custom_code:
            if not is_valid_custom_code(custom_code):
                raise InvalidCode(
                    "Custom link must be 3-32 letters, digits, hyphens or underscores, "
                    "and not a reserved name"
                )
            link = await self._insert(destination, custom_code, key_hash)
            if link is None:
                raise CodeTaken("Custom link already in use")
            return CreatedLink(link, edit_key)

        for _ in range(MAX_CODE_ATTEMPTS):
            link = await self._insert(destination, generate_code(), key_hash)
            if link is not None:
                return CreatedLink(link, edit_key)
        raise NoFreeCode("Could not generate a free short link; try again")

    async def _insert(self, destination: str, code: str, key_hash: str) -> URL | None:
        """Insert a link; None if the code is taken.

        The unique constraint on `short_url` decides, so two requests racing for one code
        can't both win and neither gets a 500.
        """
        link = URL(long_url=destination, short_url=code, clicks=0, edit_key_hash=key_hash)
        self.session.add(link)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            return None
        return link

    # -- read ---------------------------------------------------------------------------

    async def get(self, code: str) -> URL:
        link = await self.session.scalar(select(URL).where(URL.short_url == code))
        if link is None:
            raise LinkNotFound("Short link not found")
        return link

    async def resolve(self, code: str) -> CachedLink:
        """Where a short code points, from the cache when possible."""
        cached = await self.cache.get(code)
        if cached is not None:
            return cached
        link = await self.get(code)
        cached = CachedLink(id=link.id, url=link.long_url)
        await self.cache.set(code, cached)
        return cached

    async def recent_clicks(self, link: URL, limit: int = 100) -> list[Click]:
        rows = await self.session.scalars(
            select(Click)
            .where(Click.url_id == link.id)
            .order_by(Click.created_at.desc())
            .limit(limit)
        )
        return list(rows)

    async def stats(self, code: str, edit_key: str | None) -> LinkStats:
        link = await self.get_for_owner(code, edit_key)
        since = datetime.now(timezone.utc) - timedelta(days=STATS_DAYS - 1)
        start_day = since.date()

        stamps = await self.session.scalars(
            select(Click.created_at).where(
                Click.url_id == link.id,
                Click.created_at >= datetime.combine(start_day, datetime.min.time()),
            )
        )
        per_day: dict[date, int] = {}
        for stamp in stamps:
            if stamp is None:
                continue
            day = _as_utc(stamp).date()
            per_day[day] = per_day.get(day, 0) + 1

        last_clicked_at = await self.session.scalar(
            select(func.max(Click.created_at)).where(Click.url_id == link.id)
        )
        daily = [
            DailyClicks(day, per_day.get(day, 0))
            for day in (start_day + timedelta(days=i) for i in range(STATS_DAYS))
        ]
        return LinkStats(
            link=link,
            total_clicks=link.clicks or 0,
            last_clicked_at=_as_utc(last_clicked_at) if last_clicked_at else None,
            daily=daily,
        )

    # -- owner actions ------------------------------------------------------------------

    async def get_for_owner(self, code: str, edit_key: str | None) -> URL:
        link = await self.get(code)
        if not edit_key:
            raise EditKeyRequired("This needs the link's edit key")
        if link.edit_key_hash is None or not hmac.compare_digest(
            link.edit_key_hash, hash_edit_key(edit_key)
        ):
            raise EditKeyInvalid("Edit key doesn't match this link")
        return link

    async def update_destination(self, code: str, edit_key: str | None, url: str) -> URL:
        link = await self.get_for_owner(code, edit_key)
        link.long_url = check_destination(url, self.own_hosts)
        await self.session.commit()
        await self.cache.delete(code)
        return link

    async def delete(self, code: str, edit_key: str | None) -> None:
        link = await self.get_for_owner(code, edit_key)
        await self.session.execute(delete(Click).where(Click.url_id == link.id))
        await self.session.delete(link)
        await self.session.commit()
        await self.cache.delete(code)

    # -- clicks -------------------------------------------------------------------------

    async def record_click(self, link_id: int) -> None:
        # Increment in SQL so concurrent clicks can't overwrite each other.
        await self.session.execute(
            update(URL).where(URL.id == link_id).values(clicks=func.coalesce(URL.clicks, 0) + 1)
        )
        self.session.add(Click(url_id=link_id))
        await self.session.commit()


def _as_utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes, which are already UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
