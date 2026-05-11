"""
Tests for AssetGen and QA agents.
"""
import json
import pytest
from product_launcher.agents import LLMClient
from product_launcher.agents.asset_gen import AssetGenerator
from product_launcher.agents.qa_agents import QAText, QAVisual, QACross


# ─── Mock LLMs ───

class AssetMockLLM(LLMClient):
    def chat(self, messages, temperature=0.3, max_tokens=4096):
        return json.dumps({
            "assets": [
                {
                    "id": "a1",
                    "type": "hero_image",
                    "description": "Продукт на тёмном градиентном фоне, пар от кофе, тёплый свет",
                    "style": "Премиум, минимализм",
                    "dimensions": "1200x628",
                    "colors": ["#2D3436", "#0984E3", "#00B894"],
                },
                {
                    "id": "a2",
                    "type": "feature_icon",
                    "description": "Иконка LiDAR-сканера в стиле скевоморфизм",
                    "style": "Техно, глянцевый",
                    "dimensions": "512x512",
                    "colors": ["#0984E3"],
                },
            ],
            "brand_kit": {
                "logo_variants": ["Основной", "Монохромный"],
                "typography": "Inter / SF Pro Display",
            },
        })


class QATextMockLLM(LLMClient):
    def chat(self, messages, temperature=0.3, max_tokens=4096):
        return json.dumps({
            "score": 85,
            "issues": [
                {"severity": "minor", "text": "Заменить «инновационный» на конкретную фичу", "location": "hero/headline"},
            ],
            "suggestions": ["Добавить social proof в hero-секцию"],
            "passed": True,
        })


class QAVisualMockLLM(LLMClient):
    def chat(self, messages, temperature=0.3, max_tokens=4096):
        return json.dumps({
            "score": 90,
            "issues": [],
            "suggestions": ["Увеличить контраст на hero_image"],
            "passed": True,
        })


class QACrossMockLLM(LLMClient):
    def chat(self, messages, temperature=0.3, max_tokens=4096):
        return json.dumps({
            "score": 88,
            "consistency_issues": [],
            "platform_gaps": [],
            "overall": "Контент согласован между платформами",
            "passed": True,
        })


class FailLLM(LLMClient):
    def chat(self, messages, temperature=0.3, max_tokens=4096):
        return "not json {"


SAMPLE_KB = {
    "product": {"name": "Coffee Machine", "usp": "AI-powered", "features": ["f1"], "specs": {}},
    "brand": {
        "tone_of_voice": {"primary": "friendly"},
        "colors": {"primary": "#111", "secondary": "#222", "accent": "#333"},
        "target_audience": {"demographics": "25-45", "platforms": ["Instagram"]},
    },
}
SAMPLE_STRATEGY = {"content_pillars": [{"name": "Tech", "angle": "Science"}], "tone_of_voice": {"primary": "friendly"}}
SAMPLE_CONTENT = {"sections": [{"id": "hero", "headline": "Test"}]}


# ─── AssetGen Tests ───

class TestAssetGenerator:
    def test_generates_assets(self):
        gen = AssetGenerator(llm=AssetMockLLM())
        result = gen.run({"strategy": SAMPLE_STRATEGY, "kb": SAMPLE_KB})
        assert len(result["assets"]) >= 2
        assert result["assets"][0]["type"] == "hero_image"

    def test_fallback(self):
        gen = AssetGenerator(llm=FailLLM())
        result = gen.run({"strategy": SAMPLE_STRATEGY, "kb": SAMPLE_KB})
        assert len(result["assets"]) > 0


# ─── QA Tests ───

class TestQAText:
    def test_reviews_text(self):
        qa = QAText(llm=QATextMockLLM())
        result = qa.run({"content": SAMPLE_CONTENT, "strategy": SAMPLE_STRATEGY, "kb": SAMPLE_KB})
        assert "score" in result
        assert result["passed"] is True

    def test_fallback(self):
        qa = QAText(llm=FailLLM())
        result = qa.run({"content": SAMPLE_CONTENT, "strategy": SAMPLE_STRATEGY, "kb": SAMPLE_KB})
        assert "score" in result


class TestQAVisual:
    def test_reviews_visual(self):
        qa = QAVisual(llm=QAVisualMockLLM())
        result = qa.run({"assets": [{"id": "a1", "type": "hero"}], "strategy": SAMPLE_STRATEGY, "kb": SAMPLE_KB})
        assert "score" in result

    def test_fallback(self):
        qa = QAVisual(llm=FailLLM())
        result = qa.run({"assets": [], "strategy": SAMPLE_STRATEGY, "kb": SAMPLE_KB})
        assert "score" in result


class TestQACross:
    def test_cross_platform_review(self):
        qa = QACross(llm=QACrossMockLLM())
        result = qa.run({
            "website": SAMPLE_CONTENT,
            "tiktok": {"scripts": [{"id": "t1"}]},
            "instagram": {"carousels": [{"id": "ig1"}]},
            "threads": {"threads": [{"id": "th1"}]},
            "strategy": SAMPLE_STRATEGY,
            "kb": SAMPLE_KB,
        })
        assert "score" in result
        assert result["passed"] is True

    def test_fallback(self):
        qa = QACross(llm=FailLLM())
        result = qa.run({"strategy": SAMPLE_STRATEGY, "kb": SAMPLE_KB})
        assert "score" in result


class TestAllQASerializable:
    @pytest.mark.parametrize("qa_class,llm_class,input_data", [
        (QAText, QATextMockLLM, {"content": SAMPLE_CONTENT, "strategy": SAMPLE_STRATEGY, "kb": SAMPLE_KB}),
        (QAVisual, QAVisualMockLLM, {"assets": [], "strategy": SAMPLE_STRATEGY, "kb": SAMPLE_KB}),
        (QACross, QACrossMockLLM, {"strategy": SAMPLE_STRATEGY, "kb": SAMPLE_KB}),
    ])
    def test_json_serializable(self, qa_class, llm_class, input_data):
        agent = qa_class(llm=llm_class())
        result = agent.run(input_data)
        dumped = json.dumps(result, ensure_ascii=False)
        assert json.loads(dumped) == result
