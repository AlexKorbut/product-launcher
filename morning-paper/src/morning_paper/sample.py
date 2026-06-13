"""Sample content for the Phase-0 typography prototype.

Used by `cli render-proto` and the renderer contract test so we can exercise the
whole theme/render path with NO LLM, network, or DB. The prose is filler.
"""

from __future__ import annotations

from .models import GridPlan, GridSlot, Story
from .render.document import build_render_document
from .render.themes import load_manifest

_LOREM = (
    "<p>В предрассветной тишине редакция собрала главные сюжеты дня, чтобы "
    "читатель мог осмыслить их за неспешной чашкой кофе. Ниже — связное "
    "изложение событий, без спешки и без шума ленты.</p>"
    "<p>Аналитики отмечают, что за сухими цифрами стоят живые решения людей, "
    "и именно их последствия определят повестку ближайших недель. Контекст "
    "важнее заголовка, а перспектива важнее сенсации.</p>"
    "<p>Мы переводим и пересказываем источники на разных языках, сохраняя "
    "ссылку на оригинал и уважая труд журналистов, чьи материалы легли в "
    "основу этого выпуска.</p>"
)


def _stories() -> list[Story]:
    rows = [
        ("s-lead", "world", "Дипломатия выходит из тупика", "Переговоры дали первый за месяц результат"),
        ("s-eu", "world", "Европа сверяет часы", "Брюссель ищет общий знаменатель"),
        ("s-mkt", "business", "Рынки нащупывают дно", "Инвесторы осторожно возвращаются"),
        ("s-firm", "business", "Сделка года под вопросом", "Регулятор берёт паузу"),
        ("s-ai", "tech", "ИИ переписывает редакции", "Инструменты меняют рабочий день"),
        ("s-chip", "tech", "Гонка за кремнием", "Новые фабрики и старые узкие места"),
        ("s-art", "culture", "Возвращение большой формы", "Романы снова в моде"),
        ("s-film", "culture", "Фестиваль без фаворитов", "Жюри в растерянности"),
    ]
    out: list[Story] = []
    for sid, section, headline, deck in rows:
        out.append(
            Story(
                id=sid,
                section=section,
                headline=headline,
                deck=deck,
                body_html=_LOREM,
                byline="Редакция Morning Paper",
                source="Wire",
                source_url="https://example.org/",
            )
        )
    return out


def sample_grid_plan(*, page_format: str, columns: int, section_order: list[str]) -> GridPlan:
    slots = [
        GridSlot(story_id="s-lead", section="world", size="lead", columns=min(columns, 6), with_photo=True,
                 pull_quote="Контекст важнее заголовка."),
        GridSlot(story_id="s-eu", section="world", size="medium", columns=2),
        GridSlot(story_id="s-mkt", section="business", size="medium", columns=2, with_photo=True),
        GridSlot(story_id="s-firm", section="business", size="brief", columns=1),
        GridSlot(story_id="s-ai", section="tech", size="medium", columns=2),
        GridSlot(story_id="s-chip", section="tech", size="brief", columns=1),
        GridSlot(story_id="s-art", section="culture", size="brief", columns=1),
        GridSlot(story_id="s-film", section="culture", size="brief", columns=1),
    ]
    return GridPlan(page_format=page_format, section_order=section_order, slots=slots)


def sample_render_document(theme_id: str, *, locale: str = "ru"):
    """Build a complete RenderDocument for a theme using sample content."""
    manifest = load_manifest(theme_id)
    grid = sample_grid_plan(
        page_format=manifest.format.page,
        columns=manifest.grid.columns,
        section_order=manifest.grid.section_order,
    )
    return build_render_document(
        issue_id="proto-0001",
        theme_id=theme_id,
        locale=locale,
        title="The Morning Paper",
        stories=_stories(),
        grid_plan=grid,
        issue_no="1",
        edition="Prototype",
    )
