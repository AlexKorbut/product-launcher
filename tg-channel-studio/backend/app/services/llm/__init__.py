"""LLM provider factory."""
from app.config import get_settings
from app.services.llm.anthropic_provider import AnthropicProvider
from app.services.llm.base import BaseProvider, LLMResult
from app.services.llm.openai_provider import OpenAIProvider

PROVIDERS = ("anthropic", "openai")


def get_provider(name: str | None = None) -> BaseProvider:
    """Resolve a provider by name, falling back to the configured default."""
    s = get_settings()
    chosen = (name or s.llm_provider or "anthropic").lower()
    if chosen == "openai":
        return OpenAIProvider(
            s.openai_model, s.openai_price_input_per_mtok, s.openai_price_output_per_mtok
        )
    return AnthropicProvider(
        s.generation_model, s.price_input_per_mtok, s.price_output_per_mtok
    )


__all__ = ["BaseProvider", "LLMResult", "get_provider", "PROVIDERS"]
