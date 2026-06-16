from morning_paper.models import SignalKind
from morning_paper.sources.base import AuthState, SourceConfig
from morning_paper.sources.markdown_prefs import MarkdownPrefsSource

_AUTH = AuthState(source_id="markdown_prefs", user_id="u", status="connected")

_MD = """\
# Tech interests

- Machine learning and *LLMs*
- Distributed systems
1. Rust programming

I have been following the open-source AI community for years and care deeply
about reproducible research.
"""


def _cfg(**options):
    return SourceConfig(source_id="markdown_prefs", user_id="u", options=options)


def test_bullets_become_survey_and_prose_becomes_free_text():
    src = MarkdownPrefsSource()
    result = src.fetch(_cfg(text=_MD), _AUTH, cursor=None)

    surveys = [s for s in result.signals if s.kind == SignalKind.SURVEY]
    free_text = [s for s in result.signals if s.kind == SignalKind.FREE_TEXT]

    # 2 bullets + 1 numbered item
    assert len(surveys) == 3
    assert len(free_text) == 1
    assert result.cursor is None

    survey_texts = {s.text for s in surveys}
    assert "Machine learning and LLMs" in survey_texts  # emphasis stripped
    assert "Distributed systems" in survey_texts
    assert "Rust programming" in survey_texts

    # nearest heading carried as an extra entity hint
    ml = next(s for s in surveys if s.text == "Machine learning and LLMs")
    assert "Machine learning and LLMs" in ml.entities_hint
    assert "Tech interests" in ml.entities_hint

    assert "reproducible research" in free_text[0].text


def test_missing_file_and_no_text_warns():
    src = MarkdownPrefsSource()
    result = src.fetch(_cfg(path="/no/such/file.md"), _AUTH, cursor=None)
    assert result.signals == []
    assert result.warnings


def test_signal_ids_are_stable():
    src = MarkdownPrefsSource()
    a = src.fetch(_cfg(text=_MD), _AUTH, cursor=None)
    b = src.fetch(_cfg(text=_MD), _AUTH, cursor=None)
    assert [s.id for s in a.signals] == [s.id for s in b.signals]
