from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models import Channel, ChannelStatus
from app.schemas import ChannelCreate, ChannelOut, ChannelUpdate
from app.security import Principal, decrypt_secret, encrypt_secret, require_org
from app.services.telegram import TelegramError, check_bot

router = APIRouter(prefix="/api/channels", tags=["channels"])


def _out(ch: Channel) -> ChannelOut:
    data = ChannelOut.model_validate(ch)
    data.subscription_ids = [s.id for s in ch.subscriptions]
    return data


async def _get(session: AsyncSession, org_id: int, channel_id: int) -> Channel:
    ch = await session.scalar(
        select(Channel)
        .options(selectinload(Channel.subscriptions))
        .where(Channel.id == channel_id, Channel.org_id == org_id)
    )
    if ch is None:
        raise HTTPException(404, "Channel not found")
    return ch


@router.get("", response_model=list[ChannelOut])
async def list_channels(
    p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> list[ChannelOut]:
    channels = (
        await session.scalars(
            select(Channel)
            .options(selectinload(Channel.subscriptions))
            .where(Channel.org_id == p.org_id)
            .order_by(Channel.id)
        )
    ).all()
    return [_out(c) for c in channels]


@router.post("", response_model=ChannelOut, status_code=201)
async def create_channel(
    body: ChannelCreate, p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> ChannelOut:
    payload = body.model_dump(exclude={"bot_token"})
    ch = Channel(**payload, org_id=p.org_id, bot_token_encrypted=encrypt_secret(body.bot_token))
    session.add(ch)
    await session.commit()
    return await get_channel(ch.id, p, session)


@router.get("/{channel_id}", response_model=ChannelOut)
async def get_channel(
    channel_id: int, p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> ChannelOut:
    return _out(await _get(session, p.org_id, channel_id))


@router.put("/{channel_id}", response_model=ChannelOut)
async def update_channel(
    channel_id: int, body: ChannelUpdate,
    p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session),
) -> ChannelOut:
    ch = await _get(session, p.org_id, channel_id)
    for field, value in body.model_dump(exclude={"bot_token", "status"}, exclude_unset=True).items():
        setattr(ch, field, value)
    if body.bot_token:
        ch.bot_token_encrypted = encrypt_secret(body.bot_token)
    if body.status:
        ch.status = ChannelStatus(body.status)
    await session.commit()
    return _out(ch)


@router.delete("/{channel_id}", status_code=204)
async def delete_channel(
    channel_id: int, p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> None:
    ch = await _get(session, p.org_id, channel_id)
    await session.delete(ch)
    await session.commit()


@router.post("/{channel_id}/check")
async def check_channel_bot(
    channel_id: int, p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> dict:
    ch = await _get(session, p.org_id, channel_id)
    try:
        return await check_bot(decrypt_secret(ch.bot_token_encrypted), ch.username)
    except TelegramError as e:
        raise HTTPException(400, f"Telegram: {e}")
