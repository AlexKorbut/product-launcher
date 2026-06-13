from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from .context import IssueContext
from .stages import s1_ingest, s2_profile, s3_retrieve, s4_rank, s5_editorial, s6_grid, s7_render, s8_deliver

STAGES = [s1_ingest, s2_profile, s3_retrieve, s4_rank, s5_editorial, s6_grid, s7_render, s8_deliver]


def run_issue(
    user_id: str,
    *,
    theme_id: str = "times-classic",
    output_lang: str = "ru",
    out_dir: Path | None = None,
    from_stage: int = 1,
    until_stage: int = 8,
    feed_urls: list[str] = (),
    **kwargs,
) -> IssueContext:
    issue_id = datetime.now(timezone.utc).strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:6]
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

    return ctx
