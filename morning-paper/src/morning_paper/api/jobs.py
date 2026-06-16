"""Issue job submission + status for the API.

`submit_issue` enqueues a build on Celery when a broker is configured, otherwise
runs it in-process via FastAPI BackgroundTasks. Either way the work is the shared
`morning_paper.jobs.execute_issue` body, and durable status lives in the DB
`issues` row — so `issue_status` is correct across processes (a Celery worker's
result is visible to the web process).
"""

from __future__ import annotations

from typing import Any

# Fallback in-process status, used only when there is no DB layer to persist to.
# issue_id -> {status, issue_id, theme_id, pdf_key, error}
JOBS: dict[str, dict[str, Any]] = {}


def _run_in_process(issue_id: str, user_id: str, params: dict) -> None:
    from ..jobs import execute_issue

    JOBS[issue_id] = {"status": "running", "issue_id": issue_id, "theme_id": None, "pdf_key": None, "error": None}
    JOBS[issue_id] = execute_issue(user_id, params, issue_id=issue_id)


def submit_issue(user_id: str, params: dict, *, background=None) -> dict:
    """Enqueue an issue build. Returns {issue_id, status, mode}."""
    from ..pipeline.run import new_issue_id

    issue_id = new_issue_id()

    # Durable "queued" marker so status is visible before the worker starts.
    try:
        from ..db.repository import record_issue

        record_issue(issue_id, user_id, params.get("theme_id") or "pending", status="queued")
    except Exception:
        pass

    # Prefer Celery when a broker is configured.
    try:
        from ..tasks import celery_enabled, run_issue_task

        if celery_enabled():
            run_issue_task.delay(user_id, params, issue_id=issue_id)
            return {"issue_id": issue_id, "status": "queued", "mode": "celery"}
    except Exception:
        pass

    # Fallback: in-process background task (or synchronous if no scheduler given).
    JOBS[issue_id] = {"status": "queued", "issue_id": issue_id, "theme_id": None, "pdf_key": None, "error": None}
    if background is not None:
        background.add_task(_run_in_process, issue_id, user_id, params)
    else:
        _run_in_process(issue_id, user_id, params)
    return {"issue_id": issue_id, "status": "queued", "mode": "background"}


def issue_status(issue_id: str) -> dict:
    """Best-effort status. Durable DB row is the source of truth across processes;
    falls back to the in-memory JOBS map when no DB is available."""
    try:
        from ..db.repository import get_issue

        row = get_issue(issue_id)
        if row:
            return {
                "issue_id": row.get("id") or issue_id,
                "status": row.get("status", "unknown"),
                "theme_id": row.get("theme_id"),
                "pdf_key": row.get("pdf_key"),
            }
    except Exception:
        pass

    job = JOBS.get(issue_id)
    if job is not None:
        return {
            "issue_id": job.get("issue_id") or issue_id,
            "status": job.get("status", "unknown"),
            "theme_id": job.get("theme_id"),
            "pdf_key": job.get("pdf_key"),
        }
    return {"issue_id": issue_id, "status": "unknown", "theme_id": None, "pdf_key": None}
