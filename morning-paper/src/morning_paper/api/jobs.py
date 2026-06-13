"""Issue generation jobs.

In-memory job tracking + the worker body that runs the pipeline and stores the
PDF. Everything is best-effort and guarded so a missing DB never breaks the API.

FUTURE: this body becomes a Celery task; swap BackgroundTasks.add_task for
.delay(). The JOBS dict becomes a result backend (Redis/DB) so status survives
process restarts and is shared across workers.
"""

from __future__ import annotations

from typing import Any

# job_id -> {status, issue_id, pdf_key, error}
JOBS: dict[str, dict[str, Any]] = {}


def run_issue_job(job_id: str, user_id: str, params: dict) -> None:
    """Run the full pipeline for a user and persist the resulting PDF."""
    from ..pipeline.run import run_issue
    from ..store import get_object_store

    JOBS[job_id] = {"status": "running", "issue_id": None, "pdf_key": None, "error": None}
    try:
        ctx = run_issue(user_id, **params)
        pdf_key: str | None = None
        if ctx.pdf_path:
            store = get_object_store()
            pdf_key = f"issues/{ctx.issue_id}/issue.pdf"
            store.put_file(pdf_key, str(ctx.pdf_path), content_type="application/pdf")
            try:
                from ..db.repository import record_issue

                record_issue(
                    ctx.issue_id, user_id, ctx.theme_id, status="rendered", pdf_key=pdf_key
                )
            except Exception:
                pass
        JOBS[job_id] = {
            "status": "done" if pdf_key else "incomplete",
            "issue_id": ctx.issue_id,
            "theme_id": ctx.theme_id,
            "pdf_key": pdf_key,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001 — surface any pipeline failure as job error
        JOBS[job_id] = {
            "status": "error",
            "issue_id": None,
            "pdf_key": None,
            "error": str(exc),
        }


def issue_status(issue_id_or_job: str) -> dict:
    """Best-effort status for an issue or job id.

    Prefers the durable DB issue row when a `get_issue` repository call exists;
    otherwise falls back to the in-memory JOBS, keyed by either job id or the
    issue id stored on completion.
    """
    # Durable source of truth, if the repository exposes it.
    try:
        from ..db.repository import get_issue  # type: ignore[attr-defined]

        row = get_issue(issue_id_or_job)
        if row:
            return {
                "issue_id": row.get("id") or issue_id_or_job,
                "status": row.get("status", "unknown"),
                "theme_id": row.get("theme_id"),
                "pdf_key": row.get("pdf_key"),
            }
    except Exception:
        pass

    # In-memory fallback: direct job id, or a finished job carrying this issue_id.
    job = JOBS.get(issue_id_or_job)
    if job is None:
        for j in JOBS.values():
            if j.get("issue_id") == issue_id_or_job:
                job = j
                break
    if job is not None:
        return {
            "issue_id": job.get("issue_id") or issue_id_or_job,
            "status": job.get("status", "unknown"),
            "theme_id": job.get("theme_id"),
            "pdf_key": job.get("pdf_key"),
        }
    return {"issue_id": issue_id_or_job, "status": "unknown", "theme_id": None, "pdf_key": None}
