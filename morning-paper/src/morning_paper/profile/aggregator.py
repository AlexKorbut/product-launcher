from __future__ import annotations

from datetime import datetime, timezone

from .tagger import TaggedSignal


def aggregate_weights(
    tagged: list[TaggedSignal],
    *,
    existing_topics: dict[str, float] | None = None,
    existing_entities: dict[str, float] | None = None,
    decay: float = 0.85,
) -> tuple[dict[str, float], dict[str, float]]:
    """Aggregate topic + entity weights from tagged signals. Normalize to [0,1]."""
    topic_scores: dict[str, float] = {}
    entity_scores: dict[str, float] = {}
    now = datetime.now(timezone.utc)

    for ts in tagged:
        age_days = 0.0
        created_at = getattr(ts.signal, "created_at", None)
        if created_at is not None:
            try:
                delta = now - created_at
                age_days = max(0.0, delta.total_seconds() / 86400)
            except Exception:
                age_days = 0.0

        time_factor = decay ** age_days
        weight = getattr(ts.signal, "strength", 1.0) * time_factor

        for topic in ts.topics:
            topic_scores[topic] = topic_scores.get(topic, 0.0) + weight

        for entity in ts.entities:
            key = entity.strip()
            if key:
                entity_scores[key] = entity_scores.get(key, 0.0) + weight

    # Merge with existing using weighted average (30% existing, 70% new)
    if existing_topics:
        all_keys = set(topic_scores) | set(existing_topics)
        for k in all_keys:
            new_val = topic_scores.get(k, 0.0)
            old_val = existing_topics.get(k, 0.0)
            topic_scores[k] = 0.3 * old_val + 0.7 * new_val

    if existing_entities:
        all_keys = set(entity_scores) | set(existing_entities)
        for k in all_keys:
            new_val = entity_scores.get(k, 0.0)
            old_val = existing_entities.get(k, 0.0)
            entity_scores[k] = 0.3 * old_val + 0.7 * new_val

    topic_scores = _normalize(topic_scores)
    entity_scores = _normalize(entity_scores)

    return topic_scores, entity_scores


def _normalize(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return scores
    max_val = max(scores.values())
    if max_val == 0.0:
        return scores
    return {k: v / max_val for k, v in scores.items()}
