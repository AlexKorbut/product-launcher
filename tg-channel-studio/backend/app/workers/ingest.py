"""Ingest worker: reads shared DonorSources via Telethon userbot.

Each public channel is scraped ONCE for all tenants. Anti-flood hygiene:
per-source poll cadence (min interval across its subscriptions), random jitter,
incremental reads via min_id. Run as: python -m app.workers.ingest
"""
import asyncio
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from telethon import TelegramClient
from telethon.errors import (
    ChannelPrivateError,
    FloodWaitError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
)

from app.config import get_settings
from app.db import SessionLocal
from app.models import DonorSource, DonorStatus, DonorSubscription, RawPost
from app.services.dedup import content_hash
from app.services.media import download_photo
from app.workers.common import log

WORKER = "ingest"
BATCH_LIMIT = 50


async def fetch_source(client: TelegramClient, source: DonorSource) -> int:
    stored = 0
    entity = await client.get_entity(source.username.lstrip("@"))
    async with SessionLocal() as session:
        db_source = await session.get(DonorSource, source.id)
        async for msg in client.iter_messages(
            entity, min_id=source.last_message_id, limit=BATCH_LIMIT, reverse=True
        ):
            text = (msg.message or "").strip()
            db_source.last_message_id = max(db_source.last_message_id, msg.id)
            if not text:
                continue

            digest = content_hash(text)
            dup = await session.scalar(
                select(RawPost.id).where(
                    RawPost.source_id == source.id, RawPost.content_hash == digest
                ).limit(1)
            )
            if dup:
                continue

            media = await download_photo(client, msg, source.id)
            session.add(RawPost(
                source_id=source.id, tg_message_id=msg.id, text=text,
                media=media, content_hash=digest, posted_at=msg.date,
            ))
            stored += 1

        db_source.last_polled_at = datetime.now(timezone.utc)
        db_source.title = getattr(entity, "title", db_source.title) or db_source.title
        if db_source.status == DonorStatus.unavailable:
            db_source.status = DonorStatus.active
        await session.commit()
    return stored


async def mark_unavailable(source_id: int) -> None:
    async with SessionLocal() as session:
        src = await session.get(DonorSource, source_id)
        src.status = DonorStatus.unavailable
        await session.commit()


async def active_sources() -> list[tuple[DonorSource, int]]:
    """Sources with at least one active subscription + their min poll interval."""
    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(DonorSource, func.min(DonorSubscription.poll_interval_min))
                .join(DonorSubscription, DonorSubscription.source_id == DonorSource.id)
                .where(DonorSubscription.status == DonorStatus.active)
                .group_by(DonorSource.id)
            )
        ).all()
    return [(src, interval or 15) for src, interval in rows]


async def run() -> None:
    s = get_settings()
    client = TelegramClient(s.telethon_session, s.telegram_api_id, s.telegram_api_hash)
    await client.start()
    await log(WORKER, "ingest worker started")

    while True:
        now = datetime.now(timezone.utc)
        for source, interval in await active_sources():
            due = source.last_polled_at is None or now - source.last_polled_at >= timedelta(minutes=interval)
            if not due:
                continue
            try:
                n = await fetch_source(client, source)
                if n:
                    await log(WORKER, f"@{source.username}: +{n} raw posts")
            except FloodWaitError as e:
                await log(WORKER, f"flood wait {e.seconds}s — sleeping", "warning")
                await asyncio.sleep(e.seconds + 5)
            except (UsernameInvalidError, UsernameNotOccupiedError, ChannelPrivateError) as e:
                await mark_unavailable(source.id)
                await log(WORKER, f"@{source.username} unavailable: {type(e).__name__}", "error")
            except Exception as e:  # noqa: BLE001
                await log(WORKER, f"@{source.username} failed: {e}", "error")
            await asyncio.sleep(random.uniform(2, s.ingest_jitter_sec))

        await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(run())
