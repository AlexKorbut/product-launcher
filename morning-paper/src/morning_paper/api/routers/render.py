"""Stateless render endpoint: RenderDocument (or fields) -> PDF.

No user, no DB — pure document-in, PDF-out. RenderError propagates to the app's
502 handler.
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends

from ...models import GridPlan, Story
from ...render.document import build_render_document
from ...render.renderer import NodeRenderer
from ...models import RenderDocument
from ..deps import get_store
from ..schemas import RenderRequest, RenderResponse

router = APIRouter(tags=["render"])


@router.post("/render", response_model=RenderResponse)
def render(req: RenderRequest, store=Depends(get_store)) -> RenderResponse:
    if req.document is not None:
        doc = RenderDocument.model_validate(req.document)
    else:
        grid_plan = (
            GridPlan.model_validate(req.grid_plan)
            if req.grid_plan is not None
            else GridPlan()
        )
        doc = build_render_document(
            issue_id=uuid.uuid4().hex,
            theme_id=req.theme_id or "times-classic",
            locale=req.locale,
            title=req.title or "The Morning Paper",
            stories=[Story.model_validate(s) for s in (req.stories or [])],
            grid_plan=grid_plan,
        )

    key = f"renders/{uuid.uuid4().hex}.pdf"
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "render.pdf"
        # RenderError propagates -> handled as 502 by the app.
        result = NodeRenderer().render(doc, out_path=out_path)
        store.put_file(key, str(out_path), content_type="application/pdf")

    return RenderResponse(
        pdf_url=store.url(key),
        page_count=result.page_count,
        warnings=result.warnings,
    )
