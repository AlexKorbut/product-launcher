from __future__ import annotations

from .feeds import Candidate
from ..models import InterestProfile


def rank_candidates(
    candidates: list[Candidate],
    profile: InterestProfile,
    *,
    top_n: int = 40,
) -> list[Candidate]:
    """Score each candidate by topic/entity overlap with profile weights. Return top_n."""
    for c in candidates:
        c.score = _score(c, profile)
    return sorted(candidates, key=lambda x: x.score, reverse=True)[:top_n]


def _score(candidate: Candidate, profile: InterestProfile) -> float:
    text = (candidate.title + " " + candidate.body).lower()
    score = 0.0

    for topic, weight in profile.topics.items():
        if topic.lower() in text:
            score += weight

    for entity, weight in profile.entities.items():
        if entity.lower() in text:
            score += weight * 0.5

    max_possible = sum(profile.topics.values()) + sum(v * 0.5 for v in profile.entities.values())
    if max_possible > 0:
        score = score / max_possible

    return score
