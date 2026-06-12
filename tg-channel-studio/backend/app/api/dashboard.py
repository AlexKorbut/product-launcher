from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Channel, Post, PostStatus, RawPost, RawPostStatus, WorkerLog
from app.schemas import ChannelStats, DashboardOut, LogOut
from app.security import require_auth

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"], dependencies=[Depends(require_auth)])


@router.get("", response_model=DashboardOut)
async def dashboard(session: AsyncSession = Depends(get_session)) -> DashboardOut:
    today_start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)

    channels = (await session.scalars(select(Channel).order_by(Channel.id))).all()
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
                Post.channel_id == ch.id,
                Post.status == PostStatus.published,
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
        stats.append(
            ChannelStats(
                channel_id=ch.id,
                channel_name=ch.name,
                status=ch.status.value,
                queue=queue or 0,
                published_today=published_today or 0,
                failed=failed or 0,
                cost_today_usd=round(cost_today or 0.0, 4),
            )
        )

    raw_new = await session.scalar(
        select(func.count()).where(RawPost.status == RawPostStatus.new)
    )
    total_published = await session.scalar(
        select(func.count()).where(Post.status == PostStatus.published)
    )
    total_cost = await session.scalar(select(func.coalesce(func.sum(Post.cost_usd), 0.0)))

    return DashboardOut(
        channels=stats,
        raw_new=raw_new or 0,
        total_published=total_published or 0,
        total_cost_usd=round(total_cost or 0.0, 4),
    )


@router.get("/logs", response_model=list[LogOut])
async def logs(
    worker: str | None = None,
    limit: int = Query(100, le=500),
    session: AsyncSession = Depends(get_session),
) -> list[LogOut]:
    stmt = select(WorkerLog).order_by(WorkerLog.created_at.desc()).limit(limit)
    if worker:
        stmt = stmt.where(WorkerLog.worker == worker)
    return [LogOut.model_validate(item) for item in (await session.scalars(stmt)).all()]
