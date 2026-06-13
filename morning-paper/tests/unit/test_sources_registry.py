import pytest

from morning_paper import sources
from morning_paper.sources import get_source
from morning_paper.sources.base import InterestSource


def test_builtin_sources_registered():
    ids = sources.all_source_ids()
    assert "manual" in ids
    assert "rss" in ids


def test_get_source_returns_protocol_impl():
    src = get_source("manual")
    assert isinstance(src, InterestSource)
    assert src.source_id == "manual"
    assert src.requires_auth is False


def test_unknown_source_raises():
    with pytest.raises(KeyError):
        get_source("does-not-exist")


def test_duplicate_registration_rejected():
    from morning_paper.sources.registry import register

    class Dupe:
        source_id = "manual"

    with pytest.raises(ValueError):
        register(Dupe)
