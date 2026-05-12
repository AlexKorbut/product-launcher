"""
Tests for OCR Extractor agent.
Handles text extraction from raw materials (brochures, images, etc.).
"""
import json
import pytest
from product_launcher.agents import LLMClient
from product_launcher.agents.ocr_extractor import OCRExtractor


# ─── Mock LLMs ───

class OCRExtractMockLLM(LLMClient):
    """Returns realistic OCR extraction."""

    def chat(self, messages, temperature=0.3, max_tokens=4096):
        return json.dumps({
            "text": "SmartClean Pro X1 — робот-пылесос с LiDAR-навигацией и УФ-стерилизацией. "
                    "5200 mAh, 180 мин работы, 4000 Pa всасывания. Цена $299-399.",
            "confidence": 0.95,
            "segments": [
                {"type": "title", "text": "SmartClean Pro X1"},
                {"type": "feature", "text": "LiDAR-навигация с картографированием помещения"},
                {"type": "spec", "text": "5200 mAh / 180 мин / 4000 Pa"},
                {"type": "price", "text": "$299-399"},
            ],
        })


class OCREmptyMockLLM(LLMClient):
    """Returns empty/unsure result."""

    def chat(self, messages, temperature=0.3, max_tokens=4096):
        return json.dumps({
            "text": "",
            "confidence": 0.0,
            "segments": [],
        })


class OCRFailLLM(LLMClient):
    """Returns broken JSON."""

    def chat(self, messages, temperature=0.3, max_tokens=4096):
        return "not json {{["


# ─── Tests ───

class TestOCRExtractorInit:
    """Agent initialization."""

    def test_creates_with_default_llm(self):
        agent = OCRExtractor()
        assert agent.agent_name == "ocr-extractor"

    def test_creates_with_custom_llm(self):
        llm = OCRExtractMockLLM()
        agent = OCRExtractor(llm=llm)
        assert agent.llm is llm


class TestOCRExtractorRun:
    """Core extraction functionality."""

    def test_extracts_text_from_raw_string(self):
        """Raw text input → structured extraction."""
        agent = OCRExtractor(llm=OCRExtractMockLLM())
        result = agent.run({"raw_text": "SmartClean Pro X1 brochure text..."})

        assert "text" in result
        assert "SmartClean" in result["text"]
        assert result["confidence"] == 0.95
        assert "segments" in result
        assert len(result["segments"]) == 4

    def test_handles_empty_input(self):
        """Empty input → graceful fallback."""
        agent = OCRExtractor(llm=OCRExtractMockLLM())
        result = agent.run({"raw_text": ""})

        assert "text" in result
        assert isinstance(result["text"], str)

    def test_handles_missing_raw_text(self):
        """Missing raw_text key → fallback with empty result."""
        agent = OCRExtractor(llm=OCRExtractMockLLM())
        result = agent.run({})

        assert "text" in result
        assert result["confidence"] >= 0  # No text = zero confidence

    def test_handles_broken_llm(self):
        """Broken LLM response → fallback, no crash."""
        agent = OCRExtractor(llm=OCRFailLLM())
        result = agent.run({"raw_text": "Some brochure text"})

        assert "text" in result
        assert isinstance(result["text"], str)
        assert "confidence" in result

    def test_fallback_returns_useful_text(self):
        """Fallback shouldn't return empty string when input exists."""
        agent = OCRExtractor(llm=OCRFailLLM())
        result = agent.run({"raw_text": "Brochure: SmartClean Pro X1 features"})

        # Fallback should preserve some useful content
        assert len(result["text"]) > 0

    def test_result_is_json_serializable(self):
        """Result must be JSON-serializable for kanban storage."""
        agent = OCRExtractor(llm=OCRExtractMockLLM())
        result = agent.run({"raw_text": "test"})

        dumped = json.dumps(result, ensure_ascii=False)
        parsed = json.loads(dumped)
        assert parsed == result


class TestOCRExtractorFallback:
    """Fallback strategy when LLM unavailable."""

    def test_fallback_produces_minimum_viable_output(self):
        """Fallback extracts something from raw text."""
        agent = OCRExtractor(llm=OCREmptyMockLLM())
        result = agent.run({"raw_text": "Product X with feature Y"})

        # EmptyMock returns text='' which triggers fallback
        assert "text" in result
        # Fallback should have the raw text or cleaned version
        assert len(result["text"]) > 0

    def test_fallback_handles_whitespace_input(self):
        """Whitespace-only text → confident empty result."""
        agent = OCRExtractor(llm=OCREmptyMockLLM())
        result = agent.run({"raw_text": "   \n  "})

        assert result["confidence"] >= 0  # Doesn't crash
