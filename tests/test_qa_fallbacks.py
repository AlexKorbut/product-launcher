"""
Tests for QA fallbacks — must not auto-pass without checking.
"""
import json
import pytest
from product_launcher.agents import LLMClient
from product_launcher.agents.qa_agents import QAText, QAVisual, QACross


class AlwaysFailLLM(LLMClient):
    """LLM that always fails to return JSON."""
    def chat(self, messages, temperature=0.3, max_tokens=4096):
        return "not json {{["


class TestQAFallbacksHaveHeuristics:
    """QA fallbacks must check actual input, not blindly pass."""

    def test_qa_text_fallback_checks_content(self):
        """Empty content → QA should warn."""
        qa = QAText(llm=AlwaysFailLLM())
        result = qa.run({"content": {}, "strategy": {}, "kb": {}})
        assert "score" in result
        assert "passed" in result
        # Empty content should NOT auto-pass cleanly
        assert result["score"] < 80 or len(result.get("issues", [])) > 0 or not result["passed"]

    def test_qa_text_fallback_detects_missing_cta(self):
        """Content without CTA → should flag it."""
        qa = QAText(llm=AlwaysFailLLM())
        result = qa.run({
            "content": {"sections": [{"id": "hero", "headline": "Test", "cta": ""}]},
            "strategy": {},
            "kb": {},
        })
        # Missing CTA should be caught
        issues = result.get("issues", [])
        assert len(issues) > 0 or not result["passed"]

    def test_qa_visual_fallback_checks_assets(self):
        """Empty assets → QA should warn."""
        qa = QAVisual(llm=AlwaysFailLLM())
        result = qa.run({"assets": [], "strategy": {}, "kb": {}})
        # No assets should not auto-pass
        assert result["score"] < 80 or not result["passed"]

    def test_qa_cross_fallback_checks_platforms(self):
        """No platform content → cross-QA should fail."""
        qa = QACross(llm=AlwaysFailLLM())
        result = qa.run({"strategy": {}, "kb": {}})
        # No platforms provided should be a critical gap
        assert not result["passed"] or len(result.get("platform_gaps", [])) > 0

    def test_qa_cross_fallback_passes_with_all_platforms(self):
        """All platforms present → cross-QA should pass."""
        qa = QACross(llm=AlwaysFailLLM())
        result = qa.run({
            "website": {"sections": [{"id": "hero"}]},
            "tiktok": {"scripts": [{"id": "t1"}]},
            "instagram": {"carousels": [{"id": "ig1"}]},
            "threads": {"threads": [{"id": "th1"}]},
            "strategy": {},
            "kb": {},
        })
        assert result["passed"]
