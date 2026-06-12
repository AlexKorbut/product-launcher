"""Generator worker: turns new raw posts into channel posts via Claude.

Picks RawPost(status=new) for donors attached to active channels, rewrites
per channel profile, runs the anti-plagiarism gate, then routes the post to
review or straight to the schedule (auto_publish). Run as:
python -m app.workers.generator
"""
import asyncio

import anthropic
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import (
    Channel,
    ChannelStatus,
    Post,
    PostStatus,
    RawPost,
    RawPostStatus,
)
from app.services.rewrite import rewrite_post
from app.services.schedule import next_slot
from app.workers.common import log

WORKER = "generator"


async def process_raw_post(raw: RawPost) -> None:
    s = get_settings()
    async with SessionLocal() as session:
        raw = await session.get(RawPost, raw.id)
        donor = await raw.awaitable_attrs.donor
        channels = [
            c for c in await donor.awaitable_attrs.channels
            if c.status == ChannelStatus.active
        ]
        if not channels:
            raw.status = RawPostStatus.skipped
            await session.commit()
            return

        for channel in channels:
            try:
                result = await rewrite_post(channel, raw.text)
            except anthropic.RateLimitError:
                await log(WORKER, "anthropic rate limit — backing off 60s", "warning")
                await asyncio.sleep(60)
                return  # leave raw post as new; retried next cycle
            except anthropic.APIStatusError as e:
                await log(WORKER, f"anthropic error {e.status_code}: {e.message}", "error")
                continue

            if not result.text:
                await log(WORKER, f"raw {raw.id} -> {channel.name}: empty generation", "error")
                continue

            # Anti-plagiarism gate: reject rewrites that are too close to the source.
            if result.similarity_to_source > s.max_rewrite_similarity:
                await log(
                    WORKER,
                    f"raw {raw.id} -> {channel.name}: rejected, similarity "
                    f"{result.similarity_to_source:.2f} > {s.max_rewrite_similarity}",
                    "warning",
                )
                continue

            text = result.text
            if channel.signature.strip():
                text = f"{text}\n\n{channel.signature.strip()}"

            post = Post(
                channel_id=channel.id,
                raw_post_id=raw.id,
                text=text,
                media=raw.media or {},
                similarity_to_source=result.similarity_to_source,
                model=result.model,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                cost_usd=result.cost_usd,
            )
            if channel.auto_publish:
                taken = (
                    await session.scalars(
                        select(Post.scheduled_at).where(
                            Post.channel_id == channel.id,
                            Post.status == PostStatus.scheduled,
                            Post.scheduled_at.isnot(None),
                        )
                    )
                ).all()
                post.status = PostStatus.scheduled
                post.scheduled_at = next_slot(channel, taken=list(taken))
            else:
                post.status = PostStatus.review

            session.add(post)
            await log(
                WORKER,
                f"raw {raw.id} -> {channel.name}: {post.status.value}, "
                f"sim={result.similarity_to_source:.2f}, ${result.cost_usd:.4f}",
            )

        raw.status = RawPostStatus.processed
        await session.commit()


async def run() -> None:
    s = get_settings()
    await log(WORKER, "generator worker started")
    while True:
        async with SessionLocal() as session:
            raws = (
                await session.scalars(
                    select(RawPost)
                    .where(RawPost.status == RawPostStatus.new)
                    .order_by(RawPost.fetched_at)
                    .limit(5)
                )
            ).all()
        for raw in raws:
            try:
                await process_raw_post(raw)
            except Exception as e:  # noqa: BLE001 — keep the loop alive
                await log(WORKER, f"raw {raw.id} failed: {e}", "error")
        await asyncio.sleep(s.generator_poll_sec)


if __name__ == "__main__":
    asyncio.run(run())
