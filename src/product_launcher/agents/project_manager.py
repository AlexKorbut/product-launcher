"""
Project Manager Agent — decomposes brief, assigns roles, coordinates specialists.
Acts as the team lead in an IT-company structure.
"""
import json
from . import BaseAgent, LLMClient


PM_PROMPT = """Ты — Project Manager в IT-компании. Твоя задача: получить brief от клиента и распределить работу между специалистами.

Команда специалистов, доступных тебе:
1. ocr_specialist (ocr-extractor) — извлекает текст из фото 
2. product_analyst (product-analyst) — анализирует продукт, создаёт ProductKB
3. content_strategist (content-strategist) — разрабатывает контент-стратегию
4. web_designer (website-gen) — создаёт лендинг (HTML/CSS, Claude Design подход)
5. smm_tiktok (tiktok-gen) — пишет сценарии для TikTok
6. smm_instagram (instagram-gen) — создаёт контент для Instagram
7. smm_threads (threads-gen) — пишет треды для Threads
8. art_director (asset-gen) — описывает визуальные ассеты и brand kit
9. qa_lead (qa-cross) — финальная проверка всех материалов

Верни ТОЛЬКО валидный JSON:

{
  "project_name": "Название проекта (5-10 слов)",
  "brief_summary": "Краткое изложение задачи (2-3 предложения)",
  "team": [
    {
      "role": "название роли из списка выше",
      "agent": "техническое имя из списка",
      "task": "Конкретная задача для этого специалиста (1 предложение)",
      "priority": число от 1 до 9,
      "depends_on": ["agent_name"]
    }
  ],
  "acceptance_criteria": [
    "Критерий приёмки 1",
    "Критерий приёмки 2"
  ]
}

Правила:
- ВСЕГДА используй только специалистов из списка выше
- priority: 1 = первая задача, 9 = последняя
- depends_on: список agent_name, от которых зависит эта задача
- ocr_specialist всегда priority 1, depends_on = []
- product_analyst зависит от ocr_specialist
- content_strategist зависит от product_analyst
- web_designer, smm_*, art_director — priority 4, зависит от content_strategist
- qa_lead зависит от всех генераторов, priority 5
- acceptance_criteria: 2-4 конкретных проверяемых критерия
- На русском языке
"""


class ProjectManager(BaseAgent):
    """Decomposes client brief into task plan for specialists."""

    agent_name = "project-manager"
    description = "PM: распределяет задачи между специалистами, координирует работу"

    def run(self, input_data: dict) -> dict:
        """
        Args:
            input_data: {"brief": {...}, "images": [...]}

        Returns:
            {"project_name": ..., "team": [...], "acceptance_criteria": [...]}
        """
        brief = input_data.get("brief", {})
        images = input_data.get("images", [])

        self.log(f"Планирую проект: {brief.get('product_hint', 'Новый продукт')}")

        prompt_parts = [
            "## Brief от клиента",
        ]
        if brief.get("product_hint"):
            prompt_parts.append(f"Продукт: {brief['product_hint']}")
        if brief.get("requirements"):
            prompt_parts.append(f"Требования: {brief['requirements']}")
        if images:
            prompt_parts.append(f"Фото брошюры: {len(images)} шт.")
        if brief.get("notes"):
            prompt_parts.append(f"Заметки: {brief['notes']}")

        user_prompt = "\n".join(prompt_parts)

        messages = [
            {"role": "system", "content": PM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        response = self.llm.chat(messages, temperature=0.3, max_tokens=4096)
        result = self._parse(response)

        if not result:
            self.log("⚠️ Fallback-план")
            result = self._fallback_plan(brief)

        self.log(f"✓ План: {result.get('project_name', '—')}, {len(result.get('team', []))} специалистов")
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

    def _fallback_plan(self, brief: dict) -> dict:
        """Standard plan when LLM is unavailable."""
        product_hint = brief.get("product_hint", "Новый продукт")

        return {
            "project_name": f"Маркетинговые материалы: {product_hint}",
            "brief_summary": f"Создать полный комплект маркетинговых материалов для {product_hint}: лендинг + контент для Instagram, TikTok, Threads.",
            "team": [
                {"role": "ocr_specialist",    "agent": "ocr-extractor",     "task": "Извлечь текст из фото брошюры",        "priority": 1, "depends_on": []},
                {"role": "product_analyst",   "agent": "product-analyst",  "task": "Проанализировать продукт, ProductKB",  "priority": 2, "depends_on": ["ocr-extractor"]},
                {"role": "content_strategist","agent": "content-strategist","task": "Контент-стратегия для всех платформ",   "priority": 3, "depends_on": ["product-analyst"]},
                {"role": "web_designer",      "agent": "website-gen",      "task": "Лендинг (HTML/CSS, Claude Design)",    "priority": 4, "depends_on": ["content-strategist"]},
                {"role": "smm_tiktok",        "agent": "tiktok-gen",       "task": "Сценарии для TikTok",                  "priority": 4, "depends_on": ["content-strategist"]},
                {"role": "smm_instagram",     "agent": "instagram-gen",    "task": "Карусели и Reels для Instagram",       "priority": 4, "depends_on": ["content-strategist"]},
                {"role": "smm_threads",       "agent": "threads-gen",      "task": "Текстовые треды для Threads",          "priority": 4, "depends_on": ["content-strategist"]},
                {"role": "art_director",      "agent": "asset-gen",        "task": "Визуальные ассеты и brand kit",        "priority": 4, "depends_on": ["content-strategist"]},
                {"role": "qa_lead",           "agent": "qa-cross",         "task": "Финальная проверка всех материалов",    "priority": 5, "depends_on": ["website-gen", "tiktok-gen", "instagram-gen", "threads-gen", "asset-gen"]},
            ],
            "acceptance_criteria": [
                "Лендинг — самодостаточный HTML, открывается в браузере",
                "Контент на всех платформах (Instagram, TikTok, Threads)",
                "Тон соответствует brand guidelines",
                "Все материалы прошли QA-проверку",
            ],
        }
