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
        result = self._parse(response) or self._fallback_with_heuristics(content, strategy, kb)

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

    def _fallback_with_heuristics(self, content: dict, strategy: dict, kb: dict) -> dict:
        """Heuristic checks when LLM unavailable. Checks website content structure."""
        issues = []
        suggestions = ["Требуется ручная проверка (LLM недоступен)"]
        product_name = kb.get("product", {}).get("name", "Продукт")

        # Check content has sections
        sections = content.get("sections", [])
        if not sections:
            issues.append({"severity": "critical", "text": "Контент пуст — нет секций", "location": "all"})
            return {"score": 0, "issues": issues, "suggestions": suggestions, "passed": False}

        # Check for CTA
        has_cta = any(
            s.get("id") == "cta_final" or (s.get("cta") and s["cta"].strip())
            for s in sections
        )
        if not has_cta:
            issues.append({"severity": "major", "text": "Нет призыва к действию (CTA)", "location": "cta_final"})

        # Check hero has headline
        hero = next((s for s in sections if s.get("id") == "hero"), None)
        if hero:
            if not hero.get("headline"):
                issues.append({"severity": "major", "text": "Hero-секция без заголовка", "location": "hero/headline"})
            # Check product name in hero
            if product_name != "Продукт" and hero.get("headline") and product_name.lower() not in hero.get("headline", "").lower():
                issues.append({"severity": "minor", "text": "Hero не содержит название продукта", "location": "hero/headline"})
        else:
            issues.append({"severity": "critical", "text": "Отсутствует hero-секция", "location": "hero"})

        # Check features section
        features = next((s for s in sections if s.get("id") == "features"), None)
        if features and not features.get("items"):
            issues.append({"severity": "minor", "text": "Секция features без фич", "location": "features/items"})

        score = max(0, 100 - len(issues) * 15)
        passed = not any(i["severity"] == "critical" for i in issues)

        if not issues:
            suggestions.append("Структурные проверки пройдены")

        return {"score": score, "issues": issues, "suggestions": suggestions, "passed": passed}


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
        result = self._parse(response) or self._fallback_with_heuristics(assets, strategy, kb)

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

    def _fallback_with_heuristics(self, assets: list, strategy: dict, kb: dict) -> dict:
        """Heuristic checks for visual assets when LLM unavailable."""
        issues = []
        suggestions = ["Требуется ручная проверка (LLM недоступен)"]
        brand_colors = kb.get("brand", {}).get("colors", {})

        # Check we have assets at all
        if not assets:
            issues.append({"severity": "critical", "text": "Нет ассетов для проверки", "asset_id": "none"})
            return {"score": 0, "issues": issues, "suggestions": suggestions, "passed": False}

        # Check required asset types
        asset_types = {a.get("type") for a in assets if a.get("type")}
        required_types = {"hero_image", "feature_icon", "social_post"}
        missing_types = required_types - asset_types
        if missing_types:
            issues.append({
                "severity": "major",
                "text": f"Не хватает типов ассетов: {', '.join(missing_types)}",
                "asset_id": "all",
            })

        # Check dimensions
        for a in assets:
            dims = a.get("dimensions", "")
            if dims and dims not in ["1200x628", "512x512", "1080x1080", "1200×628", "512×512", "1080×1080"]:
                issues.append({
                    "severity": "minor",
                    "text": f"Нестандартный размер {dims} для {a.get('id', '?')}",
                    "asset_id": a.get("id", "?"),
                })

        # Check each asset has a description
        for a in assets:
            if not a.get("description") or len(a.get("description", "")) < 20:
                issues.append({
                    "severity": "major",
                    "text": f"Слишком короткое описание для {a.get('id', '?')}",
                    "asset_id": a.get("id", "?"),
                })

        score = max(0, 100 - len(issues) * 12)
        passed = not any(i["severity"] == "critical" for i in issues)

        if not issues:
            suggestions.append("Структурные проверки ассетов пройдены")

        return {"score": score, "issues": issues, "suggestions": suggestions, "passed": passed}


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
        result = self._parse(response) or self._fallback_with_heuristics(platforms, strategy, kb)

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

    def _fallback_with_heuristics(self, platforms: dict, strategy: dict, kb: dict) -> dict:
        """Heuristic cross-platform coverage check when LLM unavailable."""
        issues = []
        platform_gaps = []
        suggestions = ["Требуется ручная проверка (LLM недоступен)"]

        required = ["website", "tiktok", "instagram", "threads"]
        present = list(platforms.keys())

        # Check platform coverage
        missing = [p for p in required if p not in present]
        if missing:
            for m in missing:
                platform_gaps.append(f"Контент для {m} отсутствует")
                issues.append({
                    "severity": "critical",
                    "text": f"Платформа {m} не покрыта контентом",
                    "platforms": [m],
                })
            return {
                "score": 0,
                "consistency_issues": issues,
                "platform_gaps": platform_gaps,
                "overall": f"Критические пробелы: {len(missing)} платформ не покрыты.",
                "passed": False,
            }

        # All platforms present — structural check
        checks = {
            "website": lambda c: c.get("sections"),
            "tiktok": lambda c: c.get("scripts"),
            "instagram": lambda c: c.get("carousels"),
            "threads": lambda c: c.get("threads"),
        }

        for plat in required:
            checker = checks[plat]
            content = platforms.get(plat, {})
            if not checker(content):
                platform_gaps.append(f"{plat}: контент пуст")
                issues.append({
                    "severity": "major",
                    "text": f"Контент для {plat} пуст",
                    "platforms": [plat],
                })

        score = max(0, 100 - len(issues) * 20)
        passed = not any(i["severity"] == "critical" for i in issues)

        if not issues:
            overall = f"Все {len(present)} платформ покрыты контентом."
            suggestions.append("Кросс-платформенная проверка структуры пройдена")
        else:
            overall = f"Найдено {len(issues)} проблем кросс-платформенной согласованности."

        return {
            "score": score,
            "consistency_issues": issues,
            "platform_gaps": platform_gaps,
            "overall": overall,
            "passed": passed,
        }
