"""MeteredClient records usage from response.usage without network."""

from __future__ import annotations

from morning_paper.economics import cost_of
from morning_paper.llm.client import AnthropicClient
from morning_paper.metering import ListUsageSink, MeteredClient


class _FakeUsage:
    input_tokens = 1234
    output_tokens = 567
    cache_read_input_tokens = 100


class _FakeBlock:
    text = "hi there"


class _FakeResp:
    usage = _FakeUsage()
    content = [_FakeBlock()]
    model = "claude-sonnet-4-6"


def test_metered_client_records_event(monkeypatch):
    # Bypass the real SDK call: parent _create returns a fake response.
    monkeypatch.setattr(AnthropicClient, "_create", lambda self, **kw: _FakeResp())

    sink = ListUsageSink()
    client = MeteredClient(
        user_id="u1",
        issue_id="i1",
        stage="editorial",
        sink=sink,
        api_key="test",
    )

    out = client.complete(
        [{"role": "user", "content": "hi"}], model="claude-sonnet-4-6"
    )
    assert out == "hi there"

    assert len(sink.events) == 1
    ev = sink.events[0]
    assert ev.user_id == "u1"
    assert ev.issue_id == "i1"
    assert ev.stage == "editorial"
    assert ev.model == "claude-sonnet-4-6"
    assert ev.tokens_in == 1234
    assert ev.tokens_out == 567
    assert ev.cached_in == 100
    assert ev.batch is False
    assert ev.cost_usd == cost_of("claude-sonnet-4-6", 1234, 567, cached_in=100)
