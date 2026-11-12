from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class URL(Base):
    __tablename__ = "urls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    long_url: Mapped[str] = mapped_column(String)
    short_url: Mapped[str] = mapped_column(String, unique=True)
    clicks: Mapped[int | None] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )

    click_events: Mapped[list["Click"]] = relationship(back_populates="url")


class Click(Base):
    __tablename__ = "clicks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    url_id: Mapped[int | None] = mapped_column(ForeignKey("urls.id"), index=True)

    url: Mapped["URL | None"] = relationship(back_populates="click_events")
