from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

PARIS_TZ = ZoneInfo("Europe/Paris")


def utcnow() -> datetime:
    """Return the current timezone-aware UTC datetime.

    ## Parameters
        - None.

    ## Returns
        The current UTC datetime with timezone information.
    """

    return datetime.now(tz=UTC)


def parse_duration_to_timedelta(raw_duration: str) -> timedelta:
    """Parse a compact duration string into a Python timedelta.

    ## Parameters
        - raw_duration: Human-readable duration like 30m, 2h, or 7d.

    ## Returns
        A timedelta representing the parsed duration.
    """

    raw_duration = raw_duration.strip().lower()
    if not raw_duration:
        raise ValueError("Duration cannot be empty.")

    multiplier = raw_duration[-1]
    value = int(raw_duration[:-1])
    if multiplier == "m":
        return timedelta(minutes=value)
    if multiplier == "h":
        return timedelta(hours=value)
    if multiplier == "d":
        return timedelta(days=value)
    raise ValueError("Unsupported duration format. Use m, h or d suffix.")


def format_datetime(dt: datetime) -> str:
    """Format a datetime into a compact Europe/Paris string for Discord messages and logs.

    ## Parameters
        - dt: Datetime object to render for Discord display.

    ## Returns
        A compact timestamp string in Paris time.
    """

    return dt.astimezone(PARIS_TZ).strftime("%Y-%m-%d %H:%M Europe/Paris")
