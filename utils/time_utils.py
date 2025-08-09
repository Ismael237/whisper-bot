from __future__ import annotations

from datetime import datetime, date, timezone


def get_utc_time() -> datetime:
    """Get current UTC time with timezone info."""
    return datetime.now(timezone.utc)


def get_utc_date() -> date:
    """Get current UTC date."""
    return get_utc_time().date()
