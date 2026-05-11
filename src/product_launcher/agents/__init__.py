"""
Agent framework — base classes and LLM client.
All agents inherit from BaseAgent and use the shared LLM client.
"""
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    provider: str = "deepseek"
    model: str = "deepseek-v4-pro"
    api_key: str = ""
    base_url: str = "https://api.deepseek.com/v1"

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Create config from environment variables."""
        return cls(
            provider=os.environ.get("LLM_PROVIDER", "deepseek"),
            model=os.environ.get("LLM_MODEL", "deepseek-chat"),
            api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
            base_url=os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1"),
        )


class LLMClient:
    """Unified LLM client for all agents."""

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig.from_env()

    def chat(self, messages: list[dict], temperature: float = 0.3, max_tokens: int = 4096) -> str:
        """Send a chat completion request. Override for different providers."""
        import urllib.request
        import urllib.error

        api_key = self.config.api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            return self._mock_response(messages)

        url = f"{self.config.base_url}/chat/completions"
        body = json.dumps({
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }).encode()

        req = urllib.request.Request(url, data=body, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        })

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            # Fallback to mock for development
            return self._mock_response(messages)

    def _mock_response(self, messages: list[dict]) -> str:
        """Mock LLM response for development/testing."""
        last_msg = messages[-1]["content"] if messages else ""
        return json.dumps({
            "analysis": f"Mock analysis of: {last_msg[:100]}...",
            "confidence": 0.85,
            "note": "MOCK — no API key configured",
        }, ensure_ascii=False)


class BaseAgent(ABC):
    """Base class for all Product Launcher agents."""

    agent_name: str = "base"
    description: str = ""

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()

    @abstractmethod
    def run(self, input_data: dict) -> dict:
        """Execute the agent's main task. Returns output dict."""
        ...

    def log(self, message: str) -> None:
        """Log agent activity."""
        print(f"  [{self.agent_name}] {message}")
