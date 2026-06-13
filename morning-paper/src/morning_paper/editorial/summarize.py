from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from ..llm.client import AnthropicClient
from ..llm.models import SONNET
from ..retrieval.feeds import Candidate

logger = logging.getLogger(__name__)

_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "deck": {"type": "string"},
        "body_html": {"type": "string"},
        "byline": {"type": "string"},
    },
    "required": ["headline", "deck", "body_html", "byline"],
}


@dataclass
class SummarizedStory:
    id: str
    headline: str
    deck: str
    body_html: str
    byline: str
    lang_in: str
    lang_out: str
    source_url: str


def _system_prompt(output_lang: str) -> str:
    return (
        f"You are a newspaper editor writing in {output_lang}. "
        "Rewrite the provided article into newspaper register: "
        "a punchy headline (≤ 12 words), a deck/subhead (1 sentence), "
        "3-4 paragraph body in <p> tags, and a byline citing the source. "
        "Translate if necessary. "
        "Return JSON: {headline, deck, body_html, byline}."
    )


def _candidate_user_message(candidate: Candidate) -> str:
    return f"Title: {candidate.title}\n\nSource: {candidate.source}\n\nURL: {candidate.url}\n\n{candidate.body[:3000]}"


def summarize_batch(
    candidates: list[Candidate],
    *,
    output_lang: str = "ru",
    client: AnthropicClient | None = None,
    use_batch_api: bool = True,
) -> list[SummarizedStory]:
    """Summarize candidates into newspaper-register stories. Uses BatchProcessor if use_batch_api."""
    if not candidates:
        return []

    if client is None:
        client = AnthropicClient()

    system = _system_prompt(output_lang)

    if use_batch_api and len(candidates) > 3:
        return _summarize_via_batch(candidates, system=system, output_lang=output_lang)

    stories: list[SummarizedStory] = []
    for candidate in candidates:
        try:
            result = client.structured(
                [{"role": "user", "content": _candidate_user_message(candidate)}],
                model=SONNET,
                system=system,
                schema=_SCHEMA,
                tool_name="output",
                max_tokens=2048,
            )
            stories.append(
                SummarizedStory(
                    id=candidate.id,
                    headline=result.get("headline", candidate.title),
                    deck=result.get("deck", ""),
                    body_html=result.get("body_html", f"<p>{candidate.body[:500]}</p>"),
                    byline=result.get("byline", candidate.source),
                    lang_in=candidate.lang,
                    lang_out=output_lang,
                    source_url=candidate.url,
                )
            )
        except Exception as exc:
            logger.warning("summarize failed for %s: %s", candidate.id, exc)
            stories.append(
                SummarizedStory(
                    id=candidate.id,
                    headline=candidate.title,
                    deck="",
                    body_html=f"<p>{candidate.body[:500]}</p>",
                    byline=candidate.source,
                    lang_in=candidate.lang,
                    lang_out=output_lang,
                    source_url=candidate.url,
                )
            )

    return stories


def _summarize_via_batch(
    candidates: list[Candidate],
    *,
    system: str,
    output_lang: str,
) -> list[SummarizedStory]:
    from ..llm.batch import BatchProcessor

    processor = BatchProcessor()
    requests = []
    for candidate in candidates:
        requests.append(
            {
                "custom_id": candidate.id,
                "params": {
                    "model": SONNET,
                    "max_tokens": 2048,
                    "system": system,
                    "messages": [
                        {"role": "user", "content": _candidate_user_message(candidate)}
                    ],
                    "tools": [
                        {
                            "name": "output",
                            "description": "Output structured data",
                            "input_schema": _SCHEMA,
                        }
                    ],
                    "tool_choice": {"type": "tool", "name": "output"},
                },
            }
        )

    try:
        results = processor.run(requests)
    except Exception as exc:
        logger.warning("batch summarize failed, falling back to sequential: %s", exc)
        results = {}

    candidate_map = {c.id: c for c in candidates}
    stories: list[SummarizedStory] = []

    for candidate in candidates:
        raw = results.get(candidate.id)
        parsed: dict = {}
        if raw:
            try:
                parsed = json.loads(raw)
            except Exception:
                pass

        stories.append(
            SummarizedStory(
                id=candidate.id,
                headline=parsed.get("headline", candidate.title),
                deck=parsed.get("deck", ""),
                body_html=parsed.get("body_html", f"<p>{candidate.body[:500]}</p>"),
                byline=parsed.get("byline", candidate.source),
                lang_in=candidate.lang,
                lang_out=output_lang,
                source_url=candidate.url,
            )
        )

    return stories
