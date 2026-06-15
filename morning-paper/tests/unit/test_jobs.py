"""Async issue jobs: Celery gating, in-process fallback, failure handling."""

from __future__ import annotations

import importlib

import pytest

from morning_paper import jobs as core_jobs
from morning_paper.api import jobs as api_jobs


class _Bg:
    """Stand-in for FastAPI BackgroundTasks."""

    def __init__(self) -> None:
        self.tasks: list = []

    def add_task(self, fn, *args, **kwargs) -> None:
        self.tasks.append((fn, args, kwargs))


def test_celery_disabled_without_broker():
    from morning_paper.tasks import celery_enabled

    assert celery_enabled() is False


def test_submit_issue_falls_back_to_background(monkeypatch):
    calls = {}

    def fake_exec(user_id, params, *, issue_id=None):
        calls["args"] = (user_id, issue_id, params)
        return {"issue_id": issue_id, "status": "rendered", "theme_id": "t", "pdf_key": "k", "error": None}

    monkeypatch.setattr(core_jobs, "execute_issue", fake_exec)

    bg = _Bg()
    res = api_jobs.submit_issue("me", {"theme_id": "times-classic"}, background=bg)

    assert res["mode"] == "background"
    assert res["status"] == "queued"
    assert res["issue_id"]
    assert len(bg.tasks) == 1

    # Running the queued task drives the issue to a terminal state.
    fn, args, kwargs = bg.tasks[0]
    fn(*args, **kwargs)
    assert calls["args"][0] == "me"
    assert api_jobs.JOBS[res["issue_id"]]["status"] == "rendered"


def test_execute_issue_marks_failed_on_pipeline_error(monkeypatch):
    import morning_paper.pipeline.run as run_mod

    monkeypatch.setattr(run_mod, "run_issue", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))

    res = core_jobs.execute_issue("me", {"theme_id": "x"}, issue_id="iss-fail")
    assert res["status"] == "failed"
    assert res["issue_id"] == "iss-fail"
    assert "boom" in (res["error"] or "")


def test_celery_eager_roundtrip(monkeypatch):
    pytest.importorskip("celery")
    from morning_paper.config import get_settings

    monkeypatch.setenv("MP_BROKER_URL", "memory://")
    monkeypatch.setenv("MP_RESULT_BACKEND", "cache+memory://")
    get_settings.cache_clear()

    import morning_paper.tasks as tasks_mod

    tasks_mod = importlib.reload(tasks_mod)
    try:
        assert tasks_mod.celery_enabled()
        tasks_mod.celery_app.conf.task_always_eager = True
        tasks_mod.celery_app.conf.task_eager_propagates = True

        monkeypatch.setattr(
            core_jobs,
            "execute_issue",
            lambda u, p, *, issue_id=None: {"issue_id": issue_id or "x", "status": "rendered"},
        )
        result = tasks_mod.run_issue_task.delay("me", {"theme_id": "t"}, issue_id="iss-eager")
        assert result.get(timeout=5)["status"] == "rendered"
    finally:
        # Restore the no-broker module state for the rest of the suite.
        monkeypatch.delenv("MP_BROKER_URL", raising=False)
        monkeypatch.delenv("MP_RESULT_BACKEND", raising=False)
        get_settings.cache_clear()
        importlib.reload(tasks_mod)
