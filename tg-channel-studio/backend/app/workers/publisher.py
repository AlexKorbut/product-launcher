"""Publisher worker: posts scheduled content to channels via Bot API.

Handles flood-wait/retries; marks posts failed after 3 attempts.
Run as: python -m app.workers.publisher
"""
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import Channel, Post, PostStatus
from app.security import decrypt_secret
from app.services.telegram import TelegramError, send_post
from app.workers.common import log

WORKER = "publisher"
MAX_RETRIES = 3


async def publish_one(post_id: int) -> None:
    async with SessionLocal() as session:
        post = await session.get(Post, post_id)
        if post is None or post.status != PostStatus.scheduled:
            return
        channel = await session.get(Channel, post.channel_id)
        try:
            token = decrypt_secret(channel.bot_token_encrypted)
            sent = await send_post(token, channel.username, post.text, post.media)
            post.status = PostStatus.published
            post.published_at = datetime.now(timezone.utc)
            post.tg_message_id = sent.message_id
            post.error = ""
            await log(WORKER, f"published post {post.id} -> {channel.name} (msg {sent.message_id})")
        except TelegramError as e:
            post.retries += 1
            post.error = str(e)
            if e.retry_after:
                await log(WORKER, f"post {post.id}: flood wait {e.retry_after}s", "warning")
                await asyncio.sleep(e.retry_after + 1)
            if post.retries >= MAX_RETRIES:
                post.status = PostStatus.failed
                await log(WORKER, f"post {post.id} FAILED after {post.retries} tries: {e}", "error")
        except Exception as e:  # noqa: BLE001
            post.retries += 1
            post.error = str(e)
            if post.retries >= MAX_RETRIES:
                post.status = PostStatus.failed
            await log(WORKER, f"post {post.id} error: {e}", "error")
        await session.commit()


async def run() -> None:
    s = get_settings()
    await log(WORKER, "publisher worker started")
    while True:
        now = datetime.now(timezone.utc)
        async with SessionLocal() as session:
            due_ids = (
                await session.scalars(
                    select(Post.id)
                    .where(
                        Post.status == PostStatus.scheduled,
                        Post.scheduled_at.isnot(None),
                        Post.scheduled_at <= now,
                    )
                    .order_by(Post.scheduled_at)
                    .limit(10)
                )
            ).all()
        for post_id in due_ids:
            await publish_one(post_id)
            await asyncio.sleep(2)  # spacing between sends
        await asyncio.sleep(s.publisher_poll_sec)


if __name__ == "__main__":
    asyncio.run(run())
