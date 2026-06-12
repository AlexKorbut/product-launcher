"""Raw-material feed: donor posts visible to the org's subscriptions."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import DonorSource, DonorSubscription, RawPost
from app.schemas import RawPostOut
from app.security import Principal, require_org

router = APIRouter(prefix="/api/raw", tags=["raw"])


@router.get("", response_model=list[RawPostOut])
async def list_raw(
    limit: int = Query(50, le=200),
    p: Principal = Depends(require_org),
    session: AsyncSession = Depends(get_session),
) -> list[RawPostOut]:
    """Recent raw posts from sources the org is subscribed to (for manual rewrite)."""
    rows = (
        await session.execute(
            select(RawPost, DonorSource.username)
            .join(DonorSource, DonorSource.id == RawPost.source_id)
            .join(DonorSubscription, DonorSubscription.source_id == DonorSource.id)
            .where(DonorSubscription.org_id == p.org_id)
            .order_by(RawPost.fetched_at.desc())
            .distinct()
            .limit(limit)
        )
    ).all()
    return [
        RawPostOut(
            id=rp.id, source_username=username, text=rp.text, media=rp.media or {},
            posted_at=rp.posted_at, fetched_at=rp.fetched_at,
        )
        for rp, username in rows
    ]
