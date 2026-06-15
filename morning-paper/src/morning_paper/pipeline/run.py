from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from .context import IssueContext
from .stages import s1_ingest, s2_profile, s3_retrieve, s4_rank, s5_editorial, s6_grid, s7_render, s8_deliver

STAGES = [s1_ingest, s2_profile, s3_retrieve, s4_rank, s5_editorial, s6_grid, s7_render, s8_deliver]


def new_issue_id() -> str:
    """Stable, sortable issue id (date + short random). Shared by run_issue and
    the job queue so a caller can know the id before the run starts."""
    return datetime.now(timezone.utc).strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:6]


def run_issue(
    user_id: str,
    *,
    theme_id: str | None = None,
    output_lang: str | None = None,
    out_dir: Path | None = None,
    from_stage: int = 1,
    until_stage: int = 8,
    feed_urls: list[str] = (),
    issue_id: str | None = None,
    **kwargs,
) -> IssueContext:
    # Fall back to the user's saved preferences when caller doesn't override.
    from .. import accounts

    acc = accounts.load(user_id)
    theme_id = theme_id or acc.theme or "times-classic"
    output_lang = output_lang or acc.output_lang or "ru"

    issue_id = issue_id or new_issue_id()
    work_dir = (out_dir or Path(".data")) / issue_id
    work_dir.mkdir(parents=True, exist_ok=True)

    ctx = IssueContext(
        user_id=user_id,
        issue_id=issue_id,
        theme_id=theme_id,
        output_lang=output_lang,
        work_dir=work_dir,
    )

    for stage_fn in STAGES[from_stage - 1 : until_stage]:
        ctx = stage_fn(ctx, feed_urls=feed_urls, **kwargs)

    # Best-effort issue record (no-op if no DB layer / engine available).
    try:
        from ..db.repository import record_issue

        record_issue(
            ctx.issue_id,
            user_id,
            ctx.theme_id,
            status="rendered" if ctx.pdf_path else "incomplete",
            pdf_key=str(ctx.pdf_path) if ctx.pdf_path else None,
        )
    except Exception:
        pass

    return ctx
