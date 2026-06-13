from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from ..llm.client import AnthropicClient
from ..llm.models import HAIKU
from ..models import Signal

logger = logging.getLogger(__name__)

TOPICS = ["мир", "политика", "бизнес", "технологии", "наука", "культура", "спорт", "стиль"]

_SYSTEM_PROMPT = (
    "You are a multilingual text classifier. "
    "Given a batch of news signals, classify each into one or more of these topics: "
    + ", ".join(TOPICS)
    + ". Also extract named entities (persons, organizations, places) normalized to title case. "
    "Detect the language of each signal text. "
    "Respond only by calling the output tool with the structured result."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "topics": {"type": "array", "items": {"type": "string"}},
                    "entities": {"type": "array", "items": {"type": "string"}},
                    "lang": {"type": "string"},
                },
                "required": ["topics", "entities", "lang"],
            },
        }
    },
    "required": ["results"],
}

_BATCH_SIZE = 10


@dataclass
class TaggedSignal:
    signal: Signal
    topics: list[str]
    entities: list[str]
    lang: str


def tag_signals(signals: list[Signal], *, client: AnthropicClient | None = None) -> list[TaggedSignal]:
    """Batch-tag up to 50 signals using Haiku structured output."""
    if not signals:
        return []

    if client is None:
        client = AnthropicClient()

    tagged: list[TaggedSignal] = []
    for batch_start in range(0, len(signals), _BATCH_SIZE):
        batch = signals[batch_start : batch_start + _BATCH_SIZE]
        items_text = "\n".join(
            f"{i + 1}. {sig.text[:400]}" for i, sig in enumerate(batch)
        )
        messages = [
            {
                "role": "user",
                "content": (
                    f"Classify these {len(batch)} signals. "
                    f"Return a 'results' array with exactly {len(batch)} items "
                    f"in the same order:\n\n{items_text}"
                ),
            }
        ]
        try:
            result = client.structured(
                messages,
                model=HAIKU,
                system=_SYSTEM_PROMPT,
                schema=_SCHEMA,
                tool_name="output",
                max_tokens=2048,
            )
            results = result.get("results", [])
        except Exception as exc:
            logger.warning("tag_signals batch failed: %s", exc)
            results = []

        for i, sig in enumerate(batch):
            if i < len(results):
                r = results[i]
                tagged.append(
                    TaggedSignal(
                        signal=sig,
                        topics=[t for t in r.get("topics", []) if t in TOPICS],
                        entities=r.get("entities", []),
                        lang=r.get("lang", ""),
                    )
                )
            else:
                tagged.append(TaggedSignal(signal=sig, topics=[], entities=[], lang=""))

    return tagged
