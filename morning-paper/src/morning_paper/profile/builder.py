from __future__ import annotations

from ..llm.client import AnthropicClient
from ..models import InterestProfile, Signal
from .aggregator import aggregate_weights
from .tagger import tag_signals


def build_profile(
    user_id: str,
    signals: list[Signal],
    *,
    existing: InterestProfile | None = None,
    output_lang: str = "ru",
    client: AnthropicClient | None = None,
) -> InterestProfile:
    """Tag signals, aggregate weights, return updated InterestProfile."""
    if not signals:
        return existing or InterestProfile(user_id=user_id, output_lang=output_lang)

    tagged = tag_signals(signals, client=client)
    topics, entities = aggregate_weights(
        tagged,
        existing_topics=existing.topics if existing else None,
        existing_entities=existing.entities if existing else None,
    )
    return InterestProfile(
        user_id=user_id,
        output_lang=output_lang,
        topics=topics,
        entities=entities,
        interest_vectors=[],
    )
