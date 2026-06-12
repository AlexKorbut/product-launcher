from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models import Channel, Donor, DonorStatus
from app.schemas import DonorCreate, DonorOut, DonorUpdate
from app.security import require_auth

router = APIRouter(prefix="/api/donors", tags=["donors"], dependencies=[Depends(require_auth)])


def _normalize_username(value: str) -> str:
    value = value.strip()
    for prefix in ("https://t.me/", "http://t.me/", "t.me/", "@"):
        if value.startswith(prefix):
            value = value[len(prefix):]
    return value


def _out(d: Donor) -> DonorOut:
    data = DonorOut.model_validate(d)
    data.channel_ids = [c.id for c in d.channels]
    return data


async def _get(session: AsyncSession, donor_id: int) -> Donor:
    donor = await session.scalar(
        select(Donor).options(selectinload(Donor.channels)).where(Donor.id == donor_id)
    )
    if donor is None:
        raise HTTPException(404, "Donor not found")
    return donor


async def _set_channels(session: AsyncSession, donor: Donor, channel_ids: list[int]) -> None:
    channels = (await session.scalars(select(Channel).where(Channel.id.in_(channel_ids)))).all()
    current = await donor.awaitable_attrs.channels  # ensure loaded before mutating (async ORM)
    current.clear()
    current.extend(channels)


@router.get("", response_model=list[DonorOut])
async def list_donors(session: AsyncSession = Depends(get_session)) -> list[DonorOut]:
    donors = (
        await session.scalars(select(Donor).options(selectinload(Donor.channels)).order_by(Donor.id))
    ).all()
    return [_out(d) for d in donors]


@router.post("", response_model=DonorOut, status_code=201)
async def create_donor(body: DonorCreate, session: AsyncSession = Depends(get_session)) -> DonorOut:
    donor = Donor(
        username=_normalize_username(body.username),
        title=body.title,
        poll_interval_min=body.poll_interval_min,
        filters=body.filters,
    )
    session.add(donor)
    await session.flush()
    if body.channel_ids:
        await _set_channels(session, donor, body.channel_ids)
    await session.commit()
    return _out(await _get(session, donor.id))


@router.put("/{donor_id}", response_model=DonorOut)
async def update_donor(
    donor_id: int, body: DonorUpdate, session: AsyncSession = Depends(get_session)
) -> DonorOut:
    donor = await _get(session, donor_id)
    donor.username = _normalize_username(body.username)
    donor.title = body.title
    donor.poll_interval_min = body.poll_interval_min
    donor.filters = body.filters
    if body.status:
        donor.status = DonorStatus(body.status)
    if body.channel_ids is not None:
        await _set_channels(session, donor, body.channel_ids)
    await session.commit()
    return _out(donor)


@router.delete("/{donor_id}", status_code=204)
async def delete_donor(donor_id: int, session: AsyncSession = Depends(get_session)) -> None:
    donor = await _get(session, donor_id)
    await session.delete(donor)
    await session.commit()
