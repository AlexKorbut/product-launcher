from morning_paper.models import SignalKind
from morning_paper.sources import get_source
from morning_paper.sources.base import AuthState, SourceConfig


def _cfg(**options):
    return SourceConfig(source_id="manual", user_id="me", options=options)


def test_manual_emits_free_text_and_survey_signals():
    src = get_source("manual")
    cfg = _cfg(free_text="Слежу за ИИ и велоспортом", survey_topics=["tech/ai", "sport/cycling"])
    auth = AuthState(source_id="manual", user_id="me", status="connected")

    result = src.fetch(cfg, auth, cursor=None)

    kinds = [s.kind for s in result.signals]
    assert SignalKind.FREE_TEXT in kinds
    assert kinds.count(SignalKind.SURVEY) == 2
    assert result.cursor is None
    # free-text and survey are high-strength priors
    assert all(s.strength >= 0.8 for s in result.signals)


def test_manual_works_with_no_input():
    src = get_source("manual")
    result = src.fetch(_cfg(), AuthState(source_id="manual", user_id="me"), cursor=None)
    assert result.signals == []


def test_manual_signal_ids_are_stable():
    src = get_source("manual")
    cfg = _cfg(free_text="hello")
    a = src.fetch(cfg, AuthState(source_id="manual", user_id="me"), cursor=None)
    b = src.fetch(cfg, AuthState(source_id="manual", user_id="me"), cursor=None)
    assert a.signals[0].id == b.signals[0].id
