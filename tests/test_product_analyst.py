"""
Tests for ProductAnalyst agent.
Uses mock LLM — no API keys needed.
"""
import json
import pytest
from product_launcher.agents import LLMClient, BaseAgent
from product_launcher.agents.product_analyst import ProductAnalyst


# ─── Mock LLM that returns structured product data ───

class MockLLM(LLMClient):
    """Returns realistic product analysis for testing."""

    def chat(self, messages, temperature=0.3, max_tokens=4096):
        return json.dumps({
            "product": {
                "name": "SmartClean Pro X1",
                "tagline": "Чистота без усилий",
                "description": "Робот-пылесос с LiDAR-навигацией и самоочисткой. Подходит для любых покрытий.",
                "usp": "Единственный робот-пылесос с УФ-стерилизацией и влажной уборкой за один проход",
                "features": [
                    "LiDAR-навигация с картографированием",
                    "Самоочистка контейнера",
                    "УФ-стерилизация",
                    "Влажная уборка",
                    "Управление через приложение",
                ],
                "specs": {
                    "battery": "5200 mAh",
                    "runtime": "180 min",
                    "suction": "4000 Pa",
                    "noise": "55 dB",
                },
                "price_range": "$299-399",
                "category": "Бытовая техника / Роботы-пылесосы",
            },
            "brand": {
                "tone_of_voice": {
                    "primary": "friendly",
                    "adjectives": ["тёплый", "технологичный", "заботливый"],
                    "donts": ["агрессивный", "скучный", "корпоративный"],
                },
                "colors": {
                    "primary": "#2D3436",
                    "secondary": "#0984E3",
                    "accent": "#00B894",
                },
                "target_audience": {
                    "demographics": "25-45 лет, городские жители, ценят технологии и комфорт",
                    "pain_points": [
                        "Нехватка времени на уборку",
                        "Аллергия на пыль",
                        "Сложные в настройке устройства",
                    ],
                    "platforms": ["Instagram", "TikTok", "YouTube"],
                },
            },
            "market": {
                "competitors": ["Roomba", "Xiaomi", "Roborock"],
                "differentiator": "УФ-стерилизация + влажная уборка за один проход",
                "geo_focus": "Россия, СНГ, Европа",
            },
        })


class EmptyMockLLM(LLMClient):
    """Returns minimal data."""

    def chat(self, messages, temperature=0.3, max_tokens=4096):
        return json.dumps({
            "product": {"name": "Test Product", "description": "Just a test", "usp": "", "features": [], "specs": {}},
            "brand": {
                "tone_of_voice": {"primary": "minimal", "adjectives": [], "donts": []},
                "colors": {"primary": "#000000", "secondary": "#FFFFFF", "accent": "#888888"},
                "target_audience": {"demographics": "", "pain_points": [], "platforms": []},
            },
            "market": {"competitors": [], "differentiator": "", "geo_focus": ""},
        })


class BrokenMockLLM(LLMClient):
    """Returns invalid JSON — tests error handling."""

    def chat(self, messages, temperature=0.3, max_tokens=4096):
        return "This is not JSON at all {broken"


# ─── Tests ───

class TestProductAnalystInit:
    """Agent initialization."""

    def test_creates_with_default_llm(self):
        agent = ProductAnalyst()
        assert agent.agent_name == "product-analyst"
        assert agent.llm is not None

    def test_creates_with_custom_llm(self):
        llm = MockLLM()
        agent = ProductAnalyst(llm=llm)
        assert agent.llm is llm


class TestProductAnalystRun:
    """Core agent functionality."""

    def test_extracts_full_product_info(self):
        """Full brochure text → complete ProductKB."""
        agent = ProductAnalyst(llm=MockLLM())
        result = agent.run({
            "raw_text": "Представляем SmartClean Pro X1 — революционного робота-пылесоса...",
            "event": "CES 2026",
            "location": "Las Vegas",
            "date": "2026-01-07",
        })

        assert result["product"]["name"] == "SmartClean Pro X1"
        assert "LiDAR" in result["product"]["features"][0]
        assert len(result["product"]["features"]) == 5
        assert result["product"]["specs"]["suction"] == "4000 Pa"
        assert result["brand"]["tone_of_voice"]["primary"] == "friendly"
        assert result["brand"]["colors"]["primary"] == "#2D3436"
        assert result["market"]["competitors"] == ["Roomba", "Xiaomi", "Roborock"]
        assert result["source"]["event"] == "CES 2026"

    def test_handles_empty_text(self):
        """Empty OCR text → graceful empty result."""
        agent = ProductAnalyst(llm=MockLLM())
        result = agent.run({"raw_text": ""})

        assert result["product"]["name"] == "—"
        assert "No OCR text" in result["product"]["description"]
        assert result["product"]["features"] == []

    def test_handles_minimal_input(self):
        """Minimal valid input → still works."""
        agent = ProductAnalyst(llm=EmptyMockLLM())
        result = agent.run({"raw_text": "Product X. $99."})

        assert result["product"]["name"] == "Test Product"
        assert result["brand"]["tone_of_voice"]["primary"] == "minimal"

    def test_handles_broken_llm_response(self):
        """Invalid JSON from LLM → graceful fallback."""
        agent = ProductAnalyst(llm=BrokenMockLLM())
        result = agent.run({"raw_text": "Some text"})

        # Should not crash — returns error result
        assert "product" in result
        assert result["product"]["name"] == "—"
        assert "Failed to parse" in result["product"]["description"]

    def test_preserves_source_metadata(self):
        """Source info (event, location, date, images) passed through."""
        agent = ProductAnalyst(llm=MockLLM())
        result = agent.run({
            "raw_text": "test",
            "event": "Expo 2026",
            "location": "Moscow",
            "date": "2026-06-15",
            "images": ["img1.jpg", "img2.jpg"],
        })

        assert result["source"]["event"] == "Expo 2026"
        assert result["source"]["location"] == "Moscow"
        assert result["source"]["date"] == "2026-06-15"
        assert result["source"]["images"] == ["img1.jpg", "img2.jpg"]
        assert result["source"]["raw_text"] == "test"

    def test_result_is_valid_productkb(self):
        """Result can be loaded into ProductKB model."""
        from product_launcher.kb import ProductKB

        agent = ProductAnalyst(llm=MockLLM())
        result = agent.run({
            "raw_text": "Brochure text...",
            "event": "Test",
            "location": "Test",
            "date": "2026-01-01",
        })

        # Should validate without errors
        kb = ProductKB.model_validate(result)
        assert kb.product.name == "SmartClean Pro X1"


class TestProductAnalystDefaults:
    """Default values for missing fields."""

    def test_missing_fields_get_defaults(self):
        """LLM returns partial data → defaults filled in."""
        agent = ProductAnalyst(llm=EmptyMockLLM())
        result = agent.run({"raw_text": "test"})

        assert isinstance(result["product"]["features"], list)
        assert isinstance(result["product"]["specs"], dict)
        assert isinstance(result["market"]["competitors"], list)
        assert result["brand"]["colors"]["primary"].startswith("#")


class TestProductAnalystEdgeCases:
    """Edge cases and error handling."""

    def test_very_long_text(self):
        """10K+ characters shouldn't crash."""
        agent = ProductAnalyst(llm=MockLLM())
        long_text = "SmartClean Pro X1. " * 500
        result = agent.run({"raw_text": long_text})

        assert result["product"]["name"] != "—"

    def test_non_ascii_text(self):
        """Cyrillic/Unicode text handled correctly."""
        agent = ProductAnalyst(llm=MockLLM())
        result = agent.run({
            "raw_text": "Умный очиститель воздуха «Бриз-3000» с технологией HEPA-фильтрации и ионизации.",
            "event": "Выставка",
            "location": "Москва",
            "date": "2026-05-01",
        })

        assert result["product"]["name"] != "—"
