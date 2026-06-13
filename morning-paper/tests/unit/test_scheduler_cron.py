from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from morning_paper.scheduler import cron_expr, next_run_local


def test_cron_expr():
    assert cron_expr(5, 30) == "30 5 * * *"


def test_next_run_today():
    tz = "Europe/Moscow"
    now = datetime(2026, 6, 13, 4, 0, tzinfo=ZoneInfo(tz))
    nxt = next_run_local(5, 0, tz, now=now)
    assert nxt > now
    assert nxt.hour == 5
    assert nxt.date() == now.date()  # today


def test_next_run_tomorrow():
    tz = "Europe/Moscow"
    now = datetime(2026, 6, 13, 6, 0, tzinfo=ZoneInfo(tz))
    nxt = next_run_local(5, 0, tz, now=now)
    assert nxt > now
    assert nxt.hour == 5
    assert nxt.date() > now.date()  # tomorrow
