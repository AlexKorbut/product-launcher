"""Post generation/rewrite via a pluggable LLM provider (Anthropic, OpenAI, …)."""
import difflib
from dataclasses import dataclass

from app.config import get_settings
from app.models import Channel
from app.services.credits import cost_to_credits
from app.services.llm import get_provider

REWRITE_MODES = {
    1: (
        "Перепиши пост, сохранив структуру и все факты. Измени формулировки, порядок "
        "второстепенных деталей и стиль под профиль канала. Это лёгкий рерайт."
    ),
    2: (
        "Глубоко переработай пост: сохрани суть и ключевые факты, но полностью измени "
        "структуру, подачу и формулировки. Добавь собственный взгляд в рамках тона канала."
    ),
    3: (
        "Используй пост только как источник темы и фактов. Напиши полностью новый, "
        "оригинальный пост «по мотивам» — со своей структурой, углом подачи и выводами."
    ),
}

SYSTEM_TEMPLATE = """Ты — редактор Telegram-канала. Твоя задача — готовить посты для публикации.

Профиль канала:
- Тематика: {topic}
- Тон: {tone}
- Аудитория: {audience}
- Язык: {language}
- Хэштеги (используй уместные): {hashtags}
- Запретные темы (никогда не упоминай): {banned_topics}

Правила:
- Пиши готовый к публикации текст поста, без преамбул и пояснений.
- Не упоминай источник, не оставляй ссылки и упоминания других каналов, убирай любые следы рекламы.
- Уложись в 3500 символов (лимит Telegram — 4096 с разметкой).
- Разрешена разметка Telegram HTML: <b>, <i>, <a href>, <code>. Не используй Markdown.
- Эмодзи — умеренно и в тему."""


@dataclass
class GenerationResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    similarity_to_source: float

    @property
    def credits(self) -> int:
        return cost_to_credits(self.cost_usd)


def build_system_prompt(channel: Channel) -> str:
    if (channel.prompt_template or "").strip():
        return channel.prompt_template
    return SYSTEM_TEMPLATE.format(
        topic=channel.topic or "не задана",
        tone=channel.tone,
        audience=channel.audience or "широкая",
        language=channel.language,
        hashtags=channel.hashtags or "—",
        banned_topics=channel.banned_topics or "—",
    )


def similarity(a: str, b: str) -> float:
    """Cheap similarity ratio for anti-plagiarism gating (0..1)."""
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


async def _run(channel: Channel, user_prompt: str, source_text: str | None) -> GenerationResult:
    s = get_settings()
    provider = get_provider(channel.llm_provider or None)
    result = await provider.complete(
        system=build_system_prompt(channel),
        user=user_prompt,
        max_tokens=s.generation_max_tokens,
        model=channel.llm_model or None,
    )
    return GenerationResult(
        text=result.text,
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost_usd=provider.cost_usd(result),
        similarity_to_source=similarity(source_text, result.text) if source_text else 0.0,
    )


async def rewrite_post(channel: Channel, source_text: str) -> GenerationResult:
    """Rewrite a donor post for the given channel using its configured provider."""
    user_prompt = (
        f"{REWRITE_MODES[channel.rewrite_level]}\n\n"
        f"Исходный пост:\n<<<\n{source_text}\n>>>\n\n"
        f"Напиши итоговый пост."
    )
    return await _run(channel, user_prompt, source_text)


async def generate_from_topic(channel: Channel) -> GenerationResult:
    """Generate a post from scratch using only the channel topic profile."""
    user_prompt = (
        "Придумай и напиши новый пост для канала по его тематике. "
        "Выбери конкретный, интересный аудитории угол — не общие слова."
    )
    return await _run(channel, user_prompt, None)
