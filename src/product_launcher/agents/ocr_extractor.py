"""
OCR Extractor Agent — extracts structured text from raw materials.
Handles brochures, images, and other document-like inputs.
"""
import json
import re
from . import BaseAgent, LLMClient


OCR_PROMPT = """Ты — эксперт по OCR и извлечению текста. Извлеки структурированный текст из сырого материала.

Верни ТОЛЬКО валидный JSON (без ```, без markdown):

{
  "text": "Полный извлечённый текст (все значимые слова и фразы)",
  "confidence": 0.0-1.0,
  "segments": [
    {"type": "title | feature | spec | price | description", "text": "текст сегмента"}
  ]
}

Правила:
- Извлекай ВЕСЬ значимый текст, не сокращай
- segments: разбей текст на логические сегменты по типу информации
- confidence: твоя уверенность в точности извлечения (0.0-1.0)
- Если текст пустой или бессмысленный — верни пустую строку и confidence 0.0
- На языке исходного текста
"""


class OCRExtractor(BaseAgent):
    """Extracts structured text from raw materials (brochures, images, etc.)."""

    agent_name = "ocr-extractor"
    description = "Извлекает структурированный текст из брошюр / сырых материалов"

    def run(self, input_data: dict) -> dict:
        """
        Args:
            input_data: {"raw_text": "..."}

        Returns:
            {"text": "...", "confidence": 0.0-1.0, "segments": [...]}
        """
        raw_text = input_data.get("raw_text", "")

        if not raw_text or not raw_text.strip():
            return self._fallback("")

        self.log(f"Извлекаю текст ({len(raw_text)} символов)...")

        messages = [
            {"role": "system", "content": OCR_PROMPT},
            {"role": "user", "content": f"Извлеки структурированный текст:\n\n{raw_text}"},
        ]

        response = self.llm.chat(messages, temperature=0.1, max_tokens=4096)
        result = self._parse(response)

        if not result or not result.get("text"):
            self.log("⚠️ Fallback: не удалось извлечь через LLM")
            return self._fallback(raw_text)

        # Ensure all fields
        result.setdefault("confidence", 0.5)
        result.setdefault("segments", [])

        self.log(f"✓ Извлечено: {len(result['text'])} символов, confidence={result['confidence']}")
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

    def _fallback(self, raw_text: str) -> dict:
        """Extract usable text without LLM."""
        if not raw_text or not raw_text.strip():
            return {
                "text": "",
                "confidence": 0.0,
                "segments": [],
            }

        # Clean and normalize
        cleaned = raw_text.strip()
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)

        # Basic segmentation by sentence boundaries
        sentences = re.split(r'[.!?]\s+', cleaned)
        segments = []
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            # Basic type detection
            if re.match(r'^[\d]', s):
                seg_type = "spec"
            elif re.match(r'^\$', s) or re.search(r'\$\d+', s):
                seg_type = "price"
            elif len(s.split()) <= 4:
                seg_type = "title"
            else:
                seg_type = "description"
            segments.append({"type": seg_type, "text": s})

        return {
            "text": cleaned,
            "confidence": 0.7,  # Heuristic extraction
            "segments": segments,
        }
