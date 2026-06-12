"""Anthropic provider — uses the official Anthropic SDK with adaptive thinking."""
import anthropic

from app.config import get_settings
from app.services.llm.base import BaseProvider, LLMResult


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    async def complete(self, system: str, user: str, max_tokens: int, model: str | None = None) -> LLMResult:
        client = anthropic.AsyncAnthropic(api_key=get_settings().anthropic_api_key)
        response = await client.messages.create(
            model=model or self.default_model,
            max_tokens=max_tokens,
            thinking={"type": "adaptive"},
            system=[
                {
                    "type": "text",
                    "text": system,
                    # Stable per-channel system prompt — cache it across requests.
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user}],
        )
        text = next((b.text for b in response.content if b.type == "text"), "").strip()
        u = response.usage
        input_tokens = (
            u.input_tokens + (u.cache_creation_input_tokens or 0) + (u.cache_read_input_tokens or 0)
        )
        return LLMResult(text=text, model=response.model, input_tokens=input_tokens, output_tokens=u.output_tokens)
