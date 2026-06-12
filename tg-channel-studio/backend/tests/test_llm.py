from app.services.llm import get_provider
from app.services.llm.anthropic_provider import AnthropicProvider
from app.services.llm.base import LLMResult
from app.services.llm.openai_provider import OpenAIProvider


def test_default_provider_is_anthropic():
    p = get_provider()
    assert isinstance(p, AnthropicProvider)
    assert p.name == "anthropic"


def test_select_openai_provider():
    p = get_provider("openai")
    assert isinstance(p, OpenAIProvider)
    assert p.default_model  # configured model present


def test_select_is_case_insensitive_and_falls_back():
    assert isinstance(get_provider("ANTHROPIC"), AnthropicProvider)
    assert isinstance(get_provider("unknown-provider"), AnthropicProvider)


def test_cost_uses_provider_pricing():
    anth = get_provider("anthropic")   # 5 / 25 per 1M by default
    oai = get_provider("openai")       # 2.5 / 10 per 1M by default
    r = LLMResult(text="x", model="m", input_tokens=1_000_000, output_tokens=1_000_000)
    assert abs(anth.cost_usd(r) - 30.0) < 1e-6
    assert abs(oai.cost_usd(r) - 12.5) < 1e-6


async def test_rewrite_uses_channel_provider(monkeypatch):
    """A channel's llm_provider/llm_model override drives generation + cost."""
    from app.models import Channel
    from app.services import rewrite
    from app.services.llm.base import LLMResult as R

    captured = {}

    class FakeProvider:
        name = "openai"
        default_model = "gpt-4o"
        price_in = 2.5
        price_out = 10.0

        async def complete(self, system, user, max_tokens, model=None):
            captured["model"] = model
            return R(text="переписанный пост", model=model or "gpt-4o", input_tokens=1000, output_tokens=500)

        def cost_usd(self, result):
            return 0.02

    def fake_get_provider(name=None):
        captured["provider"] = name
        return FakeProvider()

    monkeypatch.setattr(rewrite, "get_provider", fake_get_provider)
    ch = Channel(name="c", username="c", bot_token_encrypted="", rewrite_level=2,
                 llm_provider="openai", llm_model="gpt-4o-mini")
    res = await rewrite.rewrite_post(ch, "исходный пост" * 10)
    assert captured["provider"] == "openai"
    assert captured["model"] == "gpt-4o-mini"
    assert res.text == "переписанный пост"
    assert res.cost_usd == 0.02 and res.credits > 0
