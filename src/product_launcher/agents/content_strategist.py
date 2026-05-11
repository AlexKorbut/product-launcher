"""
Content Strategist Agent — creates multi-platform content strategy from ProductKB.
Generates: content pillars, hooks, platform-specific plans, tone guidelines, calendar.
"""
import json
from . import BaseAgent, LLMClient


PROMPT_SYSTEM = """Ты — креативный стратег по контент-маркетингу. 
На основе информации о продукте создай комплексную контент-стратегию.

Верни ТОЛЬКО валидный JSON (без ```, без markdown):

{
  "strategy_name": "Название стратегии",
  "content_pillars": [
    {
      "name": "Название пиллара",
      "description": "О чём контент в этом пилларе",
      "angle": "Угол подачи",
      "hashtags": ["#тег1", "#тег2"]
    }
  ],
  "target_hooks": [
    "Цепляющий заголовок 1",
    "Цепляющий заголовок 2"
  ],
  "platforms": {
    "instagram": {
      "format": "Карусели / Reels / Stories",
      "frequency": "N постов/неделя",
      "tone_notes": "Особенности тона для этой платформы",
      "examples": ["Пример поста 1", "Пример поста 2"]
    },
    "tiktok": {
      "format": "Короткие видео 15-60 сек",
      "frequency": "N видео/день",
      "tone_notes": "Особенности тона для TikTok",
      "examples": ["Пример видео 1", "Пример видео 2"]
    },
    "threads": {
      "format": "Текстовые треды",
      "frequency": "N тредов/день",
      "tone_notes": "Особенности для Threads",
      "examples": ["Пример треда 1", "Пример треда 2"]
    },
    "website": {
      "format": "Лендинг",
      "sections": ["Секция 1", "Секция 2", "..."],
      "tone_notes": "Тон для лендинга"
    }
  },
  "tone_of_voice": {
    "primary": "friendly | professional | luxury | bold | minimal",
    "rules": ["Правило 1", "Правило 2"]
  },
  "content_calendar": {
    "week_1": "Тема недели 1",
    "week_2": "Тема недели 2",
    "week_3": "Тема недели 3",
    "week_4": "Тема недели 4"
  }
}

Правила:
- 3-5 content pillars, каждый с хештегами
- 3-6 цепляющих хуков
- Для каждой платформы — формат, частота и 2-3 примера
- Тон: придерживайся того, что указано в ProductKB
- Календарь на 4 недели
- Пиши на русском языке
- Будь конкретным, не используй общие фразы
"""


class ContentStrategist(BaseAgent):
    """Generates multi-platform content strategy from ProductKB."""

    agent_name = "content-strategist"
    description = "Создаёт контент-стратегию для всех платформ на основе ProductKB"

    def run(self, input_data: dict) -> dict:
        """
        Args:
            input_data: {"kb": <ProductKB dict from ProductAnalyst>}

        Returns:
            Content strategy dict with pillars, hooks, platforms, tone, calendar
        """
        kb = input_data.get("kb", {})
        product = kb.get("product", {})
        brand = kb.get("brand", {})
        market = kb.get("market", {})

        product_name = product.get("name", "Продукт")
        self.log(f"Создаю стратегию для: {product_name}")

        # Build prompt
        user_prompt = self._build_prompt(kb)

        messages = [
            {"role": "system", "content": PROMPT_SYSTEM},
            {"role": "user", "content": user_prompt},
        ]

        response = self.llm.chat(messages, temperature=0.7, max_tokens=4096)

        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            result = self._extract_json(response)

        if not result:
            self.log("⚠️ Не удалось распарсить ответ LLM, использую fallback")
            return self._fallback_strategy(kb)

        # Ensure all required fields
        result = self._ensure_defaults(result, kb)
        
        self.log(f"✓ Стратегия готова: {len(result['content_pillars'])} пилларов, "
                 f"{len(result['target_hooks'])} хуков")
        return result

    def _build_prompt(self, kb: dict) -> str:
        """Build a detailed prompt from ProductKB."""
        product = kb.get("product", {})
        brand = kb.get("brand", {})
        market = kb.get("market", {})

        parts = []

        # Product info
        parts.append(f"## Продукт\n")
        parts.append(f"Название: {product.get('name', '—')}")
        if product.get("tagline"):
            parts.append(f"Слоган: {product['tagline']}")
        parts.append(f"Описание: {product.get('description', '—')}")
        parts.append(f"УТП: {product.get('usp', '—')}")
        
        features = product.get("features", [])
        if features:
            parts.append(f"Ключевые фичи: {', '.join(features)}")
        
        specs = product.get("specs", {})
        if specs:
            parts.append(f"Характеристики: {json.dumps(specs, ensure_ascii=False)}")
        
        if product.get("price_range"):
            parts.append(f"Цена: {product['price_range']}")
        if product.get("category"):
            parts.append(f"Категория: {product['category']}")

        # Brand info
        tone = brand.get("tone_of_voice", {})
        colors = brand.get("colors", {})
        audience = brand.get("target_audience", {})

        parts.append(f"\n## Бренд\n")
        parts.append(f"Тон: {tone.get('primary', 'professional')}")
        if tone.get("adjectives"):
            parts.append(f"Прилагательные: {', '.join(tone['adjectives'])}")
        if tone.get("donts"):
            parts.append(f"НЕ использовать: {', '.join(tone['donts'])}")
        parts.append(f"Цвета: primary={colors.get('primary', '?')}, secondary={colors.get('secondary', '?')}, accent={colors.get('accent', '?')}")
        parts.append(f"Аудитория: {audience.get('demographics', '—')}")
        if audience.get("pain_points"):
            parts.append(f"Боли: {', '.join(audience['pain_points'])}")
        if audience.get("platforms"):
            parts.append(f"Платформы: {', '.join(audience['platforms'])}")

        # Market
        parts.append(f"\n## Рынок\n")
        if market.get("competitors"):
            parts.append(f"Конкуренты: {', '.join(market['competitors'])}")
        parts.append(f"Дифференциатор: {market.get('differentiator', '—')}")
        parts.append(f"Гео: {market.get('geo_focus', '—')}")

        return "\n".join(parts)

    def _extract_json(self, text: str) -> dict | None:
        """Try to extract JSON from LLM response."""
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        return None

    def _ensure_defaults(self, result: dict, kb: dict) -> dict:
        """Fill missing fields with sensible defaults."""
        result.setdefault("strategy_name", f"Стратегия для {kb.get('product', {}).get('name', 'продукта')}")
        result.setdefault("content_pillars", self._default_pillars(kb))
        result.setdefault("target_hooks", self._default_hooks(kb))
        result.setdefault("platforms", self._default_platforms(kb))
        result.setdefault("tone_of_voice", {
            "primary": kb.get("brand", {}).get("tone_of_voice", {}).get("primary", "professional"),
            "rules": ["Будь полезным", "Избегай клише"],
        })
        result.setdefault("content_calendar", {
            "week_1": "Знакомство с продуктом",
            "week_2": "Технологии и фичи",
            "week_3": "Социальные доказательства",
            "week_4": "Призыв к действию",
        })
        return result

    def _fallback_strategy(self, kb: dict) -> dict:
        """Generate a minimal viable strategy without LLM."""
        product_name = kb.get("product", {}).get("name", "Продукт")
        features = kb.get("product", {}).get("features", [])
        platform_list = kb.get("brand", {}).get("target_audience", {}).get("platforms", ["Instagram", "TikTok", "Threads"])

        return {
            "strategy_name": f"Базовая стратегия: {product_name}",
            "content_pillars": self._default_pillars(kb),
            "target_hooks": self._default_hooks(kb),
            "platforms": self._default_platforms(kb),
            "tone_of_voice": {
                "primary": kb.get("brand", {}).get("tone_of_voice", {}).get("primary", "professional"),
                "rules": ["Акцент на преимущества", "Избегай общих фраз", "Показывай, а не рассказывай"],
            },
            "content_calendar": {
                "week_1": "Тизер: что это и зачем",
                "week_2": "Демонстрация возможностей",
                "week_3": "Кейсы и отзывы",
                "week_4": "Спецпредложение",
            },
        }

    def _default_pillars(self, kb: dict) -> list[dict]:
        """Generate default content pillars from KB."""
        product_name = kb.get("product", {}).get("name", "Продукт")
        features = kb.get("product", {}).get("features", [])
        usp = kb.get("product", {}).get("usp", "")

        pillars = [
            {
                "name": "Продукт",
                "description": f"Что такое {product_name} и как он работает",
                "angle": "Знакомство с инновацией",
                "hashtags": ["#новинка", f"#{product_name.lower().replace(' ', '')}"],
            },
        ]

        if features:
            pillars.append({
                "name": "Технология",
                "description": f"Ключевые фичи: {', '.join(features[:3])}",
                "angle": "Как это работает",
                "hashtags": ["#технологии", "#инновации"],
            })

        pillars.append({
            "name": "Результат",
            "description": "Как продукт меняет жизнь пользователя",
            "angle": "До и после",
            "hashtags": ["#результат", "#лайфхак"],
        })

        return pillars

    def _default_hooks(self, kb: dict) -> list[str]:
        """Generate default hooks."""
        product_name = kb.get("product", {}).get("name", "Продукт")
        return [
            f"Почему {product_name} — это то, что вам нужно",
            f"3 причины выбрать {product_name}",
            f"Как {product_name} экономит ваше время",
        ]

    def _default_platforms(self, kb: dict) -> dict:
        """Generate default platform strategies."""
        return {
            "instagram": {
                "format": "Карусели и Reels",
                "frequency": "5 постов/неделя",
                "tone_notes": "Визуальный, вдохновляющий",
                "examples": ["Обзор продукта в карусели", "Reels с демонстрацией"],
            },
            "tiktok": {
                "format": "Короткие видео 15-30 сек",
                "frequency": "2-3 видео/день",
                "tone_notes": "Динамичный, нативный",
                "examples": ["Тренд с продуктом", "POV: утро с продуктом"],
            },
            "threads": {
                "format": "Текстовые треды",
                "frequency": "2 треда/день",
                "tone_notes": "Экспертный, честный",
                "examples": ["Тред: мифы о категории", "Обсуждение болей аудитории"],
            },
            "website": {
                "format": "Лендинг",
                "sections": ["Hero", "Фичи", "Отзывы", "Цена", "CTA"],
                "tone_notes": "Продающий, доверительный",
            },
        }
