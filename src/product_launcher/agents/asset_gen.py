"""
Asset Generator — creates visual asset descriptions (images, icons, brand kit).
Output is used by designers or image generation AIs.
"""
import json
from . import BaseAgent, LLMClient


PROMPT = """Ты — арт-директор. Создай список визуальных ассетов для маркетинговой кампании.

Верни ТОЛЬКО валидный JSON:

{
  "assets": [
    {
      "id": "a1",
      "type": "hero_image | feature_icon | social_post | banner | infographic",
      "description": "Подробное описание визуала (50-100 слов)",
      "style": "Стиль (премиум, минимализм, техно, etc)",
      "dimensions": "WxH в пикселях",
      "colors": ["#HEX1", "#HEX2"]
    }
  ],
  "brand_kit": {
    "logo_variants": ["Вариант 1", "Вариант 2"],
    "typography": "Названия шрифтов",
    "mood": "Описание настроения (2-3 предложения)"
  }
}

Правила:
- Минимум 3 ассета разных типов
- Цвета из brand.colors
- Размеры реалистичные (hero: 1200x628, icon: 512x512, post: 1080x1080)
- Описания детальные — дизайнер должен понять что рисовать
- На русском языке
"""


class AssetGenerator(BaseAgent):
    agent_name = "asset-gen"
    description = "Генерирует описания визуальных ассетов для дизайнеров/ИИ"

    def run(self, input_data: dict) -> dict:
        strategy = input_data.get("strategy", {})
        kb = input_data.get("kb", {})

        self.log("Генерирую визуальные ассеты...")

        prompt = self._build_prompt(strategy, kb)
        messages = [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.chat(messages, temperature=0.8, max_tokens=4096)
        result = self._parse(response)

        if not result:
            self.log("⚠️ Fallback для ассетов")
            result = self._fallback(strategy, kb)

        self.log(f"✓ {len(result.get('assets', []))} ассетов + brand kit")
        return result

    def _build_prompt(self, strategy: dict, kb: dict) -> str:
        product = kb.get("product", {})
        brand = kb.get("brand", {})
        colors = brand.get("colors", {})

        parts = [
            f"Продукт: {product.get('name', '—')}",
            f"УТП: {product.get('usp', '—')}",
            f"Цвета бренда: primary={colors.get('primary')}, secondary={colors.get('secondary')}, accent={colors.get('accent')}",
        ]

        tone = strategy.get("tone_of_voice", {})
        parts.append(f"Тон: {tone.get('primary', 'friendly')}")

        pillars = strategy.get("content_pillars", [])
        if pillars:
            parts.append(f"Пиллары: {', '.join(p['name'] for p in pillars)}")

        return "\n".join(parts)

    def _parse(self, response: str) -> dict | None:
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            start = response.find("{")
            end = response.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(response[start:end + 1])
                except json.JSONDecodeError:
                    pass
        return None

    def _fallback(self, strategy: dict, kb: dict) -> dict:
        name = kb.get("product", {}).get("name", "Продукт")
        colors = kb.get("brand", {}).get("colors", {})
        c1 = colors.get("primary", "#1A1A2E")
        c2 = colors.get("secondary", "#16213E")
        c3 = colors.get("accent", "#E94560")

        return {
            "assets": [
                {"id": "a1", "type": "hero_image", "description": f"{name} на тёмном градиентном фоне ({c1} → {c2}), акцентный свет {c3}, минималистичная композиция", "style": "Премиум, минимализм", "dimensions": "1200x628", "colors": [c1, c2, c3]},
                {"id": "a2", "type": "feature_icon", "description": f"Иконки ключевых фич {name} в едином стиле — глянцевые, техно, с градиентом {c2}→{c3}", "style": "Техно, глянцевый", "dimensions": "512x512", "colors": [c2, c3]},
                {"id": "a3", "type": "social_post", "description": f"Квадратный постер для Instagram: {name} в центре, тёмный фон, акцентные линии {c3}, текст {c3}", "style": "Минимализм, премиум", "dimensions": "1080x1080", "colors": [c1, c3]},
            ],
            "brand_kit": {
                "logo_variants": ["Основной (светлый на тёмном)", "Монохромный"],
                "typography": "Inter / SF Pro Display",
                "mood": f"Технологичный, тёплый, премиальный. {name} — это будущее, которое уже здесь.",
            },
        }
