"""
Timezone utilities — all times stored as UTC, converted to local for display.
Default: Asia/Kolkata (IST).
"""

from datetime import datetime
from zoneinfo import ZoneInfo

DEFAULT_TZ = ZoneInfo("Asia/Kolkata")


def utc_now():
    """Get current UTC time (timezone-aware)."""
    return datetime.utcnow()


def to_local(dt, tz=None):
    """Convert a naive UTC datetime to local timezone string."""
    if dt is None:
        return None
    tz = tz or DEFAULT_TZ
    # Assume dt is naive UTC — attach UTC then convert
    utc_dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    local_dt = utc_dt.astimezone(tz)
    return local_dt.strftime("%d-%m-%Y %I:%M %p")


def to_local_short(dt, tz=None):
    """Short format: HH:MM AM/PM."""
    if dt is None:
        return None
    tz = tz or DEFAULT_TZ
    utc_dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    local_dt = utc_dt.astimezone(tz)
    return local_dt.strftime("%I:%M %p")


def to_local_date(dt, tz=None):
    """Date-only format: DD-MM-YYYY."""
    if dt is None:
        return None
    tz = tz or DEFAULT_TZ
    utc_dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    local_dt = utc_dt.astimezone(tz)
    return local_dt.strftime("%d-%m-%Y")
