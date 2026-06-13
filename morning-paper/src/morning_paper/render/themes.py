"""Theme registry (Python side).

A theme is DATA, not code: themes/<id>/theme.toml + theme.css + assets. This
module parses and validates manifests and exposes theme capabilities (column
count, max-lead, page format) that the editorial grid planner must respect.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from ..config import THEMES_DIR

PageFormat = Literal["a4", "a3", "letter", "broadsheet", "tabloid"]
ColorMode = Literal["bw", "duotone", "color"]
PhotoTreatment = Literal["none", "bw", "duotone", "color"]


class FormatSpec(BaseModel):
    page: PageFormat = "a4"
    orientation: Literal["portrait", "landscape"] = "portrait"
    bleed_mm: float = 0.0
    color_mode: ColorMode = "bw"
    duotone: list[str] = Field(default_factory=list)


class GridSpec(BaseModel):
    columns: int = Field(default=6, ge=1, le=12)
    rule_weight: str = "1px"
    gutter: str = "10px"
    section_order: list[str] = Field(default_factory=list)
    max_lead: int = Field(default=1, ge=1)


class TypeSpec(BaseModel):
    masthead_font: str
    headline_font: str
    body_font: str
    scale: str = "classic"
    hyphenate: bool = True


class ColorSpec(BaseModel):
    paper: str = "#ffffff"
    ink: str = "#000000"
    accent: str = "#000000"


class PhotoSpec(BaseModel):
    treatment: PhotoTreatment = "bw"
    max_width_px: int = 1600


class FontAsset(BaseModel):
    family: str
    files: list[str]
    license: str  # required — asserted in tests so we never ship unlicensed fonts


class AssetSpec(BaseModel):
    masthead: str | None = None


class ThemeManifest(BaseModel):
    schema_version: int = 1
    id: str
    display_name: str
    mood: str = ""
    format: FormatSpec = FormatSpec()
    grid: GridSpec = GridSpec()
    type: TypeSpec
    colors: ColorSpec = ColorSpec()
    photo: PhotoSpec = PhotoSpec()
    fonts: list[FontAsset] = Field(default_factory=list)
    assets: AssetSpec = AssetSpec()

    @property
    def dir(self) -> Path:
        return THEMES_DIR / self.id

    def css_variables(self) -> dict[str, str]:
        """Map the manifest to the CSS custom properties base.css consumes."""
        return {
            "--paper": self.colors.paper,
            "--ink": self.colors.ink,
            "--accent": self.colors.accent,
            "--masthead-font": self.type.masthead_font,
            "--headline-font": self.type.headline_font,
            "--body-font": self.type.body_font,
            "--columns": str(self.grid.columns),
            "--rule-weight": self.grid.rule_weight,
            "--gutter": self.grid.gutter,
        }


def load_manifest(theme_id: str) -> ThemeManifest:
    path = THEMES_DIR / theme_id / "theme.toml"
    if not path.exists():
        raise FileNotFoundError(f"no theme manifest at {path}")
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    return ThemeManifest.model_validate(data)


def list_theme_ids() -> list[str]:
    if not THEMES_DIR.exists():
        return []
    return sorted(
        p.name
        for p in THEMES_DIR.iterdir()
        if p.is_dir() and not p.name.startswith("_") and (p / "theme.toml").exists()
    )


def list_manifests() -> list[ThemeManifest]:
    return [load_manifest(tid) for tid in list_theme_ids()]
