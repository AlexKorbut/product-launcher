from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Alert, Channel, Organization, Post, PostStatus, RawPost, WorkerLog
from app.schemas import AlertOut, ChannelStats, DashboardOut, LogOut
from app.security import Principal, require_org

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
async def dashboard(
    p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> DashboardOut:
    today_start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
    org_id = p.org_id

    channels = (
        await session.scalars(select(Channel).where(Channel.org_id == org_id).order_by(Channel.id))
    ).all()
    stats: list[ChannelStats] = []
    for ch in channels:
        queue = await session.scalar(
            select(func.count()).where(
                Post.channel_id == ch.id,
                Post.status.in_([PostStatus.review, PostStatus.approved, PostStatus.scheduled]),
            )
        )
        published_today = await session.scalar(
            select(func.count()).where(
                Post.channel_id == ch.id, Post.status == PostStatus.published,
                Post.published_at >= today_start,
            )
        )
        failed = await session.scalar(
            select(func.count()).where(Post.channel_id == ch.id, Post.status == PostStatus.failed)
        )
        cost_today = await session.scalar(
            select(func.coalesce(func.sum(Post.cost_usd), 0.0)).where(
                Post.channel_id == ch.id, Post.created_at >= today_start
            )
        )
        stats.append(ChannelStats(
            channel_id=ch.id, channel_name=ch.name, status=ch.status.value,
            queue=queue or 0, published_today=published_today or 0,
            failed=failed or 0, cost_today_usd=round(cost_today or 0.0, 4),
        ))

    raw_new = await session.scalar(select(func.count()).where(RawPost.fanned_out.is_(False)))
    total_published = await session.scalar(
        select(func.count()).where(Post.org_id == org_id, Post.status == PostStatus.published)
    )
    total_cost = await session.scalar(
        select(func.coalesce(func.sum(Post.cost_usd), 0.0)).where(Post.org_id == org_id)
    )
    balance = await session.scalar(
        select(Organization.credit_balance).where(Organization.id == org_id)
    )

    return DashboardOut(
        channels=stats, raw_new=raw_new or 0, total_published=total_published or 0,
        total_cost_usd=round(total_cost or 0.0, 4), credit_balance=balance or 0,
    )


@router.get("/logs", response_model=list[LogOut])
async def logs(
    worker: str | None = None, limit: int = Query(100, le=500),
    p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session),
) -> list[LogOut]:
    stmt = (
        select(WorkerLog)
        .where((WorkerLog.org_id == p.org_id) | (WorkerLog.org_id.is_(None)))
        .order_by(WorkerLog.created_at.desc())
        .limit(limit)
    )
    if worker:
        stmt = stmt.where(WorkerLog.worker == worker)
    return [LogOut.model_validate(x) for x in (await session.scalars(stmt)).all()]


@router.get("/alerts", response_model=list[AlertOut])
async def alerts(
    p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> list[AlertOut]:
    rows = (
        await session.scalars(
            select(Alert).where(Alert.org_id == p.org_id, Alert.is_read.is_(False))
            .order_by(Alert.created_at.desc()).limit(50)
        )
    ).all()
    return [AlertOut.model_validate(a) for a in rows]


@router.post("/alerts/read", status_code=204)
async def mark_alerts_read(
    p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> None:
    rows = (await session.scalars(select(Alert).where(Alert.org_id == p.org_id, Alert.is_read.is_(False)))).all()
    for a in rows:
        a.is_read = True
    await session.commit()
