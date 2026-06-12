"""Publisher worker: posts scheduled content to channels via Bot API.

Transfers donor media (downloaded by ingest) via sendPhoto, handles
flood-wait/retries, raises alerts and marks posts failed after 3 attempts.
Run as: python -m app.workers.publisher
"""
import asyncio
import os
from datetime import datetime, timezone

from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import AlertKind, Channel, Post, PostStatus
from app.security import decrypt_secret
from app.services.media import upload_photo_to_channel
from app.services.telegram import TelegramError, send_post
from app.workers.common import log, raise_alert

WORKER = "publisher"
MAX_RETRIES = 3


def _chat_id(username: str) -> str:
    if username.startswith("-") or username.startswith("@"):
        return username
    return f"@{username}"


async def publish_one(post_id: int) -> None:
    async with SessionLocal() as session:
        post = await session.get(Post, post_id)
        if post is None or post.status != PostStatus.scheduled:
            return
        channel = await session.get(Channel, post.channel_id)
        try:
            token = decrypt_secret(channel.bot_token_encrypted)
            media = post.media or {}
            if media.get("type") == "photo" and media.get("path") and os.path.exists(media["path"]):
                message_id = await upload_photo_to_channel(
                    token, _chat_id(channel.username), media["path"], post.text
                )
            else:
                sent = await send_post(token, channel.username, post.text, None)
                message_id = sent.message_id
            post.status = PostStatus.published
            post.published_at = datetime.now(timezone.utc)
            post.tg_message_id = message_id
            post.error = ""
            await log(WORKER, f"published post {post.id} -> {channel.name} (msg {message_id})", org_id=post.org_id)
        except TelegramError as e:
            post.retries += 1
            post.error = str(e)
            if e.retry_after:
                await log(WORKER, f"post {post.id}: flood wait {e.retry_after}s", "warning", org_id=post.org_id)
                await asyncio.sleep(e.retry_after + 1)
            if post.retries >= MAX_RETRIES:
                post.status = PostStatus.failed
                await raise_alert(post.org_id, AlertKind.publish_failed,
                                  f"Не удалось опубликовать пост в «{channel.name}»: {e}")
                await log(WORKER, f"post {post.id} FAILED after {post.retries}: {e}", "error", org_id=post.org_id)
        except Exception as e:  # noqa: BLE001
            post.retries += 1
            post.error = str(e)
            if post.retries >= MAX_RETRIES:
                post.status = PostStatus.failed
                await raise_alert(post.org_id, AlertKind.publish_failed,
                                  f"Ошибка публикации в «{channel.name}»: {e}")
            await log(WORKER, f"post {post.id} error: {e}", "error", org_id=post.org_id)
        await session.commit()


async def run() -> None:
    s = get_settings()
    await log(WORKER, "publisher worker started")
    while True:
        now = datetime.now(timezone.utc)
        async with SessionLocal() as session:
            due_ids = (
                await session.scalars(
                    select(Post.id).where(
                        Post.status == PostStatus.scheduled,
                        Post.scheduled_at.isnot(None),
                        Post.scheduled_at <= now,
                    ).order_by(Post.scheduled_at).limit(10)
                )
            ).all()
        for post_id in due_ids:
            await publish_one(post_id)
            await asyncio.sleep(2)
        await asyncio.sleep(s.publisher_poll_sec)


if __name__ == "__main__":
    asyncio.run(run())
