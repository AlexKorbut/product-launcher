from __future__ import annotations

import logging

from ..llm.client import AnthropicClient
from ..llm.models import OPUS
from ..models import GridPlan, GridSlot
from ..render.themes import ThemeManifest
from .summarize import SummarizedStory

logger = logging.getLogger(__name__)

GRID_SCHEMA = {
    "type": "object",
    "properties": {
        "section_order": {"type": "array", "items": {"type": "string"}},
        "slots": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "story_id": {"type": "string"},
                    "section": {"type": "string"},
                    "size": {"type": "string", "enum": ["lead", "medium", "brief"]},
                    "columns": {"type": "integer", "minimum": 1, "maximum": 6},
                    "with_photo": {"type": "boolean"},
                    "pull_quote": {"type": ["string", "null"]},
                },
                "required": ["story_id", "section", "size", "columns", "with_photo"],
            },
        },
    },
    "required": ["section_order", "slots"],
}


def plan_grid(
    stories: list[SummarizedStory],
    *,
    theme: ThemeManifest,
    client: AnthropicClient | None = None,
) -> GridPlan:
    """Use Opus with extended thinking to decide grid layout. Returns validated GridPlan."""
    if not stories:
        return GridPlan()

    if client is None:
        client = AnthropicClient()

    story_list = "\n".join(
        f"- id={s.id} headline={s.headline!r}" for s in stories
    )
    system = (
        "You are a newspaper editor planning a front page layout. "
        "Choose one lead story, arrange the rest as medium or brief stories in sections. "
        f"Respect the theme constraints: {theme.grid.columns} columns, "
        f"max {theme.grid.max_lead} lead stories."
    )
    user_msg = (
        f"Plan a grid layout for these {len(stories)} stories:\n{story_list}\n\n"
        "Assign each story a section, size (lead/medium/brief), column span, "
        "and whether to show a photo."
    )

    try:
        result = client.structured(
            [{"role": "user", "content": user_msg}],
            model=OPUS,
            system=system,
            schema=GRID_SCHEMA,
            tool_name="output",
            max_tokens=4096,
        )
        grid = GridPlan.model_validate(result)
        problems = grid.validate_against_theme(
            columns=theme.grid.columns, max_lead=theme.grid.max_lead
        )
        if problems:
            logger.warning("grid plan has constraint violations: %s; using fallback", problems)
            return _fallback_grid(stories, theme=theme)
        return grid
    except Exception as exc:
        logger.warning("plan_grid failed: %s; using fallback", exc)
        return _fallback_grid(stories, theme=theme)


def _fallback_grid(stories: list[SummarizedStory], *, theme: ThemeManifest) -> GridPlan:
    sections_seen: list[str] = []
    slots: list[GridSlot] = []
    for i, story in enumerate(stories):
        section = "world"
        if i == 0:
            size = "lead"
            columns = min(theme.grid.columns, 4)
            with_photo = True
        elif i % 3 == 0:
            size = "brief"
            columns = 1
            with_photo = False
        else:
            size = "medium"
            columns = 2
            with_photo = False

        if section not in sections_seen:
            sections_seen.append(section)

        slots.append(
            GridSlot(
                story_id=story.id,
                section=section,
                size=size,
                columns=columns,
                with_photo=with_photo,
            )
        )

    return GridPlan(section_order=sections_seen, slots=slots)
