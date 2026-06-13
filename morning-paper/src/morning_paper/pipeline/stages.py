from __future__ import annotations

import logging
from datetime import date

from .context import IssueContext

logger = logging.getLogger(__name__)

STAGE_NAMES = ["ingest", "profile", "retrieve", "rank", "editorial", "grid", "render", "deliver"]

_DEFAULT_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.dw.com/rdf/rss-en-world",
]


def s1_ingest(ctx: IssueContext, **kwargs) -> IssueContext:
    """Gather signals from the user's configured sources (or, for a brand-new
    user with nothing configured, every auth-free source with empty options)."""
    from ..sources.registry import get_source
    from ..sources.base import AuthState, SourceConfig
    from .. import accounts

    configured = accounts.enabled_sources(ctx.user_id)

    if not configured:
        from ..sources.registry import all_sources

        configured = [
            accounts.SourceAccount(source_id=getattr(cls, "source_id", ""), options={})
            for cls in all_sources()
            if not getattr(cls, "requires_auth", False)
        ]

    signals = []
    for sa in configured:
        source_id = sa.source_id
        try:
            source = get_source(source_id)
        except KeyError:
            logger.warning("unknown source %s in accounts; skipping", source_id)
            continue
        cfg = SourceConfig(
            source_id=source_id, user_id=ctx.user_id, enabled=True, options=sa.options
        )
        auth = AuthState(
            source_id=source_id,
            user_id=ctx.user_id,
            status="connected",
            secret_ref=sa.secret_ref,
        )
        try:
            result = source.fetch(cfg, auth, cursor=sa.cursor)
            signals.extend(result.signals)
            for w in result.warnings:
                logger.warning("source %s: %s", source_id, w)
            if result.cursor != sa.cursor:
                try:
                    accounts.update_cursor(ctx.user_id, source_id, result.cursor)
                except Exception:
                    pass
        except Exception as exc:
            logger.warning("source %s fetch failed: %s", source_id, exc)

    ctx.signals = signals
    return ctx


def s2_profile(ctx: IssueContext, **kwargs) -> IssueContext:
    """Build/update InterestProfile from signals."""
    from ..profile.builder import build_profile

    try:
        client = None
        try:
            from ..metering import metered_client

            client = metered_client(
                ctx.user_id, ctx.issue_id, "profile", sink=ctx.usage_sink
            )
        except Exception as exc:
            logger.warning("metered client unavailable for profile: %s", exc)
        ctx.profile = build_profile(
            ctx.user_id,
            ctx.signals,
            output_lang=ctx.output_lang,
            client=client,
        )
    except Exception as exc:
        logger.warning("profile build failed: %s", exc)
        from ..models import InterestProfile
        ctx.profile = InterestProfile(user_id=ctx.user_id, output_lang=ctx.output_lang)

    return ctx


def s3_retrieve(ctx: IssueContext, feed_urls: list[str] = (), **kwargs) -> IssueContext:
    """Fetch candidate articles based on profile topics."""
    from ..retrieval.feeds import fetch_rss_candidates

    urls = list(feed_urls) if feed_urls else _DEFAULT_FEEDS

    try:
        ctx.candidates = fetch_rss_candidates(urls, max_per_feed=20)
    except Exception as exc:
        logger.warning("retrieve failed: %s", exc)
        ctx.candidates = []

    return ctx


def s4_rank(ctx: IssueContext, **kwargs) -> IssueContext:
    """Score candidates against profile, dedup, keep top 40."""
    from ..retrieval.rank import rank_candidates
    from ..retrieval.dedup import dedup_candidates
    from ..models import InterestProfile

    profile = ctx.profile or InterestProfile(user_id=ctx.user_id, output_lang=ctx.output_lang)

    try:
        ranked = rank_candidates(ctx.candidates, profile, top_n=40)
        ctx.ranked = dedup_candidates(ranked)
    except Exception as exc:
        logger.warning("rank/dedup failed: %s", exc)
        ctx.ranked = ctx.candidates[:40]

    return ctx


def s5_editorial(ctx: IssueContext, **kwargs) -> IssueContext:
    """Summarize+translate top candidates into newspaper stories."""
    from ..editorial.summarize import summarize_batch

    try:
        client = None
        usage_sink = None
        usage_ctx = None
        try:
            from ..metering import default_sink, metered_client

            client = metered_client(
                ctx.user_id, ctx.issue_id, "editorial", sink=ctx.usage_sink
            )
            usage_sink = ctx.usage_sink if ctx.usage_sink is not None else default_sink()
            usage_ctx = {
                "user_id": ctx.user_id,
                "issue_id": ctx.issue_id,
                "stage": "editorial",
            }
        except Exception as exc:
            logger.warning("metered client unavailable for editorial: %s", exc)
        ctx.stories = summarize_batch(
            ctx.ranked[:20],
            output_lang=ctx.output_lang,
            client=client,
            usage_sink=usage_sink,
            usage_ctx=usage_ctx,
        )
    except Exception as exc:
        logger.warning("editorial summarize failed: %s", exc)
        from ..editorial.summarize import SummarizedStory
        ctx.stories = [
            SummarizedStory(
                id=c.id,
                headline=c.title,
                deck="",
                body_html=f"<p>{c.body[:400]}</p>",
                byline=c.source,
                lang_in=c.lang,
                lang_out=ctx.output_lang,
                source_url=c.url,
            )
            for c in ctx.ranked[:20]
        ]

    return ctx


def s6_grid(ctx: IssueContext, **kwargs) -> IssueContext:
    """Plan grid layout for the issue."""
    from ..editorial.grid import plan_grid
    from ..render.themes import load_manifest

    try:
        theme = load_manifest(ctx.theme_id)
        ctx.grid_plan = plan_grid(ctx.stories, theme=theme)
    except Exception as exc:
        logger.warning("grid plan failed: %s", exc)
        from ..models import GridPlan, GridSlot
        slots = []
        for i, story in enumerate(ctx.stories[:10]):
            size = "lead" if i == 0 else ("medium" if i < 4 else "brief")
            slots.append(
                GridSlot(
                    story_id=story.id,
                    section="world",
                    size=size,
                    columns=4 if i == 0 else 2,
                    with_photo=(i == 0),
                )
            )
        ctx.grid_plan = GridPlan(section_order=["world"], slots=slots)

    return ctx


def s7_render(ctx: IssueContext, **kwargs) -> IssueContext:
    """Build RenderDocument and render PDF."""
    from ..models import Story
    from ..render.document import build_render_document
    from ..render.renderer import NodeRenderer, RenderError
    from ..models import GridPlan

    if not ctx.stories or not ctx.grid_plan:
        logger.warning("render skipped: no stories or grid plan")
        return ctx

    stories_model = [
        Story(
            id=s.id,
            section=_slot_section(s.id, ctx.grid_plan),
            headline=s.headline,
            deck=s.deck or None,
            body_html=s.body_html,
            byline=s.byline or None,
            source=s.source_url,
            source_url=s.source_url,
        )
        for s in ctx.stories
    ]

    doc = build_render_document(
        issue_id=ctx.issue_id,
        theme_id=ctx.theme_id,
        locale=ctx.output_lang,
        title="The Morning Paper",
        stories=stories_model,
        grid_plan=ctx.grid_plan,
        issue_date=date.today(),
    )
    ctx.render_document = doc

    out_path = ctx.work_dir / "issue.pdf"
    try:
        result = NodeRenderer().render(doc, out_path=out_path)
        ctx.pdf_path = out_path
    except RenderError as exc:
        logger.warning("render failed: %s", exc)

    return ctx


def s8_deliver(ctx: IssueContext, deliver_channel: str | None = None, **kwargs) -> IssueContext:
    """Deliver the PDF over the user's chosen channel (default: file outbox)."""
    if not ctx.pdf_path:
        logger.warning("deliver: no PDF path available")
        return ctx

    from .. import accounts

    channel = deliver_channel or accounts.load(ctx.user_id).deliver_channel or "file"
    subject = f"The Morning Paper — {date.today().isoformat()}"
    try:
        from ..delivery import get_deliverer

        result = get_deliverer(channel).deliver(
            ctx.pdf_path, user_id=ctx.user_id, subject=subject
        )
        if result.ok:
            logger.info("delivered via %s -> %s", result.channel, result.location)
            ctx.delivery_location = result.location
        else:
            logger.warning("delivery via %s failed: %s", channel, result.detail)
    except Exception as exc:
        logger.warning("deliver failed: %s", exc)

    print(str(ctx.delivery_location or ctx.pdf_path))
    return ctx


def _slot_section(story_id: str, grid_plan) -> str:
    for slot in grid_plan.slots:
        if slot.story_id == story_id:
            return slot.section
    return "world"
