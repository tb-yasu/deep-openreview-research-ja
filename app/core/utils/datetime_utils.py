from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.config import settings


def get_current_time(
    timezone: str = settings.TIMEZONE,
    fmt: str = "%Y-%m-%d %H:%M:%S",
) -> str:
    return datetime.now(ZoneInfo(timezone)).strftime(fmt)
