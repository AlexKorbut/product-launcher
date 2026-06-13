"""Rendering package: render-document assembly, theme registry, Node boundary."""

from .document import build_render_document
from .renderer import NodeRenderer, Renderer, RenderError, RenderResult
from .themes import ThemeManifest, list_manifests, list_theme_ids, load_manifest

__all__ = [
    "build_render_document",
    "NodeRenderer",
    "Renderer",
    "RenderError",
    "RenderResult",
    "ThemeManifest",
    "list_manifests",
    "list_theme_ids",
    "load_manifest",
]
