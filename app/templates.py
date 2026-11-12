from datetime import datetime, timezone
from pathlib import Path

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def format_utc(value: datetime | None) -> str:
    """Render a timestamp in UTC. SQLite hands back naive datetimes, which are already UTC."""
    if value is None:
        return ""
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc)
    return value.strftime("%Y-%m-%d %H:%M:%S UTC")


templates.env.filters["utc"] = format_utc
