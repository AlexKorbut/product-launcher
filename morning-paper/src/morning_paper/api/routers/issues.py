"""Issue generation: enqueue a build, poll status, download the PDF."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from fastapi.responses import FileResponse

from ..deps import Principal, get_principal, get_store, require_owner
from ..jobs import issue_status, submit_issue
from ..schemas import CostOut, IssueCreate, IssueStatusOut, JobOut

router = APIRouter(tags=["issues"])


@router.post("/users/{user_id}/issues", status_code=202, response_model=JobOut)
def create_issue(
    user_id: str,
    body: IssueCreate,
    background: BackgroundTasks,
    principal: Principal = Depends(get_principal),
) -> JobOut:
    require_owner(principal, user_id)
    params: dict = {}
    if body.theme_id is not None:
        params["theme_id"] = body.theme_id
    if body.output_lang is not None:
        params["output_lang"] = body.output_lang
    if body.feed_urls:
        params["feed_urls"] = list(body.feed_urls)

    result = submit_issue(user_id, params, background=background)
    return JobOut(job_id=result["issue_id"], issue_id=result["issue_id"], status=result["status"])


def _cost(issue_id: str) -> CostOut:
    try:
        from ...db.repository import issue_cost  # type: ignore[attr-defined]

        data = issue_cost(issue_id)
        return CostOut(
            cost_usd=data.get("cost_usd", 0.0),
            tokens_in=data.get("tokens_in", 0),
            tokens_out=data.get("tokens_out", 0),
        )
    except Exception:
        return CostOut()


@router.get("/issues/{issue_id}", response_model=IssueStatusOut)
def get_issue_status(
    issue_id: str, principal: Principal = Depends(get_principal)
) -> IssueStatusOut:
    st = issue_status(issue_id)
    pdf_url = None
    if st.get("pdf_key"):
        try:
            pdf_url = get_store().url(st["pdf_key"])
        except Exception:
            pdf_url = None
    return IssueStatusOut(
        issue_id=st.get("issue_id") or issue_id,
        status=st.get("status", "unknown"),
        theme_id=st.get("theme_id"),
        pdf_url=pdf_url,
        cost=_cost(st.get("issue_id") or issue_id),
    )


@router.get("/issues/{issue_id}/pdf")
def get_issue_pdf(issue_id: str, principal: Principal = Depends(get_principal)):
    store = get_store()
    key = f"issues/{issue_id}/issue.pdf"
    path = store.open_path(key)
    if path:
        return FileResponse(path, media_type="application/pdf")
    if store.exists(key):
        return Response(store.get(key), media_type="application/pdf")
    raise HTTPException(404, f"no PDF for issue {issue_id!r}")
