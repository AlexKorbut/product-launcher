"""
Tests for Product Knowledge Base — the central data model.
All agents read from this, so it must be rock-solid.
"""
import pytest
import json
from datetime import datetime


# ─── RED: these imports will fail until we create the module ───

def test_kb_importable():
    """Module must be importable."""
    from product_launcher.kb import ProductKB


class TestProductKBValidation:
    """Valid KB data must pass validation."""

    def test_valid_kb_with_all_required_fields(self):
        """KB with all required fields validates successfully."""
        from product_launcher.kb import ProductKB

        kb = ProductKB(
            product={
                "name": "AI-Powered Coffee Machine",
                "description": "Makes coffee using AI",
                "usp": "Never bitter, always perfect",
                "features": ["Auto-brew", "Voice control", "Self-cleaning"],
                "specs": {"power": "220V", "capacity": "1.5L"},
            },
            brand={
                "tone_of_voice": {
                    "primary": "friendly",
                    "adjectives": ["warm", "modern"],
                    "donts": ["corporate", "boring"],
                },
                "colors": {"primary": "#FF6B35", "secondary": "#004E89", "accent": "#1A936F"},
                "target_audience": {
                    "demographics": "25-45, tech-savvy",
                    "pain_points": ["Bad coffee at home", "Complicated machines"],
                    "platforms": ["Instagram", "TikTok", "Threads"],
                },
            },
            market={
                "competitors": ["Nespresso", "Jura"],
                "differentiator": "AI taste calibration",
                "geo_focus": "Global",
            },
            source={
                "event": "Guangzhou Trade Fair 2026",
                "location": "Guangzhou, China",
                "date": "2026-05-10",
                "raw_text": "Brochure text here...",
                "images": ["photo1.jpg", "photo2.jpg"],
            },
        )

        assert kb.product.name == "AI-Powered Coffee Machine"
        assert kb.product.usp == "Never bitter, always perfect"
        assert len(kb.product.features) == 3
        assert kb.brand.colors.primary == "#FF6B35"
        assert kb.brand.tone_of_voice.primary == "friendly"
        assert len(kb.market.competitors) == 2
        assert kb.source.event == "Guangzhou Trade Fair 2026"


class TestProductKBValidationErrors:
    """Invalid data must raise clear errors."""

    def test_missing_required_product_field_raises_error(self):
        """Missing 'name' in product raises ValidationError."""
        from product_launcher.kb import ProductKB
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ProductKB(
                product={
                    # name is missing
                    "description": "Something",
                    "usp": "Unique",
                    "features": ["f1"],
                    "specs": {},
                },
                brand={
                    "tone_of_voice": {"primary": "neutral", "adjectives": [], "donts": []},
                    "colors": {"primary": "#000", "secondary": "#fff", "accent": "#888"},
                    "target_audience": {"demographics": "all", "pain_points": [], "platforms": []},
                },
                market={"competitors": [], "differentiator": "", "geo_focus": ""},
                source={"event": "", "location": "", "date": "", "raw_text": "", "images": []},
            )

    def test_empty_product_name_raises_error(self):
        """Empty product name should fail validation."""
        from product_launcher.kb import ProductKB
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ProductKB(
                product={
                    "name": "",  # empty!
                    "description": "Something",
                    "usp": "Unique",
                    "features": ["f1"],
                    "specs": {},
                },
                brand={
                    "tone_of_voice": {"primary": "neutral", "adjectives": [], "donts": []},
                    "colors": {"primary": "#000", "secondary": "#fff", "accent": "#888"},
                    "target_audience": {"demographics": "all", "pain_points": [], "platforms": []},
                },
                market={"competitors": [], "differentiator": "", "geo_focus": ""},
                source={"event": "", "location": "", "date": "", "raw_text": "", "images": []},
            )

    def test_invalid_color_hex_raises_error(self):
        """Non-hex color code should fail."""
        from product_launcher.kb import ProductKB
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ProductKB(
                product={
                    "name": "Test",
                    "description": "Test",
                    "usp": "Test",
                    "features": ["f1"],
                    "specs": {},
                },
                brand={
                    "tone_of_voice": {"primary": "neutral", "adjectives": [], "donts": []},
                    "colors": {"primary": "not-a-color", "secondary": "#fff", "accent": "#888"},
                    "target_audience": {"demographics": "all", "pain_points": [], "platforms": []},
                },
                market={"competitors": [], "differentiator": "", "geo_focus": ""},
                source={"event": "", "location": "", "date": "", "raw_text": "", "images": []},
            )


class TestProductKBSerialization:
    """KB must serialize to/from JSON."""

    def test_kb_to_json_and_back(self):
        """Round-trip: KB → JSON → KB preserves all data."""
        from product_launcher.kb import ProductKB

        original = ProductKB(
            product={
                "name": "Roundtrip Test",
                "description": "Testing serialization",
                "usp": "Serializable",
                "features": ["f1"],
                "specs": {"key": "value"},
            },
            brand={
                "tone_of_voice": {"primary": "neutral", "adjectives": ["clean"], "donts": []},
                "colors": {"primary": "#111", "secondary": "#222", "accent": "#333"},
                "target_audience": {"demographics": "devs", "pain_points": [], "platforms": []},
            },
            market={"competitors": [], "differentiator": "test", "geo_focus": "earth"},
            source={"event": "test", "location": "here", "date": "2026-01-01", "raw_text": "", "images": []},
        )

        # To JSON string
        json_str = original.model_dump_json(indent=2)

        # Back to KB
        parsed = ProductKB.model_validate_json(json_str)

        assert parsed.product.name == original.product.name
        assert parsed.brand.colors.primary == original.brand.colors.primary
        assert parsed.model_dump() == original.model_dump()
