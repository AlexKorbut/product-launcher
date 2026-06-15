"""Broker-agnostic issue execution.

`execute_issue` is the single body that runs the pipeline, stores the resulting
PDF in the object store, and records durable status in the DB. It is called both
by the Celery task (`tasks.run_issue_task`) and by the in-process FastAPI
fallback, so the two paths behave identically.

Everything is best-effort: a missing DB or object store degrades gracefully and
never turns a render failure into an unhandled crash.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _set_status(issue_id: str, user_id: str, theme_id: str, status: str, pdf_key: str | None = None) -> None:
    try:
        from .db.repository import record_issue

        record_issue(issue_id, user_id, theme_id, status=status, pdf_key=pdf_key)
    except Exception:
        # No DB layer / engine — status simply isn't durable. Fine for local dev.
        pass


def execute_issue(user_id: str, params: dict | None = None, *, issue_id: str | None = None) -> dict[str, Any]:
    """Run the full pipeline for a user, store the PDF, return a status dict.

    Returns: {issue_id, status, theme_id, pdf_key, error}.
    """
    from .pipeline.run import new_issue_id, run_issue
    from .store import get_object_store

    params = dict(params or {})
    issue_id = issue_id or new_issue_id()
    theme_hint = params.get("theme_id") or "pending"

    _set_status(issue_id, user_id, theme_hint, "running")

    try:
        ctx = run_issue(user_id, issue_id=issue_id, **params)
    except Exception as exc:  # noqa: BLE001 — surface any pipeline failure as job error
        logger.warning("issue %s failed: %s", issue_id, exc)
        _set_status(issue_id, user_id, theme_hint, "failed")
        return {"issue_id": issue_id, "status": "failed", "theme_id": theme_hint, "pdf_key": None, "error": str(exc)}

    pdf_key: str | None = None
    if ctx.pdf_path:
        try:
            store = get_object_store()
            pdf_key = f"issues/{ctx.issue_id}/issue.pdf"
            store.put_file(pdf_key, str(ctx.pdf_path), content_type="application/pdf")
        except Exception as exc:  # noqa: BLE001
            logger.warning("issue %s: storing PDF failed: %s", issue_id, exc)
            pdf_key = None

    status = "rendered" if pdf_key else "incomplete"
    _set_status(ctx.issue_id, user_id, ctx.theme_id, status, pdf_key)
    return {
        "issue_id": ctx.issue_id,
        "status": status,
        "theme_id": ctx.theme_id,
        "pdf_key": pdf_key,
        "error": None,
    }
