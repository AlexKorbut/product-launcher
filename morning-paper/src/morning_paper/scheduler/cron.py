from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def next_run_local(
    hour: int, minute: int, tz: str, *, now: datetime | None = None
) -> datetime:
    """Next occurrence of hour:minute in the given IANA timezone (tz-aware)."""
    zone = ZoneInfo(tz)
    now = now.astimezone(zone) if now is not None else datetime.now(zone)
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def cron_expr(hour: int, minute: int) -> str:
    """Daily crontab expression for hour:minute."""
    return f"{minute} {hour} * * *"


class IssueScheduler:
    """Optional APScheduler-backed runner for nightly issue jobs."""

    def __init__(self) -> None:
        try:
            from apscheduler.schedulers.background import BackgroundScheduler

            self._scheduler = BackgroundScheduler()
            self._available = True
        except ImportError:
            self._scheduler = None
            self._available = False

    def start(self) -> None:
        if not self._available:
            raise RuntimeError(
                "apscheduler not installed; run `pip install apscheduler` "
                "or use system cron with cron_expr()."
            )
        self._scheduler.start()

    def schedule_user(self, user_id, *, hour, minute, tz, job) -> None:
        if not self._available:
            raise RuntimeError(
                "apscheduler not installed; run `pip install apscheduler` "
                "or use system cron with cron_expr()."
            )
        from apscheduler.triggers.cron import CronTrigger

        self._scheduler.add_job(
            job,
            CronTrigger(hour=hour, minute=minute, timezone=tz),
            id=str(user_id),
            replace_existing=True,
        )
