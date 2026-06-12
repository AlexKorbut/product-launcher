"""Post generation/rewrite via the Anthropic API (async client, adaptive thinking)."""
import difflib
from dataclasses import dataclass

import anthropic

from app.config import get_settings
from app.models import Channel

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


def _client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=get_settings().anthropic_api_key)


def build_system_prompt(channel: Channel) -> str:
    if channel.prompt_template.strip():
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


def _cost(input_tokens: int, output_tokens: int) -> float:
    s = get_settings()
    return (
        input_tokens * s.price_input_per_mtok / 1_000_000
        + output_tokens * s.price_output_per_mtok / 1_000_000
    )


async def rewrite_post(channel: Channel, source_text: str) -> GenerationResult:
    """Rewrite a donor post for the given channel."""
    s = get_settings()
    user_prompt = (
        f"{REWRITE_MODES[channel.rewrite_level]}\n\n"
        f"Исходный пост:\n<<<\n{source_text}\n>>>\n\n"
        f"Напиши итоговый пост."
    )
    response = await _client().messages.create(
        model=s.generation_model,
        max_tokens=s.generation_max_tokens,
        thinking={"type": "adaptive"},
        system=[
            {
                "type": "text",
                "text": build_system_prompt(channel),
                # The channel profile is stable across requests — cache it.
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = next((b.text for b in response.content if b.type == "text"), "").strip()
    usage = response.usage
    input_tokens = (
        usage.input_tokens
        + (usage.cache_creation_input_tokens or 0)
        + (usage.cache_read_input_tokens or 0)
    )
    return GenerationResult(
        text=text,
        model=response.model,
        input_tokens=input_tokens,
        output_tokens=usage.output_tokens,
        cost_usd=_cost(usage.input_tokens, usage.output_tokens),
        similarity_to_source=similarity(source_text, text),
    )


async def generate_from_topic(channel: Channel) -> GenerationResult:
    """Generate a post from scratch using only the channel topic profile."""
    s = get_settings()
    response = await _client().messages.create(
        model=s.generation_model,
        max_tokens=s.generation_max_tokens,
        thinking={"type": "adaptive"},
        system=[
            {
                "type": "text",
                "text": build_system_prompt(channel),
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": (
                    "Придумай и напиши новый пост для канала по его тематике. "
                    "Выбери конкретный, интересный аудитории угол — не общие слова."
                ),
            }
        ],
    )
    text = next((b.text for b in response.content if b.type == "text"), "").strip()
    usage = response.usage
    return GenerationResult(
        text=text,
        model=response.model,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cost_usd=_cost(usage.input_tokens, usage.output_tokens),
        similarity_to_source=0.0,
    )
