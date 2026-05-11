"""
OCR Extractor — extracts text from product brochure images.
Supports multiple backends: deepseek (default), local (DeepSeek-OCR 2), api, mock.
"""
from pydantic import BaseModel, Field
from pathlib import Path
from typing import Optional


class OCRResult(BaseModel):
    """Structured OCR result."""
    text: str = ""
    language: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    image_count: int = Field(default=0, ge=0)


class OCRExtractor:
    """Extract text from product brochure images."""

    VALID_BACKENDS = {"deepseek", "local", "api", "mock"}

    def __init__(self, backend: str = "deepseek"):
        if backend not in self.VALID_BACKENDS:
            raise ValueError(f"Unknown backend: {backend}. Valid: {self.VALID_BACKENDS}")
        self.backend = backend

    def extract(self, image_paths: list[str]) -> str:
        """Extract text from images. Returns concatenated text."""
        if not image_paths:
            return ""

        # Validate all files exist (all backends)
        for path in image_paths:
            if not Path(path).exists():
                raise FileNotFoundError(f"Image not found: {path}")

        if self.backend == "mock":
            return self._mock_extract(image_paths)

        # Real backends — placeholder for now
        return ""

    def _mock_extract(self, paths: list[str]) -> str:
        """Mock extraction for testing."""
        parts = []
        for i, path in enumerate(paths):
            parts.append(f"[MOCK OCR] Content from {Path(path).name}")
        return "\n---\n".join(parts)
