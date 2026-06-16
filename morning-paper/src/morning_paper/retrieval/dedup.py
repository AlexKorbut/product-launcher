from __future__ import annotations

import re

from .feeds import Candidate


def dedup_candidates(
    candidates: list[Candidate], *, similarity_threshold: float = 0.7
) -> list[Candidate]:
    """Remove near-duplicate articles based on title Jaccard similarity."""
    kept: list[Candidate] = []
    for candidate in candidates:
        words = _word_set(candidate.title)
        is_dup = False
        for existing in kept:
            if _jaccard(words, _word_set(existing.title)) >= similarity_threshold:
                # Keep the higher-scored one
                if candidate.score > existing.score:
                    kept.remove(existing)
                    kept.append(candidate)
                is_dup = True
                break
        if not is_dup:
            kept.append(candidate)
    return kept


def _word_set(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union > 0 else 0.0
