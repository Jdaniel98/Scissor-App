from pydantic import BaseModel, HttpUrl
from typing_extensions import Optional


class URLBase(BaseModel):
    long_url: str
    custom_url: Optional[str] = None


class ShortenUrl(URLBase):
    clicks: Optional[int] = None
