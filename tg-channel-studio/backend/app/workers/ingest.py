"""Ingest worker: reads donor channels via Telethon userbot and stores raw posts.

Anti-flood hygiene: per-donor poll intervals, random jitter between reads,
incremental reads via min_id. Run as: python -m app.workers.ingest
"""
import asyncio
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from telethon import TelegramClient
from telethon.errors import (
    ChannelPrivateError,
    FloodWaitError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
)

from app.config import get_settings
from app.db import SessionLocal
from app.models import Donor, DonorStatus, RawPost, RawPostStatus
from app.services.dedup import content_hash, passes_filters
from app.workers.common import log

WORKER = "ingest"
BATCH_LIMIT = 50


async def fetch_donor(client: TelegramClient, donor: Donor) -> int:
    """Fetch new messages from one donor; returns number of stored posts."""
    stored = 0
    entity = await client.get_entity(donor.username.lstrip("@"))
    async with SessionLocal() as session:
        db_donor = await session.get(Donor, donor.id)
        async for msg in client.iter_messages(
            entity, min_id=donor.last_message_id, limit=BATCH_LIMIT, reverse=True
        ):
            text = (msg.message or "").strip()
            db_donor.last_message_id = max(db_donor.last_message_id, msg.id)
            if not text:
                continue

            media = {}
            if msg.photo:
                media = {"type": "photo"}  # MVP: фиксируем наличие, перенос файла — v0.2

            ok, reason = passes_filters(text, media, donor.filters or {})
            status = RawPostStatus.new if ok else RawPostStatus.skipped

            digest = content_hash(text)
            dup = await session.scalar(
                select(RawPost.id).where(RawPost.content_hash == digest).limit(1)
            )
            if dup:
                continue

            session.add(
                RawPost(
                    donor_id=donor.id,
                    tg_message_id=msg.id,
                    text=text,
                    media=media,
                    content_hash=digest,
                    posted_at=msg.date,
                    status=status,
                )
            )
            if ok:
                stored += 1
            elif reason:
                await log(WORKER, f"@{donor.username}: skip msg {msg.id} ({reason})")

        db_donor.last_polled_at = datetime.now(timezone.utc)
        db_donor.title = getattr(entity, "title", db_donor.title) or db_donor.title
        if db_donor.status == DonorStatus.unavailable:
            db_donor.status = DonorStatus.active
        await session.commit()
    return stored


async def mark_unavailable(donor_id: int) -> None:
    async with SessionLocal() as session:
        donor = await session.get(Donor, donor_id)
        donor.status = DonorStatus.unavailable
        await session.commit()


async def run() -> None:
    s = get_settings()
    client = TelegramClient(s.telethon_session, s.telegram_api_id, s.telegram_api_hash)
    await client.start()
    await log(WORKER, "ingest worker started")

    while True:
        async with SessionLocal() as session:
            donors = (
                await session.scalars(select(Donor).where(Donor.status != DonorStatus.paused))
            ).all()

        now = datetime.now(timezone.utc)
        for donor in donors:
            due = donor.last_polled_at is None or now - donor.last_polled_at >= timedelta(
                minutes=donor.poll_interval_min
            )
            if not due:
                continue
            try:
                n = await fetch_donor(client, donor)
                if n:
                    await log(WORKER, f"@{donor.username}: +{n} raw posts")
            except FloodWaitError as e:
                await log(WORKER, f"flood wait {e.seconds}s — sleeping", "warning")
                await asyncio.sleep(e.seconds + 5)
            except (UsernameInvalidError, UsernameNotOccupiedError, ChannelPrivateError) as e:
                await mark_unavailable(donor.id)
                await log(WORKER, f"@{donor.username} unavailable: {type(e).__name__}", "error")
            except Exception as e:  # noqa: BLE001 — keep the loop alive
                await log(WORKER, f"@{donor.username} failed: {e}", "error")
            # Random jitter between donor reads — gentler MTProto usage profile.
            await asyncio.sleep(random.uniform(2, s.ingest_jitter_sec))

        await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(run())
