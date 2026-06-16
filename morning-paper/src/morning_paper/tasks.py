"""Celery wiring for the nightly/async issue pipeline.

Optional: `celery` and a broker (Redis) are only needed to run a worker. If
neither is configured, `celery_enabled()` is False and the API falls back to
in-process execution — the same `execute_issue` body runs either way.

Run a worker with:  celery -A morning_paper.tasks worker --loglevel=info
(or: morning-paper worker), with MP_BROKER_URL set.
"""

from __future__ import annotations


def _broker_urls() -> tuple[str | None, str | None]:
    from .config import get_settings

    s = get_settings().secrets
    return s.mp_broker_url, (s.mp_result_backend or s.mp_broker_url)


def _build_app():
    try:
        from celery import Celery
    except ImportError:
        return None
    broker, backend = _broker_urls()
    if not broker:
        return None
    app = Celery("morning_paper", broker=broker, backend=backend)
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        task_track_started=True,
        timezone="UTC",
    )
    return app


celery_app = _build_app()


def celery_enabled() -> bool:
    """True when Celery is installed AND a broker is configured."""
    return celery_app is not None


if celery_app is not None:

    @celery_app.task(name="morning_paper.run_issue")
    def run_issue_task(user_id: str, params: dict | None = None, issue_id: str | None = None) -> dict:
        from .jobs import execute_issue

        return execute_issue(user_id, params, issue_id=issue_id)

else:

    def run_issue_task(*_args, **_kwargs):  # type: ignore[misc]
        raise RuntimeError(
            "Celery is not configured. Install morning-paper[worker] and set MP_BROKER_URL."
        )
