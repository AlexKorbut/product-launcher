from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Channel, ChannelStatus, Post, PostStatus, RawPost
from app.schemas import GenerateRequest, PostOut, PostUpdate
from app.security import Principal, require_org
from app.services import credits
from app.services.rewrite import generate_from_topic, rewrite_post
from app.services.schedule import next_slot

router = APIRouter(prefix="/api/posts", tags=["posts"])


async def _get(session: AsyncSession, org_id: int, post_id: int) -> Post:
    post = await session.scalar(
        select(Post).where(Post.id == post_id, Post.org_id == org_id)
    )
    if post is None:
        raise HTTPException(404, "Post not found")
    return post


@router.get("", response_model=list[PostOut])
async def list_posts(
    channel_id: int | None = None,
    status: str | None = Query(None),
    limit: int = Query(100, le=500),
    p: Principal = Depends(require_org),
    session: AsyncSession = Depends(get_session),
) -> list[PostOut]:
    stmt = select(Post).where(Post.org_id == p.org_id).order_by(Post.created_at.desc()).limit(limit)
    if channel_id:
        stmt = stmt.where(Post.channel_id == channel_id)
    if status:
        stmt = stmt.where(Post.status == PostStatus(status))
    return [PostOut.model_validate(x) for x in (await session.scalars(stmt)).all()]


@router.post("/generate", response_model=PostOut, status_code=201)
async def generate(
    body: GenerateRequest, p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> PostOut:
    """Manual generation: rewrite a raw post or generate from scratch. Debits credits."""
    channel = await session.scalar(
        select(Channel).where(Channel.id == body.channel_id, Channel.org_id == p.org_id)
    )
    if channel is None:
        raise HTTPException(404, "Channel not found")
    if await credits.get_balance(session, p.org_id) <= 0:
        raise HTTPException(402, "Недостаточно кредитов — пополни баланс")

    if body.raw_post_id:
        raw = await session.get(RawPost, body.raw_post_id)
        if raw is None:
            raise HTTPException(404, "Raw post not found")
        result = await rewrite_post(channel, raw.text)
        media = raw.media or {}
    else:
        result = await generate_from_topic(channel)
        media = {}

    text = result.text
    if channel.signature.strip():
        text = f"{text}\n\n{channel.signature.strip()}"

    post = Post(
        org_id=p.org_id, channel_id=channel.id, raw_post_id=body.raw_post_id,
        text=text, media=media, status=PostStatus.review,
        similarity_to_source=result.similarity_to_source, model=result.model,
        input_tokens=result.input_tokens, output_tokens=result.output_tokens,
        cost_usd=result.cost_usd, credits_charged=result.credits,
    )
    session.add(post)
    await session.flush()
    await credits.debit(session, p.org_id, result.credits, ref=f"post:{post.id}")
    await session.commit()
    return PostOut.model_validate(post)


@router.put("/{post_id}", response_model=PostOut)
async def update_post(
    post_id: int, body: PostUpdate,
    p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session),
) -> PostOut:
    post = await _get(session, p.org_id, post_id)
    if post.status == PostStatus.published:
        raise HTTPException(400, "Cannot edit a published post")
    if body.text is not None:
        post.text = body.text
    if body.scheduled_at is not None:
        post.scheduled_at = body.scheduled_at
    await session.commit()
    return PostOut.model_validate(post)


@router.post("/{post_id}/approve", response_model=PostOut)
async def approve_post(
    post_id: int, p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> PostOut:
    post = await _get(session, p.org_id, post_id)
    if post.status not in (PostStatus.review, PostStatus.draft, PostStatus.failed):
        raise HTTPException(400, f"Cannot approve a post in status {post.status.value}")
    channel = await session.get(Channel, post.channel_id)
    if channel.status != ChannelStatus.active:
        raise HTTPException(400, "Channel is paused")
    if post.scheduled_at is None:
        taken = (
            await session.scalars(
                select(Post.scheduled_at).where(
                    Post.channel_id == channel.id,
                    Post.status == PostStatus.scheduled,
                    Post.scheduled_at.isnot(None),
                )
            )
        ).all()
        post.scheduled_at = next_slot(channel, taken=list(taken))
    post.status = PostStatus.scheduled
    post.retries = 0
    post.error = ""
    await session.commit()
    return PostOut.model_validate(post)


@router.post("/{post_id}/publish-now", response_model=PostOut)
async def publish_now(
    post_id: int, p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> PostOut:
    post = await _get(session, p.org_id, post_id)
    if post.status == PostStatus.published:
        raise HTTPException(400, "Already published")
    post.status = PostStatus.scheduled
    post.scheduled_at = datetime.now(timezone.utc)
    post.retries = 0
    post.error = ""
    await session.commit()
    return PostOut.model_validate(post)


@router.post("/{post_id}/reject", response_model=PostOut)
async def reject_post(
    post_id: int, p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> PostOut:
    post = await _get(session, p.org_id, post_id)
    if post.status == PostStatus.published:
        raise HTTPException(400, "Cannot reject a published post")
    post.status = PostStatus.rejected
    await session.commit()
    return PostOut.model_validate(post)


@router.delete("/{post_id}", status_code=204)
async def delete_post(
    post_id: int, p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> None:
    post = await _get(session, p.org_id, post_id)
    await session.delete(post)
    await session.commit()
