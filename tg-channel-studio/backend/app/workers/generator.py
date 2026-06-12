"""Generator worker: fans out new raw posts to subscribed orgs and rewrites them.

For each new RawPost it finds every DonorSubscription on that source, applies the
subscription's filters, checks the org's credit balance, rewrites per channel
profile via Claude, runs the anti-plagiarism gate, debits credits, and routes the
post to review or the schedule. Run as: python -m app.workers.generator
"""
import asyncio

import anthropic
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.db import SessionLocal
from app.models import (
    AlertKind,
    ChannelStatus,
    DonorStatus,
    DonorSubscription,
    Post,
    PostStatus,
    RawPost,
)
from app.services import credits
from app.services.dedup import passes_filters
from app.services.rewrite import rewrite_post
from app.services.schedule import next_slot
from app.workers.common import log, raise_alert

WORKER = "generator"


async def _scheduled_slots(session, channel_id: int) -> list:
    return list(
        (await session.scalars(
            select(Post.scheduled_at).where(
                Post.channel_id == channel_id,
                Post.status == PostStatus.scheduled,
                Post.scheduled_at.isnot(None),
            )
        )).all()
    )


async def process_raw_post(raw_id: int) -> None:
    s = get_settings()
    async with SessionLocal() as session:
        raw = await session.get(RawPost, raw_id)
        if raw is None or raw.fanned_out:
            return
        subs = (
            await session.scalars(
                select(DonorSubscription)
                .options(selectinload(DonorSubscription.channels))
                .where(
                    DonorSubscription.source_id == raw.source_id,
                    DonorSubscription.status == DonorStatus.active,
                )
            )
        ).all()

        for sub in subs:
            ok, reason = passes_filters(raw.text, raw.media or {}, sub.filters or {})
            if not ok:
                if reason:
                    await log(WORKER, f"raw {raw.id}/sub {sub.id}: filtered ({reason})", org_id=sub.org_id)
                continue

            channels = [c for c in sub.channels if c.status == ChannelStatus.active]
            for channel in channels:
                if await credits.get_balance(session, sub.org_id) <= 0:
                    await raise_alert(sub.org_id, AlertKind.out_of_credits,
                                      "Кредиты закончились — генерация приостановлена")
                    await log(WORKER, f"org {sub.org_id}: out of credits, skipping", "warning", org_id=sub.org_id)
                    continue
                try:
                    result = await rewrite_post(channel, raw.text)
                except anthropic.RateLimitError:
                    await log(WORKER, "anthropic rate limit — backing off 60s", "warning")
                    await asyncio.sleep(60)
                    return  # leave raw post un-fanned; retried next cycle
                except anthropic.APIStatusError as e:
                    await log(WORKER, f"anthropic error {e.status_code}: {e.message}", "error", org_id=sub.org_id)
                    continue
                except Exception as e:  # noqa: BLE001 — other providers (OpenAI, etc.)
                    await log(WORKER, f"llm error ({channel.name}): {e}", "error", org_id=sub.org_id)
                    continue

                if not result.text:
                    await log(WORKER, f"raw {raw.id} -> {channel.name}: empty generation", "error", org_id=sub.org_id)
                    continue
                if result.similarity_to_source > s.max_rewrite_similarity:
                    await log(WORKER, f"raw {raw.id} -> {channel.name}: rejected, "
                              f"sim {result.similarity_to_source:.2f}", "warning", org_id=sub.org_id)
                    continue

                text = result.text
                if channel.signature.strip():
                    text = f"{text}\n\n{channel.signature.strip()}"

                post = Post(
                    org_id=sub.org_id, channel_id=channel.id, raw_post_id=raw.id,
                    text=text, media=raw.media or {},
                    similarity_to_source=result.similarity_to_source, model=result.model,
                    input_tokens=result.input_tokens, output_tokens=result.output_tokens,
                    cost_usd=result.cost_usd, credits_charged=result.credits,
                )
                if channel.auto_publish:
                    post.status = PostStatus.scheduled
                    post.scheduled_at = next_slot(channel, taken=await _scheduled_slots(session, channel.id))
                else:
                    post.status = PostStatus.review
                session.add(post)
                await session.flush()
                await credits.debit(session, sub.org_id, result.credits, ref=f"post:{post.id}")
                await log(WORKER, f"raw {raw.id} -> {channel.name}: {post.status.value}, "
                          f"-{result.credits} cr, sim={result.similarity_to_source:.2f}", org_id=sub.org_id)

        raw.fanned_out = True
        await session.commit()


async def run() -> None:
    s = get_settings()
    await log(WORKER, "generator worker started")
    while True:
        async with SessionLocal() as session:
            ids = (
                await session.scalars(
                    select(RawPost.id).where(RawPost.fanned_out.is_(False))
                    .order_by(RawPost.fetched_at).limit(5)
                )
            ).all()
        for raw_id in ids:
            try:
                await process_raw_post(raw_id)
            except Exception as e:  # noqa: BLE001
                await log(WORKER, f"raw {raw_id} failed: {e}", "error")
        await asyncio.sleep(s.generator_poll_sec)


if __name__ == "__main__":
    asyncio.run(run())
