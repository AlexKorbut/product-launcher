"""
Content Generators — create platform-specific content from strategy.
Website, TikTok, Instagram, Threads — each with specialized prompts.
"""
import json
from . import BaseAgent, LLMClient


# ═══════════════════════════════════════════════
#  PROMPTS
# ═══════════════════════════════════════════════

WEBSITE_PROMPT = """Ты — копирайтер и дизайнер лендингов.
Создай структуру лендинга на основе контент-стратегии.

Верни ТОЛЬКО валидный JSON:

{
  "sections": [
    {
      "id": "hero",
      "headline": "Заголовок",
      "subheadline": "Подзаголовок",
      "cta": "Текст кнопки",
      "visual": "Описание визуала"
    },
    {
      "id": "features",
      "headline": "Заголовок секции",
      "items": [
        {"title": "Фича", "desc": "Описание"}
      ]
    },
    {
      "id": "social_proof",
      "headline": "Заголовок",
      "testimonials": [
        {"name": "Имя", "text": "Отзыв", "role": "Роль"}
      ]
    },
    {
      "id": "pricing",
      "headline": "Заголовок",
      "price": "Цена",
      "includes": ["Что входит"]
    },
    {
      "id": "cta_final",
      "headline": "Финальный заголовок",
      "cta": "Текст кнопки",
      "urgency": "Срочность (опционально)"
    }
  ],
  "meta": {
    "title": "SEO title",
    "description": "SEO description"
  }
}

Правила:
- Минимум 3 секции (hero, features, cta_final — обязательно)
- Заголовки — цепляющие, конкретные
- На русском языке
- Не используй общие фразы
"""

TIKTOK_PROMPT = """Ты — сценарист TikTok-видео.
Создай 3 сценария для коротких видео (15-60 сек).

Верни ТОЛЬКО валидный JSON:

{
  "scripts": [
    {
      "id": "t1",
      "hook": "Цепляющая первая фраза/текст на экране",
      "duration_sec": 25,
      "scenes": [
        {
          "time": "0-3s",
          "visual": "Что в кадре",
          "text": "Текст на экране",
          "sound": "Звук/музыка"
        }
      ],
      "hashtags": ["#тег1", "#тег2"],
      "trend_note": "На какой тренд похоже (опционально)"
    }
  ]
}

Правила:
- 3 разных сценария
- Хук в первые 3 секунды — самый важный
- Нативный стиль, не рекламный
- На русском языке
- Используй актуальные TikTok-форматы
"""

INSTAGRAM_PROMPT = """Ты — SMM-менеджер Instagram.
Создай 2 карусели и 1 Reels на основе стратегии.

Верни ТОЛЬКО валидный JSON:

{
  "carousels": [
    {
      "id": "ig1",
      "slides": [
        {"image_desc": "Описание картинки", "text": "Текст на слайде"}
      ],
      "caption": "Текст поста (до 2200 символов)",
      "hashtags": ["#тег1", "#тег2"]
    }
  ],
  "reels": [
    {
      "id": "r1",
      "hook": "Цепляющее начало",
      "duration_sec": 30,
      "description": "Описание Reels"
    }
  ]
}

Правила:
- Карусели: 4-7 слайдов каждая
- Reels: короткий, динамичный сценарий
- Визуальный стиль — премиальный
- На русском языке
- Хештеги релевантные
"""

THREADS_PROMPT = """Ты — автор контента для Threads.
Создай 2 текстовых треда на основе стратегии.

Верни ТОЛЬКО валидный JSON:

{
  "threads": [
    {
      "id": "th1",
      "title": "Заголовок первого поста в треде",
      "posts": [
        "1/N Текст первого поста...",
        "2/N Текст второго поста..."
      ]
    }
  ]
}

Правила:
- Каждый тред: 5-8 постов
- Первый пост — хук, привлекающий внимание
- Разговорный стиль, как в соцсетях
- Без рекламных штампов
- На русском языке
- Заканчивай вопросом к аудитории или призывом к обсуждению
"""


# ═══════════════════════════════════════════════
#  BASE GENERATOR
# ═══════════════════════════════════════════════

class ContentGenerator(BaseAgent):
    """Base class for all content generators."""

    prompt_system: str = ""
    platform: str = ""

    def run(self, input_data: dict) -> dict:
        strategy = input_data.get("strategy", {})
        kb = input_data.get("kb", {})

        self.log(f"Генерирую контент для {self.platform}...")

        prompt = self._build_prompt(strategy, kb)
        messages = [
            {"role": "system", "content": self.prompt_system},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.chat(messages, temperature=0.8, max_tokens=4096)
        result = self._parse(response)

        if not result:
            self.log(f"⚠️ Fallback для {self.platform}")
            result = self._fallback(strategy, kb)

        self.log(f"✓ {self.platform}: готово")
        return result

    def _build_prompt(self, strategy: dict, kb: dict) -> str:
        """Build platform-specific prompt from strategy + KB."""
        parts = []

        product = kb.get("product", {})
        parts.append(f"Продукт: {product.get('name', '—')}")
        parts.append(f"УТП: {product.get('usp', '—')}")
        features = product.get("features", [])
        if features:
            parts.append(f"Фичи: {', '.join(features)}")
        if product.get("price_range"):
            parts.append(f"Цена: {product['price_range']}")

        tone = strategy.get("tone_of_voice", {})
        parts.append(f"\nТон: {tone.get('primary', 'friendly')}")
        rules = tone.get("rules", [])
        if rules:
            parts.append(f"Правила тона: {'; '.join(rules)}")

        hooks = strategy.get("target_hooks", [])
        if hooks:
            parts.append(f"\nКлючевые хуки: {' | '.join(hooks[:4])}")

        pillars = strategy.get("content_pillars", [])
        if pillars:
            parts.append(f"\nКонтент-пиллары:")
            for cp in pillars:
                parts.append(f"  - {cp['name']}: {cp.get('angle', '')}")

        platform_strat = strategy.get("platforms", {}).get(self.platform, {})
        if platform_strat:
            parts.append(f"\nСтратегия для {self.platform}:")
            parts.append(f"  Формат: {platform_strat.get('format', '—')}")
            parts.append(f"  Частота: {platform_strat.get('frequency', '—')}")
            parts.append(f"  Тон: {platform_strat.get('tone_notes', '—')}")

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
        """Platform-specific fallback — override in subclasses."""
        raise NotImplementedError


# ═══════════════════════════════════════════════
#  PLATFORM GENERATORS
# ═══════════════════════════════════════════════

class WebsiteGenerator(ContentGenerator):
    agent_name = "website-gen"
    description = "Генерирует структуру лендинга"
    prompt_system = WEBSITE_PROMPT
    platform = "website"

    def _fallback(self, strategy: dict, kb: dict) -> dict:
        name = kb.get("product", {}).get("name", "Продукт")
        usp = kb.get("product", {}).get("usp", "Инновационное решение")
        return {
            "sections": [
                {"id": "hero", "headline": f"{name} — {usp}", "subheadline": "", "cta": "Узнать больше", "visual": ""},
                {"id": "features", "headline": "Ключевые возможности", "items": [
                    {"title": f, "desc": ""} for f in kb.get("product", {}).get("features", ["Фича 1"])[:4]
                ]},
                {"id": "cta_final", "headline": "Готовы попробовать?", "cta": "Оформить предзаказ", "urgency": ""},
            ],
            "meta": {"title": f"{name} | Официальный сайт", "description": usp},
        }


class TikTokGenerator(ContentGenerator):
    agent_name = "tiktok-gen"
    description = "Создаёт сценарии для TikTok"
    prompt_system = TIKTOK_PROMPT
    platform = "tiktok"

    def _fallback(self, strategy: dict, kb: dict) -> dict:
        name = kb.get("product", {}).get("name", "Продукт")
        hook = strategy.get("target_hooks", [f"Революция {name}"])[0]
        return {
            "scripts": [{
                "id": "t1",
                "hook": hook[:60],
                "duration_sec": 25,
                "scenes": [
                    {"time": "0-3s", "visual": "Крупный план продукта", "text": hook, "sound": "Трендовый трек"},
                    {"time": "3-20s", "visual": "Демонстрация использования", "text": f"{name} — {kb.get('product', {}).get('usp', '')}", "sound": "Трек продолжается"},
                    {"time": "20-25s", "visual": "Результат + логотип", "text": "Жми ❤️ если хочешь такой же", "sound": "Бит дроп"},
                ],
                "hashtags": ["#fyp", "#новинка"],
            }],
        }


class InstagramGenerator(ContentGenerator):
    agent_name = "instagram-gen"
    description = "Создаёт карусели и Reels для Instagram"
    prompt_system = INSTAGRAM_PROMPT
    platform = "instagram"

    def _fallback(self, strategy: dict, kb: dict) -> dict:
        name = kb.get("product", {}).get("name", "Продукт")
        usp = kb.get("product", {}).get("usp", "")
        features = kb.get("product", {}).get("features", [])
        return {
            "carousels": [{
                "id": "ig1",
                "slides": [
                    {"image_desc": f"{name} на тёмном фоне", "text": f"Знакомьтесь — {name}"},
                    *[{"image_desc": f"Фича: {f}", "text": f} for f in features[:3]],
                    {"image_desc": "CTA", "text": "Переходи по ссылке в шапке профиля 🔗"},
                ],
                "caption": f"{name} — {usp}\n\n✨ {' | '.join(features[:3])}\n\nПредзаказ открыт! Ссылка в шапке профиля.",
                "hashtags": ["#новинка", "#технологии"],
            }],
            "reels": [{"id": "r1", "hook": f"Как {name} меняет правила игры", "duration_sec": 30, "description": "Демонстрация продукта"}],
        }


class ThreadsGenerator(ContentGenerator):
    agent_name = "threads-gen"
    description = "Создаёт текстовые треды для Threads"
    prompt_system = THREADS_PROMPT
    platform = "threads"

    def _fallback(self, strategy: dict, kb: dict) -> dict:
        name = kb.get("product", {}).get("name", "Продукт")
        usp = kb.get("product", {}).get("usp", "")
        return {
            "threads": [{
                "id": "th1",
                "title": f"Почему {name} — это то, о чём все говорят 🧵",
                "posts": [
                    f"1/5 Знаете, что общего у профессионального бариста и {name}?",
                    f"2/5 И тот и другой делают идеальный кофе. Но {name} не просит зарплату и не опаздывает на смену.",
                    f"3/5 {usp}",
                    f"4/5 Мы запустили предзаказ. Первые 50 покупателей получают эксклюзивный доступ к бета-режимам.",
                    "5/5 А какой кофе вы пьёте? Эспрессо или капучино? Голосуйте в опросе 👇",
                ],
            }],
        }
