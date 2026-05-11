"""
Product Analyst Agent — extracts structured product knowledge from OCR text.
Uses LLM to parse brochure text into ProductKB format.
"""
import json
from . import BaseAgent, LLMClient


PROMPT_SYSTEM = """Ты — эксперт по анализу продуктов. Из текста брошюры извлеки структурированную информацию.
Верни ТОЛЬКО валидный JSON (без markdown, без ```) по этой схеме:

{
  "product": {
    "name": "...",
    "tagline": "...",
    "description": "...",
    "usp": "...",
    "features": ["...", "..."],
    "specs": {"key": "value", ...},
    "price_range": "...",
    "category": "..."
  },
  "brand": {
    "tone_of_voice": {
      "primary": "professional | friendly | luxury | bold | minimal",
      "adjectives": ["...", "..."],
      "donts": ["...", "..."]
    },
    "colors": {
      "primary": "#HEX",
      "secondary": "#HEX",
      "accent": "#HEX"
    },
    "target_audience": {
      "demographics": "...",
      "pain_points": ["...", "..."],
      "platforms": ["Instagram", "TikTok", "Threads", ...]
    }
  },
  "market": {
    "competitors": ["...", "..."],
    "differentiator": "...",
    "geo_focus": "..."
  },
  "source": {
    "event": "...",
    "location": "...",
    "date": "..."
  }
}

Правила:
- Если информации нет — оставь пустую строку или []
- Цвета всегда в HEX (#RRGGBB), даже если в брошюре названия — сконвертируй
- tone_of_voice.primary — ВСЕГДА одно из: professional, friendly, luxury, bold, minimal
- Не выдумывай то, чего нет в тексте
"""


class ProductAnalyst(BaseAgent):
    """Extracts ProductKB from raw OCR text."""

    agent_name = "product-analyst"
    description = "Анализирует OCR-текст брошюры и создаёт структурированную базу знаний о продукте"

    def run(self, input_data: dict) -> dict:
        """
        Args:
            input_data: {"raw_text": "...", "images": [...], "event": "...", "location": "...", "date": "..."}

        Returns:
            ProductKB-compatible dict
        """
        raw_text = input_data.get("raw_text", "")
        if not raw_text.strip():
            return self._empty_result("No OCR text provided")

        self.log(f"Анализирую текст ({len(raw_text)} символов)...")

        messages = [
            {"role": "system", "content": PROMPT_SYSTEM},
            {"role": "user", "content": f"Проанализируй этот текст брошюры:\n\n{raw_text}"},
        ]

        response = self.llm.chat(messages, temperature=0.3, max_tokens=4096)

        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            result = self._extract_json(response)

        if not result:
            return self._empty_result("Failed to parse LLM response")

        # Ensure all required fields exist with defaults
        result.setdefault("product", {})
        result.setdefault("brand", {})
        result.setdefault("market", {})
        result.setdefault("source", {})

        result["product"].setdefault("name", "Неизвестный продукт")
        result["product"].setdefault("description", "")
        result["product"].setdefault("usp", "")
        result["product"].setdefault("features", [])
        result["product"].setdefault("specs", {})

        result["brand"].setdefault("tone_of_voice", {
            "primary": "professional",
            "adjectives": [],
            "donts": [],
        })
        result["brand"].setdefault("colors", {
            "primary": "#1A1A2E",
            "secondary": "#16213E",
            "accent": "#E94560",
        })
        result["brand"].setdefault("target_audience", {
            "demographics": "",
            "pain_points": [],
            "platforms": [],
        })

        result["market"].setdefault("competitors", [])
        result["market"].setdefault("differentiator", "")
        result["market"].setdefault("geo_focus", "")

        # Preserve source info from input
        result["source"] = {
            "event": input_data.get("event", ""),
            "location": input_data.get("location", ""),
            "date": input_data.get("date", ""),
            "raw_text": raw_text,
            "images": input_data.get("images", []),
        }

        self.log(f"✓ Извлечено: {result['product']['name']}")
        return result

    def _extract_json(self, text: str) -> dict | None:
        """Try to extract JSON from text that may contain markdown or extra content."""
        # Try to find JSON between { and }
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        return None

    def _empty_result(self, reason: str) -> dict:
        """Return empty result with error note."""
        return {
            "product": {
                "name": "—",
                "description": reason,
                "usp": "",
                "features": [],
                "specs": {},
            },
            "brand": {
                "tone_of_voice": {"primary": "professional", "adjectives": [], "donts": []},
                "colors": {"primary": "#1A1A2E", "secondary": "#16213E", "accent": "#E94560"},
                "target_audience": {"demographics": "", "pain_points": [], "platforms": []},
            },
            "market": {"competitors": [], "differentiator": "", "geo_focus": ""},
            "source": {"event": "", "location": "", "date": "", "raw_text": "", "images": []},
        }
