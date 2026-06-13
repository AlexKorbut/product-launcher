"""Interest profile: build (ingest+tag) and read.

Never returns raw signal text — only topic/entity weights.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from ..deps import Principal, get_principal, require_owner
from ..jobs import JOBS, run_issue_job
from ..schemas import JobOut, ProfileOut

router = APIRouter(tags=["profile"])


@router.post("/users/{user_id}/profile:build", response_model=JobOut)
def build_profile(
    user_id: str,
    background: BackgroundTasks,
    principal: Principal = Depends(get_principal),
) -> JobOut:
    # Build the profile by running ingest+tag stages only (1..2). The pipeline
    # persists the profile internally, so we reuse the same job worker.
    require_owner(principal, user_id)
    job_id = uuid.uuid4().hex
    JOBS[job_id] = {"status": "running", "issue_id": None, "pdf_key": None, "error": None}
    background.add_task(run_issue_job, job_id, user_id, {"until_stage": 2})
    return JobOut(job_id=job_id, issue_id=None, status="running")


@router.get("/users/{user_id}/profile", response_model=ProfileOut)
def get_profile(
    user_id: str, principal: Principal = Depends(get_principal)
) -> ProfileOut:
    require_owner(principal, user_id)
    from ...db.repository import load_profile

    profile = load_profile(user_id)
    if profile is None:
        raise HTTPException(404, f"no profile for user {user_id!r}")
    return ProfileOut(
        user_id=profile.user_id,
        output_lang=profile.output_lang,
        topics=dict(profile.topics),
        entities=dict(profile.entities),
        version=profile.version,
        updated_at=profile.updated_at,
    )
