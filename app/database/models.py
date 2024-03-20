from sqlalchemy import Boolean,DateTime, Column, Integer, String, ForeignKey, text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .db import Base


class URL(Base):
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, nullable=False)
    long_url = Column(String, nullable=False)
    short_url = Column(String, unique=True, nullable=False)
    clicks = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    

    

    click = relationship("Click", back_populates="url")


class Click(Base):
    __tablename__ = "clicks"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    url_id = Column(Integer, ForeignKey("urls.id"))

    url = relationship("URL", back_populates="click")

