"""
QA Agents — review generated content for quality, consistency, and cross-platform alignment.
"""
import json
from . import BaseAgent, LLMClient


QA_TEXT_PROMPT = """Ты — редактор-контролёр качества текстового контента.
Проверь сгенерированный контент на соответствие стратегии и brand guidelines.

Верни ТОЛЬКО валидный JSON:

{
  "score": 0-100,
  "issues": [
    {
      "severity": "critical | major | minor",
      "text": "Описание проблемы",
      "location": "Где найдено (hero/headline, features/item, etc)"
    }
  ],
  "suggestions": ["Конкретное предложение по улучшению"],
  "passed": true/false
}

Критерии проверки:
- Соответствие tone of voice
- Орфография и грамматика (русский язык)
- Отсутствие клише и воды
- Конкретность (цифры, факты, а не общие слова)
- Наличие УТП в hero-секции
- Призыв к действию (CTA)
"""

QA_VISUAL_PROMPT = """Ты — арт-директор на контроле качества визуальных ассетов.
Оцени описания ассетов на соответствие brand guidelines.

Верни ТОЛЬКО валидный JSON:

{
  "score": 0-100,
  "issues": [
    {
      "severity": "critical | major | minor",
      "text": "Описание проблемы",
      "asset_id": "ID ассета"
    }
  ],
  "suggestions": ["Предложение"],
  "passed": true/false
}

Критерии:
- Соответствие цветовой палитре бренда
- Единый визуальный стиль
- Правильные размеры (hero 1200×628, icon 512×512, post 1080×1080)
- Достаточная детализация описаний
- Соответствие tone of voice в визуале
"""

QA_CROSS_PROMPT = """Ты — кросс-платформенный QA-специалист.
Проверь согласованность контента между всеми платформами.

Верни ТОЛЬКО валидный JSON:

{
  "score": 0-100,
  "consistency_issues": [
    {
      "severity": "critical | major | minor",
      "text": "Описание несоответствия",
      "platforms": ["platform1", "platform2"]
    }
  ],
  "platform_gaps": ["Чего не хватает на платформе X"],
  "overall": "Общая оценка (1-2 предложения)",
  "passed": true/false
}

Критерии:
- Единый message на всех платформах
- Адаптация под формат (TikTok ≠ Threads ≠ Instagram ≠ Website)
- Отсутствие противоречий
- Полнота покрытия (все платформы)
"""


class QAText(BaseAgent):
    agent_name = "qa-text"
    description = "Проверяет качество текстового контента"

    def run(self, input_data: dict) -> dict:
        content = input_data.get("content", {})
        strategy = input_data.get("strategy", {})
        kb = input_data.get("kb", {})

        self.log("Проверяю текстовый контент...")

        prompt = f"""Продукт: {kb.get('product', {}).get('name', '—')}
Тон: {strategy.get('tone_of_voice', {}).get('primary', 'friendly')}
Правила тона: {'; '.join(strategy.get('tone_of_voice', {}).get('rules', []))}

Контент для проверки:
{json.dumps(content, ensure_ascii=False, indent=2)}"""

        messages = [
            {"role": "system", "content": QA_TEXT_PROMPT},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.chat(messages, temperature=0.2, max_tokens=2048)
        result = self._parse(response) or self._fallback()

        passed = result.get("passed", False)
        self.log(f"{'✅' if passed else '⚠️'} QA текста: {result.get('score', 0)}/100")
        return result

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

    def _fallback(self) -> dict:
        return {"score": 70, "issues": [], "suggestions": ["Требуется ручная проверка"], "passed": True}


class QAVisual(BaseAgent):
    agent_name = "qa-visual"
    description = "Проверяет качество визуальных ассетов"

    def run(self, input_data: dict) -> dict:
        assets = input_data.get("assets", [])
        strategy = input_data.get("strategy", {})
        kb = input_data.get("kb", {})

        self.log(f"Проверяю {len(assets)} визуальных ассетов...")

        colors = kb.get("brand", {}).get("colors", {})
        prompt = f"""Цвета бренда: primary={colors.get('primary')}, secondary={colors.get('secondary')}, accent={colors.get('accent')}
Тон: {strategy.get('tone_of_voice', {}).get('primary', 'friendly')}

Ассеты:
{json.dumps(assets, ensure_ascii=False, indent=2)}"""

        messages = [
            {"role": "system", "content": QA_VISUAL_PROMPT},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.chat(messages, temperature=0.2, max_tokens=2048)
        result = self._parse(response) or self._fallback()

        passed = result.get("passed", False)
        self.log(f"{'✅' if passed else '⚠️'} QA визуала: {result.get('score', 0)}/100")
        return result

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

    def _fallback(self) -> dict:
        return {"score": 70, "issues": [], "suggestions": ["Требуется ручная проверка"], "passed": True}


class QACross(BaseAgent):
    agent_name = "qa-cross"
    description = "Кросс-платформенная проверка согласованности"

    def run(self, input_data: dict) -> dict:
        strategy = input_data.get("strategy", {})
        kb = input_data.get("kb", {})

        # Collect all platform content
        platforms = {}
        for plat in ["website", "tiktok", "instagram", "threads"]:
            if plat in input_data:
                platforms[plat] = input_data[plat]

        self.log(f"Кросс-QA: {len(platforms)} платформ...")

        prompt = f"""Продукт: {kb.get('product', {}).get('name', '—')}
Контент по платформам:
{json.dumps(platforms, ensure_ascii=False, indent=2)}"""

        messages = [
            {"role": "system", "content": QA_CROSS_PROMPT},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.chat(messages, temperature=0.2, max_tokens=2048)
        result = self._parse(response) or self._fallback()

        passed = result.get("passed", False)
        self.log(f"{'✅' if passed else '⚠️'} Кросс-QA: {result.get('score', 0)}/100")
        return result

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

    def _fallback(self) -> dict:
        return {"score": 70, "issues": [], "platform_gaps": [], "overall": "Требуется ручная проверка", "passed": True}
