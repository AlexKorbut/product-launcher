"""
Tests for OCR Extractor agent.
Extracts text and structure from product brochure images.
"""
import pytest
from pathlib import Path


# ─── RED: module doesn't exist yet ───

class TestOCRExtractorInit:
    """Extractor initialization."""

    def test_ocr_extractor_importable(self):
        """Module must be importable."""
        from product_launcher.ocr import OCRExtractor

    def test_ocr_extractor_creates_with_default_backend(self):
        """Default backend should be 'deepseek'."""
        from product_launcher.ocr import OCRExtractor

        extractor = OCRExtractor()
        assert extractor.backend == "deepseek"

    def test_ocr_extractor_accepts_custom_backend(self):
        """Should accept 'api' or 'local' backend."""
        from product_launcher.ocr import OCRExtractor

        local = OCRExtractor(backend="local")
        assert local.backend == "local"

        api = OCRExtractor(backend="api")
        assert api.backend == "api"


class TestOCRExtractSingleImage:
    """Single image extraction."""

    def test_extract_returns_string(self):
        """extract() must return a string."""
        from product_launcher.ocr import OCRExtractor

        extractor = OCRExtractor(backend="mock")
        result = extractor.extract(["test.jpg"])
        assert isinstance(result, str)

    def test_extract_handles_empty_list(self):
        """Empty image list returns empty string."""
        from product_launcher.ocr import OCRExtractor

        extractor = OCRExtractor(backend="mock")
        result = extractor.extract([])
        assert result == ""

    def test_extract_handles_nonexistent_file(self):
        """Non-existent file raises FileNotFoundError."""
        from product_launcher.ocr import OCRExtractor

        extractor = OCRExtractor(backend="mock")
        with pytest.raises(FileNotFoundError):
            extractor.extract(["/nonexistent/photo.jpg"])

    def test_extract_concatenates_multiple_images(self):
        """Multiple images produce concatenated output with separators."""
        from product_launcher.ocr import OCRExtractor

        extractor = OCRExtractor(backend="mock")
        result = extractor.extract(["img1.jpg", "img2.jpg"])
        # Should contain separator between images
        assert "---" in result or len(result.split("\n")) > 1


class TestOCRResultStructure:
    """OCR result structure."""

    def test_ocr_result_has_text_and_metadata(self):
        """OCRResult must have text and metadata fields."""
        from product_launcher.ocr import OCRResult

        result = OCRResult(
            text="Extracted text",
            language="ru",
            confidence=0.95,
            image_count=1,
        )

        assert result.text == "Extracted text"
        assert result.language == "ru"
        assert result.confidence == 0.95
        assert result.image_count == 1

    def test_ocr_result_confidence_is_float_0_to_1(self):
        """Confidence must be between 0 and 1."""
        from product_launcher.ocr import OCRResult
        from pydantic import ValidationError

        # Valid
        OCRResult(text="ok", confidence=0.5)

        # Invalid: -0.1
        with pytest.raises(ValidationError):
            OCRResult(text="ok", confidence=-0.1)

        # Invalid: 1.5
        with pytest.raises(ValidationError):
            OCRResult(text="ok", confidence=1.5)
