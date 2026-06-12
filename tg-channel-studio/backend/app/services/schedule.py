"""Publishing slot calculation: spread posts_per_day across non-quiet hours."""
from datetime import datetime, timedelta, timezone

from app.models import Channel


def _is_quiet(hour: int, start: int, end: int) -> bool:
    if start == end:
        return False
    if start < end:  # e.g. 1..6
        return start <= hour < end
    return hour >= start or hour < end  # wraps midnight, e.g. 23..8


def active_hours(channel: Channel) -> list[int]:
    return [
        h for h in range(24)
        if not _is_quiet(h, channel.quiet_hours_start, channel.quiet_hours_end)
    ]


def next_slot(channel: Channel, after: datetime | None = None, taken: list[datetime] | None = None) -> datetime:
    """Next publishing slot in UTC, respecting quiet hours and per-day cadence."""
    tz = timezone(timedelta(minutes=channel.tz_offset_minutes))
    now_local = (after or datetime.now(timezone.utc)).astimezone(tz)
    hours = active_hours(channel)
    if not hours:
        hours = list(range(24))

    step = max(1, len(hours) // max(1, channel.posts_per_day))
    slot_hours = hours[::step][: channel.posts_per_day]
    taken_local = {t.astimezone(tz).replace(minute=0, second=0, microsecond=0) for t in (taken or [])}

    candidate = now_local.replace(minute=0, second=0, microsecond=0)
    for _ in range(24 * 14):  # search up to two weeks ahead
        candidate += timedelta(hours=1)
        if candidate.hour in slot_hours and candidate not in taken_local:
            return candidate.astimezone(timezone.utc)
    return (now_local + timedelta(hours=1)).astimezone(timezone.utc)
