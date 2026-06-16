"""Test profile builder with mock LLM client."""
from unittest.mock import MagicMock

import pytest

from morning_paper.models import Signal, SignalKind
from morning_paper.profile.tagger import TaggedSignal, tag_signals
from morning_paper.profile.builder import build_profile
from morning_paper.profile.aggregator import aggregate_weights


def test_aggregate_weights_basic():
    tagged = [
        TaggedSignal(
            signal=MagicMock(strength=1.0, created_at=None),
            topics=["технологии", "бизнес"],
            entities=["Apple"],
            lang="ru",
        ),
        TaggedSignal(
            signal=MagicMock(strength=0.8, created_at=None),
            topics=["технологии"],
            entities=[],
            lang="en",
        ),
    ]
    topics, entities = aggregate_weights(tagged)
    assert topics["технологии"] > topics["бизнес"]
    assert "Apple" in entities


def test_build_profile_empty_signals():
    profile = build_profile("user1", [], output_lang="ru")
    assert profile.user_id == "user1"
    assert profile.topics == {}


def test_aggregate_weights_normalization():
    tagged = [
        TaggedSignal(
            signal=MagicMock(strength=1.0, created_at=None),
            topics=["технологии"],
            entities=[],
            lang="ru",
        ),
    ]
    topics, _ = aggregate_weights(tagged)
    assert topics.get("технологии") == pytest.approx(1.0)


def test_aggregate_weights_with_existing():
    tagged = [
        TaggedSignal(
            signal=MagicMock(strength=1.0, created_at=None),
            topics=["наука"],
            entities=[],
            lang="ru",
        ),
    ]
    topics, _ = aggregate_weights(
        tagged,
        existing_topics={"наука": 0.5, "спорт": 0.9},
    )
    assert "наука" in topics
    assert "спорт" in topics
    # Normalization means max == 1.0
    assert max(topics.values()) == pytest.approx(1.0)
