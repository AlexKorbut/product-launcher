"""Theme catalog. Exposes only safe public fields (no font files/licenses)."""

from __future__ import annotations

from fastapi import APIRouter

from ...render.themes import list_manifests
from ..schemas import ThemeOut

router = APIRouter(tags=["themes"])


@router.get("/themes", response_model=list[ThemeOut])
def list_themes() -> list[ThemeOut]:
    out: list[ThemeOut] = []
    for m in list_manifests():
        out.append(
            ThemeOut(
                id=m.id,
                display_name=m.display_name,
                mood=m.mood,
                page=m.format.page,
                columns=m.grid.columns,
                color_mode=m.format.color_mode,
                colors={
                    "paper": m.colors.paper,
                    "ink": m.colors.ink,
                    "accent": m.colors.accent,
                },
            )
        )
    return out
