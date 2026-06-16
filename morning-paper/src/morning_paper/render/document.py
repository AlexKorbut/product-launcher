"""Build the semantic RenderDocument from pipeline outputs.

This is the last Python step before the Node renderer. It assembles stories +
the editorial grid plan + masthead into the theme-agnostic JSON contract.
"""

from __future__ import annotations

from datetime import date

from ..models import GridPlan, Masthead, RenderDocument, Story, StoryView


def build_render_document(
    *,
    issue_id: str,
    theme_id: str,
    locale: str,
    title: str,
    stories: list[Story],
    grid_plan: GridPlan,
    issue_no: str | None = None,
    edition: str | None = None,
    issue_date: date | None = None,
) -> RenderDocument:
    by_id = {s.id: s for s in stories}
    views: dict[str, StoryView] = {}
    images: dict[str, str] = {}

    for slot in grid_plan.slots:
        story = by_id.get(slot.story_id)
        if story is None:
            continue
        views[story.id] = StoryView(
            headline=story.headline,
            deck=story.deck,
            body_html=story.body_html,
            byline=story.byline,
            caption=story.source,  # attribution shown as caption/source line
            image_ref=story.image_ref if slot.with_photo else None,
        )
        if slot.with_photo and story.image_ref:
            images[story.image_ref] = story.image_ref

    masthead = Masthead(
        title=title,
        date=(issue_date or date.today()).isoformat(),
        issue_no=issue_no,
        edition=edition,
    )
    return RenderDocument(
        issue_id=issue_id,
        theme_id=theme_id,
        locale=locale,
        masthead=masthead,
        grid_plan=grid_plan,
        stories=views,
        images=images,
    )
