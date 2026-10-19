"""Coaching clock.

Class dates and clock times are Asia/Kolkata wall-clock values. They are not
converted to UTC. Account timestamps elsewhere in the app stay timezone-aware UTC.
The app has no per-user timezone.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

COACHING_TIME_ZONE = ZoneInfo("Asia/Kolkata")


def coaching_today() -> date:
    return datetime.now(COACHING_TIME_ZONE).date()
