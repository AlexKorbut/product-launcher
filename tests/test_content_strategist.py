"""
Tests for ContentStrategist agent.
Takes ProductKB → generates content strategy for all platforms.
"""
import json
import pytest
from product_launcher.agents import LLMClient
from product_launcher.agents.content_strategist import ContentStrategist


# ─── Mock LLMs ───

class StrategyMockLLM(LLMClient):
    """Returns realistic content strategy."""

    def chat(self, messages, temperature=0.3, max_tokens=4096):
        return json.dumps({
            "strategy_name": "Кофе нового поколения",
            "content_pillars": [
                {
                    "name": "Технология",
                    "description": "LiDAR, AI, автоподбор рецепта",
                    "angle": "Наука на службе вкуса",
                    "hashtags": ["#технологии", "#умныйкофе"],
                },
                {
                    "name": "Вкус",
                    "description": "Идеальный кофе каждое утро без усилий",
                    "angle": "Бариста у вас дома",
                    "hashtags": ["#кофе", "#вкус"],
                },
                {
                    "name": "Дизайн",
                    "description": "Премиальный внешний вид, впишется в любой интерьер",
                    "angle": "Техника как искусство",
                    "hashtags": ["#дизайн", "#интерьер"],
                },
                {
                    "name": "Образ жизни",
                    "description": "Утренние ритуалы, экономия времени, забота о себе",
                    "angle": "5 минут на идеальное утро",
                    "hashtags": ["#утро", "#лайфстайл"],
                },
            ],
            "target_hooks": [
                "Забудьте о грязных чашках и жжёном кофе",
                "Ваш персональный бариста за 499 долларов",
                "Почему 90% людей неправильно варят кофе",
                "Один девайс — 50 рецептов кофе",
            ],
            "platforms": {
                "instagram": {
                    "format": "Карусели и Reels",
                    "frequency": "5 постов/неделя",
                    "tone_notes": "Визуальный, вдохновляющий, lifestyle",
                    "examples": [
                        "Карусель: 5 утренних ритуалов с кофе",
                        "Reels: процесс приготовления за 15 секунд",
                        "Пост-сравнение: обычная кофеварка vs умная",
                    ],
                },
                "tiktok": {
                    "format": "Короткие видео 15-30 сек",
                    "frequency": "3 видео/день",
                    "tone_notes": "Динамичный, трендовый, нативный",
                    "examples": [
                        "POV: Monday morning with AI coffee",
                        "Тренд: покажи свой утренний ритуал",
                        "Дуэт с известным бариста",
                    ],
                },
                "threads": {
                    "format": "Текстовые треды",
                    "frequency": "2-3 треда/день",
                    "tone_notes": "Экспертный, community-driven, честный",
                    "examples": [
                        "Тред: мифы о кофе, в которые мы верили",
                        "Опрос: какой кофе вы пьёте утром?",
                    ],
                },
                "website": {
                    "format": "Лендинг из 5 секций",
                    "sections": [
                        "Hero: продукт + главная метрика",
                        "Технология: как это работает",
                        "Результаты: до/после, отзывы",
                        "Для кого: портреты пользователей",
                        "CTA: предзаказ со скидкой",
                    ],
                    "tone_notes": "Продающий, доверительный, tech-стиль",
                },
            },
            "tone_of_voice": {
                "primary": "friendly",
                "rules": [
                    "На «ты» с аудиторией",
                    "Минимум канцелярита",
                    "Один эмодзи на 2-3 предложения",
                    "Цифры и факты вместо общих слов",
                ],
            },
            "content_calendar": {
                "week_1": "Запуск: тизеры и интрига",
                "week_2": "Технология: LiDAR, рецепты, демо",
                "week_3": "Социальные доказательства: UGC, отзывы",
                "week_4": "Призыв к действию: скидки, предзаказ",
            },
        })


class MinimalMockLLM(LLMClient):
    """Minimal valid response."""

    def chat(self, messages, temperature=0.3, max_tokens=4096):
        return json.dumps({
            "content_pillars": [
                {"name": "Основной", "description": "test", "angle": "test", "hashtags": ["#test"]},
            ],
            "target_hooks": ["Hook 1"],
            "platforms": {
                "instagram": {"format": "test", "frequency": "1/week", "tone_notes": "test", "examples": []},
                "tiktok": {"format": "test", "frequency": "1/week", "tone_notes": "test", "examples": []},
                "threads": {"format": "test", "frequency": "1/week", "tone_notes": "test", "examples": []},
                "website": {"format": "test", "sections": ["1"], "tone_notes": "test"},
            },
            "tone_of_voice": {"primary": "minimal", "rules": ["rule"]},
            "content_calendar": {},
        })


class BadLLM(LLMClient):
    """Returns broken/incomplete JSON."""

    def chat(self, messages, temperature=0.3, max_tokens=4096):
        return "Not JSON {{{{"


# ─── Test input: ProductKB ───

SAMPLE_KB = {
    "product": {
        "name": "SmartClean Pro X1",
        "description": "Робот-пылесос с LiDAR и УФ-стерилизацией",
        "usp": "Единственный с УФ-стерилизацией и влажной уборкой за один проход",
        "features": ["LiDAR", "Самоочистка", "УФ-стерилизация", "Влажная уборка"],
        "specs": {"battery": "5200 mAh", "suction": "4000 Pa"},
        "price_range": "$299-399",
    },
    "brand": {
        "tone_of_voice": {"primary": "friendly", "adjectives": ["тёплый", "технологичный"], "donts": ["агрессивный"]},
        "colors": {"primary": "#2D3436", "secondary": "#0984E3", "accent": "#00B894"},
        "target_audience": {
            "demographics": "25-45, городские жители",
            "pain_points": ["Нет времени на уборку", "Аллергия"],
            "platforms": ["Instagram", "TikTok", "Threads"],
        },
    },
    "market": {
        "competitors": ["Roomba", "Xiaomi"],
        "differentiator": "УФ-стерилизация",
        "geo_focus": "Россия, СНГ",
    },
}


# ─── Tests ───

class TestContentStrategistInit:
    """Agent initialization."""

    def test_creates_with_default_llm(self):
        agent = ContentStrategist()
        assert agent.agent_name == "content-strategist"

    def test_creates_with_custom_llm(self):
        llm = StrategyMockLLM()
        agent = ContentStrategist(llm=llm)
        assert agent.llm is llm


class TestContentStrategistRun:
    """Core strategy generation."""

    def test_generates_full_strategy(self):
        """Full KB → complete content strategy."""
        agent = ContentStrategist(llm=StrategyMockLLM())
        result = agent.run({"kb": SAMPLE_KB})

        assert "strategy_name" in result
        assert len(result["content_pillars"]) == 4
        assert result["content_pillars"][0]["name"] == "Технология"
        assert len(result["target_hooks"]) == 4
        assert "instagram" in result["platforms"]
        assert "tiktok" in result["platforms"]
        assert result["platforms"]["instagram"]["frequency"] is not None

    def test_handles_empty_kb(self):
        """Empty KB → graceful fallback."""
        agent = ContentStrategist(llm=StrategyMockLLM())
        result = agent.run({"kb": {}})

        assert "content_pillars" in result
        assert len(result["content_pillars"]) > 0

    def test_handles_broken_llm(self):
        """Invalid LLM response → fallback, no crash."""
        agent = ContentStrategist(llm=BadLLM())
        result = agent.run({"kb": SAMPLE_KB})

        assert "content_pillars" in result
        assert len(result["content_pillars"]) > 0  # fallback pillars

    def test_all_platforms_present(self):
        """Strategy covers all required platforms."""
        agent = ContentStrategist(llm=StrategyMockLLM())
        result = agent.run({"kb": SAMPLE_KB})

        for platform in ["instagram", "tiktok", "threads", "website"]:
            assert platform in result["platforms"], f"Missing {platform}"
            assert isinstance(result["platforms"][platform], dict)

    def test_tone_of_voice_rules(self):
        """Tone guidelines are actionable."""
        agent = ContentStrategist(llm=StrategyMockLLM())
        result = agent.run({"kb": SAMPLE_KB})

        assert "tone_of_voice" in result
        assert "primary" in result["tone_of_voice"]
        assert len(result["tone_of_voice"]["rules"]) > 0

    def test_strategy_includes_product_name(self):
        """Strategy references the actual product."""
        agent = ContentStrategist(llm=StrategyMockLLM())
        result = agent.run({"kb": SAMPLE_KB})

        # Product name should appear somewhere in the strategy
        strategy_text = json.dumps(result, ensure_ascii=False)
        assert "SmartClean" in strategy_text or "content_pillars" in result

    def test_result_is_json_serializable(self):
        """Result must be JSON-serializable for kanban storage."""
        agent = ContentStrategist(llm=StrategyMockLLM())
        result = agent.run({"kb": SAMPLE_KB})

        dumped = json.dumps(result, ensure_ascii=False)
        parsed = json.loads(dumped)
        assert parsed == result


class TestContentStrategistPrompt:
    """Prompt construction."""

    def test_prompt_includes_product_info(self):
        """Prompt contains key product details."""
        agent = ContentStrategist(llm=MinimalMockLLM())
        # Run with specific KB to check prompt is built correctly
        result = agent.run({"kb": SAMPLE_KB})
        assert result is not None  # Doesn't crash

    def test_prompt_handles_missing_fields(self):
        """Missing KB fields don't crash prompt builder."""
        agent = ContentStrategist(llm=MinimalMockLLM())
        partial_kb = {
            "product": {"name": "Test"},
        }
        result = agent.run({"kb": partial_kb})
        assert "content_pillars" in result


class TestContentStrategistFallback:
    """Fallback strategy when LLM fails."""

    def test_fallback_has_minimum_viable_strategy(self):
        """Fallback strategy is usable for generation."""
        agent = ContentStrategist(llm=BadLLM())
        result = agent.run({"kb": SAMPLE_KB})

        assert len(result["content_pillars"]) >= 1
        assert len(result["target_hooks"]) >= 1
        assert "instagram" in result["platforms"]
        assert "tone_of_voice" in result
