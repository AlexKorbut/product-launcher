"""
Tests for content generators: Website, TikTok, Instagram, Threads.
Each takes ContentStrategy → platform-specific content.
"""
import json
import pytest
from product_launcher.agents import LLMClient
from product_launcher.agents.content_generator import (
    ContentGenerator,
    WebsiteGenerator,
    TikTokGenerator,
    InstagramGenerator,
    ThreadsGenerator,
)


# ─── Mock LLMs ───

class WebsiteMockLLM(LLMClient):
    def chat(self, messages, temperature=0.3, max_tokens=4096):
        return json.dumps({
            "sections": [
                {
                    "id": "hero",
                    "headline": "Революция утреннего кофе",
                    "subheadline": "AI-powered кофемашина, которая знает ваш вкус",
                    "cta": "Предзаказать со скидкой 20%",
                    "visual": "Продукт на тёмном фоне с паром",
                },
                {
                    "id": "features",
                    "headline": "Технология, которая работает на вас",
                    "items": [
                        {"title": "LiDAR-навигация", "desc": "Точное картографирование помещения"},
                        {"title": "50 рецептов", "desc": "От эспрессо до флэт уайта одним нажатием"},
                    ],
                },
            ],
            "meta": {"title": "AI Coffee Machine | Умный кофе дома", "description": "..."},
            "tokens": 1200,
        })


class TikTokMockLLM(LLMClient):
    def chat(self, messages, temperature=0.7, max_tokens=4096):
        return json.dumps({
            "scripts": [
                {
                    "id": "t1",
                    "hook": "POV: твой понедельник спасён ☕️",
                    "duration_sec": 25,
                    "scenes": [
                        {"time": "0-3s", "visual": "Крупный план: нажатие кнопки", "text": "", "sound": "Звук включения"},
                        {"time": "3-15s", "visual": "Процесс приготовления кофе", "text": "Когда кофемашина знает твой идеальный рецепт", "sound": "Трендовый трек"},
                        {"time": "15-25s", "visual": "Девушка пьёт кофе, улыбается", "text": "Утро. Сделано. 🔥", "sound": "Бит дроп"},
                    ],
                    "hashtags": ["#кофе", "#утро", "#технологии", "#fyp"],
                },
            ],
            "tokens": 800,
        })


class InstagramMockLLM(LLMClient):
    def chat(self, messages, temperature=0.7, max_tokens=4096):
        return json.dumps({
            "carousels": [
                {
                    "id": "ig1",
                    "slides": [
                        {"image_desc": "Продукт на мраморном столе", "text": "Знакомьтесь — ваш новый утренний ритуал ☕️"},
                        {"image_desc": "Крупный план интерфейса", "text": "50 рецептов в одном устройстве"},
                        {"image_desc": "Инфографика: 3 фичи", "text": "LiDAR + УФ + Самоочистка ✨"},
                        {"image_desc": "Счастливый пользователь", "text": "5 минут = идеальный кофе"},
                    ],
                    "caption": "Умная кофемашина, которая учится вашему вкусу. LiDAR-навигация, 50 рецептов, самоочистка. Предзаказ открыт! 🔗 в шапке профиля",
                    "hashtags": ["#умныйдом", "#кофе", "#технологии", "#новинка"],
                },
            ],
            "reels": [
                {
                    "id": "r1",
                    "hook": "Как мы тестировали 50 рецептов за 1 день ☕️",
                    "duration_sec": 30,
                    "description": "Бэкстейдж: команда тестирует все режимы кофемашины",
                },
            ],
            "tokens": 600,
        })


class ThreadsMockLLM(LLMClient):
    def chat(self, messages, temperature=0.7, max_tokens=4096):
        return json.dumps({
            "threads": [
                {
                    "id": "th1",
                    "title": "Почему домашний кофе никогда не будет как в кофейне (и что с этим делать) 🧵",
                    "posts": [
                        "1/7 Каждый бариста знает: секрет не в зёрнах, а в постоянстве параметров. Температура, помол, давление — если хоть одно плавает, кофе уже не тот.",
                        "2/7 Дома вы не можете контролировать всё это вручную. Вернее, можете, но кто будет этим заниматься в 7 утра?",
                        "3/7 Мы встроили в кофемашину те же сенсоры, что стоят в профессиональных машинах за $5000+. Разница — в цене и размере.",
                        "4/7 LiDAR сканирует чашку, определяет объём и автоматически подбирает пропорции. Никаких «ой, перелил».",
                        "5/7 Результат: идеальный эспрессо каждое утро. Без весов, без таймера, без мата.",
                        "6/7 Мы запускаем предзаказ на следующей неделе. Первые 100 покупателей получат годовой запас зёрен в подарок.",
                        "7/7 Какой кофе вы пьёте утром? Делитесь в комментариях — самый популярный ответ протестируем в прямом эфире ☕️",
                    ],
                },
            ],
            "tokens": 500,
        })


class FailMockLLM(LLMClient):
    def chat(self, messages, temperature=0.3, max_tokens=4096):
        return "not json {{{"


# ─── Sample strategy ───

SAMPLE_STRATEGY = {
    "strategy_name": "Кофе нового поколения",
    "content_pillars": [
        {"name": "Технология", "angle": "Наука на службе вкуса", "hashtags": ["#технологии"]},
        {"name": "Вкус", "angle": "Бариста у вас дома", "hashtags": ["#кофе"]},
    ],
    "target_hooks": ["Забудьте о плохом кофе", "Ваш бариста за $499"],
    "platforms": {
        "instagram": {"format": "Карусели", "frequency": "5/неделя", "tone_notes": "Визуальный"},
        "tiktok": {"format": "Видео 15-30с", "frequency": "3/день", "tone_notes": "Динамичный"},
        "threads": {"format": "Треды", "frequency": "2/день", "tone_notes": "Экспертный"},
        "website": {"format": "Лендинг", "sections": ["Hero", "Фичи"], "tone_notes": "Продающий"},
    },
    "tone_of_voice": {"primary": "friendly", "rules": ["На ты", "Без канцелярита"]},
    "content_calendar": {"week_1": "Запуск"},
}

SAMPLE_KB = {
    "product": {
        "name": "AI Coffee Machine",
        "description": "Умная кофемашина с AI",
        "usp": "50 рецептов, LiDAR, самоочистка",
        "features": ["LiDAR", "50 рецептов", "Самоочистка"],
        "specs": {"power": "1500W"},
        "price_range": "$499",
    },
    "brand": {
        "tone_of_voice": {"primary": "friendly"},
        "colors": {"primary": "#2D3436", "secondary": "#0984E3", "accent": "#00B894"},
        "target_audience": {"demographics": "25-45", "platforms": ["Instagram", "TikTok"]},
    },
}


# ─── Tests ───

class TestWebsiteGenerator:
    def test_generates_landing_page(self):
        gen = WebsiteGenerator(llm=WebsiteMockLLM())
        result = gen.run({"strategy": SAMPLE_STRATEGY, "kb": SAMPLE_KB})

        assert len(result["sections"]) >= 2
        assert result["sections"][0]["id"] == "hero"
        assert "headline" in result["sections"][0]
        assert "meta" in result

    def test_fallback_on_broken_llm(self):
        gen = WebsiteGenerator(llm=FailMockLLM())
        result = gen.run({"strategy": SAMPLE_STRATEGY, "kb": SAMPLE_KB})

        assert len(result["sections"]) > 0
        assert "headline" in result["sections"][0]


class TestTikTokGenerator:
    def test_generates_scripts(self):
        gen = TikTokGenerator(llm=TikTokMockLLM())
        result = gen.run({"strategy": SAMPLE_STRATEGY, "kb": SAMPLE_KB})

        assert len(result["scripts"]) >= 1
        assert "hook" in result["scripts"][0]
        assert "scenes" in result["scripts"][0]
        assert len(result["scripts"][0]["scenes"]) >= 2

    def test_fallback_on_broken_llm(self):
        gen = TikTokGenerator(llm=FailMockLLM())
        result = gen.run({"strategy": SAMPLE_STRATEGY, "kb": SAMPLE_KB})
        assert "scripts" in result


class TestInstagramGenerator:
    def test_generates_carousels_and_reels(self):
        gen = InstagramGenerator(llm=InstagramMockLLM())
        result = gen.run({"strategy": SAMPLE_STRATEGY, "kb": SAMPLE_KB})

        assert "carousels" in result
        assert "reels" in result
        assert len(result["carousels"]) >= 1

    def test_fallback_on_broken_llm(self):
        gen = InstagramGenerator(llm=FailMockLLM())
        result = gen.run({"strategy": SAMPLE_STRATEGY, "kb": SAMPLE_KB})
        assert "carousels" in result


class TestThreadsGenerator:
    def test_generates_threads(self):
        gen = ThreadsGenerator(llm=ThreadsMockLLM())
        result = gen.run({"strategy": SAMPLE_STRATEGY, "kb": SAMPLE_KB})

        assert len(result["threads"]) >= 1
        assert "title" in result["threads"][0]
        assert len(result["threads"][0]["posts"]) >= 3

    def test_fallback_on_broken_llm(self):
        gen = ThreadsGenerator(llm=FailMockLLM())
        result = gen.run({"strategy": SAMPLE_STRATEGY, "kb": SAMPLE_KB})
        assert "threads" in result


class TestAllGeneratorsJsonSerializable:
    @pytest.mark.parametrize("gen_class,llm_class", [
        (WebsiteGenerator, WebsiteMockLLM),
        (TikTokGenerator, TikTokMockLLM),
        (InstagramGenerator, InstagramMockLLM),
        (ThreadsGenerator, ThreadsMockLLM),
    ])
    def test_output_is_json_serializable(self, gen_class, llm_class):
        gen = gen_class(llm=llm_class())
        result = gen.run({"strategy": SAMPLE_STRATEGY, "kb": SAMPLE_KB})

        dumped = json.dumps(result, ensure_ascii=False)
        parsed = json.loads(dumped)
        assert parsed == result
