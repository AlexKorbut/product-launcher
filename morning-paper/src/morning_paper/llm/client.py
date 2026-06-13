from __future__ import annotations

from anthropic import Anthropic

from .models import HAIKU, OPUS, SONNET


class AnthropicClient:
    def __init__(self, api_key: str | None = None) -> None:
        self._client = Anthropic(api_key=api_key)

    def _create(self, **kwargs):
        """Single chokepoint for the SDK call. Subclasses (see metering.MeteredClient)
        override this to observe response.usage without touching public behavior."""
        return self._client.messages.create(**kwargs)

    def _normalize_system(self, system: str | list[dict] | None) -> list[dict] | None:
        if system is None:
            return None
        if isinstance(system, str):
            return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        return system

    def complete(
        self,
        messages: list[dict],
        *,
        model: str = SONNET,
        system: str | list[dict] | None = None,
        max_tokens: int = 2048,
        temperature: float = 1.0,
        thinking: dict | None = None,
    ) -> str:
        """Returns the text of the first content block."""
        kwargs: dict = dict(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
        )
        normalized = self._normalize_system(system)
        if normalized is not None:
            kwargs["system"] = normalized
        if thinking is not None:
            kwargs["thinking"] = thinking
            kwargs["temperature"] = 1.0
        else:
            kwargs["temperature"] = temperature
        response = self._create(**kwargs)
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return ""

    def structured(
        self,
        messages: list[dict],
        *,
        model: str = SONNET,
        system: str | list[dict] | None = None,
        schema: dict,
        tool_name: str = "output",
        max_tokens: int = 4096,
    ) -> dict:
        """Force a tool call and return the parsed input dict."""
        normalized = self._normalize_system(system)
        kwargs: dict = dict(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            tools=[{"name": tool_name, "description": "Output structured data", "input_schema": schema}],
            tool_choice={"type": "tool", "name": tool_name},
        )
        if normalized is not None:
            kwargs["system"] = normalized
        response = self._create(**kwargs)
        for block in response.content:
            if getattr(block, "type", None) == "tool_use":
                return block.input
        return {}

    def count_tokens(
        self,
        messages: list[dict],
        *,
        model: str = SONNET,
        system: str | None = None,
    ) -> int:
        """Estimate token count without running the full request."""
        kwargs: dict = dict(model=model, messages=messages)
        if system is not None:
            kwargs["system"] = system
        result = self._client.messages.count_tokens(**kwargs)
        return result.input_tokens
