"""
Tests for ProjectManager agent — decomposes brief, assigns roles, coordinates team.
"""
import json
import pytest
from product_launcher.agents import LLMClient
from product_launcher.agents.project_manager import ProjectManager


class PMMockLLM(LLMClient):
    """Returns realistic task breakdown."""

    def chat(self, messages, temperature=0.3, max_tokens=4096):
        return json.dumps({
            "project_name": "Запуск SmartClean Pro X1",
            "brief_summary": "Робот-пылесос с УФ-стерилизацией. Задача: создать все маркетинговые материалы.",
            "team": [
                {
                    "role": "ocr_specialist",
                    "agent": "ocr-extractor",
                    "task": "Извлечь текст из фото брошюры",
                    "priority": 1,
                    "depends_on": [],
                },
                {
                    "role": "product_analyst",
                    "agent": "product-analyst",
                    "task": "Проанализировать продукт, создать ProductKB",
                    "priority": 2,
                    "depends_on": ["ocr-extractor"],
                },
                {
                    "role": "content_strategist",
                    "agent": "content-strategist",
                    "task": "Разработать контент-стратегию для всех платформ",
                    "priority": 3,
                    "depends_on": ["product-analyst"],
                },
                {
                    "role": "web_designer",
                    "agent": "website-gen",
                    "task": "Создать лендинг (Claude Design подход)",
                    "priority": 4,
                    "depends_on": ["content-strategist"],
                },
                {
                    "role": "smm_tiktok",
                    "agent": "tiktok-gen",
                    "task": "Сценарии для TikTok",
                    "priority": 4,
                    "depends_on": ["content-strategist"],
                },
                {
                    "role": "smm_instagram",
                    "agent": "instagram-gen",
                    "task": "Контент для Instagram",
                    "priority": 4,
                    "depends_on": ["content-strategist"],
                },
                {
                    "role": "smm_threads",
                    "agent": "threads-gen",
                    "task": "Треды для Threads",
                    "priority": 4,
                    "depends_on": ["content-strategist"],
                },
                {
                    "role": "art_director",
                    "agent": "asset-gen",
                    "task": "Визуальные ассеты и brand kit",
                    "priority": 4,
                    "depends_on": ["content-strategist"],
                },
                {
                    "role": "qa_text",
                    "agent": "qa-text",
                    "task": "Проверить качество текстов",
                    "priority": 5,
                    "depends_on": ["website-gen"],
                },
                {
                    "role": "qa_visual",
                    "agent": "qa-visual",
                    "task": "Проверить качество ассетов",
                    "priority": 5,
                    "depends_on": ["asset-gen"],
                },
                {
                    "role": "qa_lead",
                    "agent": "qa-cross",
                    "task": "Финальная проверка всех материалов",
                    "priority": 6,
                    "depends_on": ["website-gen", "tiktok-gen", "instagram-gen", "threads-gen", "asset-gen"],
                },
            ],
            "acceptance_criteria": [
                "Лендинг открывается в браузере без ошибок",
                "Текст соответствует tone of voice бренда",
                "Все платформы покрыты контентом",
            ],
        })


class PMFailLLM(LLMClient):
    def chat(self, messages, temperature=0.3, max_tokens=4096):
        return "not json {"


SAMPLE_BRIEF = {
    "product_hint": "AI-powered robot vacuum with UV sterilization",
    "images": ["brochure_1.jpg", "brochure_2.jpg"],
    "requirements": "Landing page + social media content for Instagram, TikTok, Threads",
}


class TestProjectManager:
    """PM decomposes brief and creates task plan."""

    def test_creates_task_breakdown(self):
        pm = ProjectManager(llm=PMMockLLM())
        result = pm.run({"brief": SAMPLE_BRIEF})

        assert "project_name" in result
        assert "team" in result
        assert len(result["team"]) >= 5
        assert result["team"][0]["role"] == "ocr_specialist"

    def test_tasks_have_dependencies(self):
        pm = ProjectManager(llm=PMMockLLM())
        result = pm.run({"brief": SAMPLE_BRIEF})

        for member in result["team"]:
            assert "depends_on" in member
            assert "priority" in member
            assert "agent" in member

    def test_sequential_priority_order(self):
        """OCR first, analyst second, strategy third — dependencies respected."""
        pm = ProjectManager(llm=PMMockLLM())
        result = pm.run({"brief": SAMPLE_BRIEF})

        priorities = [m["priority"] for m in result["team"]]
        assert priorities == sorted(priorities), "Tasks should be ordered by priority"

    def test_handles_minimal_brief(self):
        """PM works with minimal brief."""
        pm = ProjectManager(llm=PMMockLLM())
        result = pm.run({"brief": {"product_hint": "Coffee machine"}})
        assert len(result["team"]) > 0

    def test_fallback_plan(self):
        """Broken LLM → PM produces fallback plan."""
        pm = ProjectManager(llm=PMFailLLM())
        result = pm.run({"brief": SAMPLE_BRIEF})
        assert len(result["team"]) >= 3
        assert result["team"][0]["agent"] == "ocr-extractor"

    def test_includes_acceptance_criteria(self):
        pm = ProjectManager(llm=PMMockLLM())
        result = pm.run({"brief": SAMPLE_BRIEF})
        assert "acceptance_criteria" in result
        assert len(result["acceptance_criteria"]) > 0

    def test_json_serializable(self):
        pm = ProjectManager(llm=PMMockLLM())
        result = pm.run({"brief": SAMPLE_BRIEF})
        json.dumps(result, ensure_ascii=False)  # Should not crash
