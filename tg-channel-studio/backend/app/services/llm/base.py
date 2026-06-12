"""Provider-agnostic LLM interface used by the rewrite service."""
from dataclasses import dataclass


@dataclass
class LLMResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int


class BaseProvider:
    """Base class for chat-completion providers.

    Subclasses implement `complete()`. Pricing (per 1M tokens) is injected so
    cost — and therefore credits charged — is computed consistently per provider.
    """

    name: str = "base"

    def __init__(self, default_model: str, price_in_per_mtok: float, price_out_per_mtok: float):
        self.default_model = default_model
        self.price_in = price_in_per_mtok
        self.price_out = price_out_per_mtok

    async def complete(self, system: str, user: str, max_tokens: int, model: str | None = None) -> LLMResult:
        raise NotImplementedError

    def cost_usd(self, result: LLMResult) -> float:
        return result.input_tokens * self.price_in / 1_000_000 + result.output_tokens * self.price_out / 1_000_000
