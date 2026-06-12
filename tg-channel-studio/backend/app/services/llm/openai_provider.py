"""OpenAI-compatible provider.

Works with OpenAI and any OpenAI-compatible endpoint (OpenRouter, DeepSeek,
Together, Groq, local servers) by setting OPENAI_BASE_URL.
"""
from app.config import get_settings
from app.services.llm.base import BaseProvider, LLMResult


class OpenAIProvider(BaseProvider):
    name = "openai"

    async def complete(self, system: str, user: str, max_tokens: int, model: str | None = None) -> LLMResult:
        from openai import AsyncOpenAI  # imported lazily so the dep is optional

        s = get_settings()
        client = AsyncOpenAI(api_key=s.openai_api_key, base_url=s.openai_base_url or None)
        response = await client.chat.completions.create(
            model=model or self.default_model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        text = (response.choices[0].message.content or "").strip()
        usage = response.usage
        return LLMResult(
            text=text,
            model=response.model,
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
        )
