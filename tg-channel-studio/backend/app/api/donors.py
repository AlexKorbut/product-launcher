from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models import Channel, DonorSource, DonorStatus, DonorSubscription
from app.schemas import DonorCreate, DonorOut, DonorUpdate
from app.security import Principal, require_org

router = APIRouter(prefix="/api/donors", tags=["donors"])


def _normalize_username(value: str) -> str:
    value = value.strip()
    for prefix in ("https://t.me/", "http://t.me/", "t.me/", "@"):
        if value.startswith(prefix):
            value = value[len(prefix):]
    return value


def _out(sub: DonorSubscription) -> DonorOut:
    return DonorOut(
        id=sub.id,
        username=sub.source.username,
        title=sub.source.title,
        poll_interval_min=sub.poll_interval_min,
        filters=sub.filters or {},
        status=sub.status.value,
        last_polled_at=sub.source.last_polled_at,
        channel_ids=[c.id for c in sub.channels],
    )


async def _get(session: AsyncSession, org_id: int, sub_id: int) -> DonorSubscription:
    sub = await session.scalar(
        select(DonorSubscription)
        .options(selectinload(DonorSubscription.channels), selectinload(DonorSubscription.source))
        .where(DonorSubscription.id == sub_id, DonorSubscription.org_id == org_id)
    )
    if sub is None:
        raise HTTPException(404, "Donor not found")
    return sub


async def _resolve_source(session: AsyncSession, username: str) -> DonorSource:
    """Get-or-create the shared DonorSource for a username."""
    source = await session.scalar(select(DonorSource).where(DonorSource.username == username))
    if source is None:
        source = DonorSource(username=username)
        session.add(source)
        await session.flush()
    return source


async def _set_channels(session: AsyncSession, sub: DonorSubscription, channel_ids: list[int], org_id: int) -> None:
    channels = (
        await session.scalars(
            select(Channel).where(Channel.id.in_(channel_ids), Channel.org_id == org_id)
        )
    ).all()
    current = await sub.awaitable_attrs.channels
    current.clear()
    current.extend(channels)


@router.get("", response_model=list[DonorOut])
async def list_donors(
    p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> list[DonorOut]:
    subs = (
        await session.scalars(
            select(DonorSubscription)
            .options(selectinload(DonorSubscription.channels), selectinload(DonorSubscription.source))
            .where(DonorSubscription.org_id == p.org_id)
            .order_by(DonorSubscription.id)
        )
    ).all()
    return [_out(s) for s in subs]


@router.post("", response_model=DonorOut, status_code=201)
async def create_donor(
    body: DonorCreate, p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> DonorOut:
    username = _normalize_username(body.username)
    source = await _resolve_source(session, username)
    dup = await session.scalar(
        select(DonorSubscription).where(
            DonorSubscription.org_id == p.org_id, DonorSubscription.source_id == source.id
        )
    )
    if dup:
        raise HTTPException(409, "Donor already added")
    sub = DonorSubscription(
        org_id=p.org_id, source_id=source.id,
        poll_interval_min=body.poll_interval_min, filters=body.filters,
    )
    session.add(sub)
    await session.flush()
    if body.channel_ids:
        await _set_channels(session, sub, body.channel_ids, p.org_id)
    await session.commit()
    return _out(await _get(session, p.org_id, sub.id))


@router.put("/{sub_id}", response_model=DonorOut)
async def update_donor(
    sub_id: int, body: DonorUpdate,
    p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session),
) -> DonorOut:
    sub = await _get(session, p.org_id, sub_id)
    sub.poll_interval_min = body.poll_interval_min
    sub.filters = body.filters
    if body.status:
        sub.status = DonorStatus(body.status)
    if body.channel_ids is not None:
        await _set_channels(session, sub, body.channel_ids, p.org_id)
    await session.commit()
    return _out(sub)


@router.delete("/{sub_id}", status_code=204)
async def delete_donor(
    sub_id: int, p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> None:
    sub = await _get(session, p.org_id, sub_id)
    await session.delete(sub)
    await session.commit()
