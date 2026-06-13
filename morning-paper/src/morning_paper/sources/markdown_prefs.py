"""Markdown interests file source. Auth-free; the user hands us a `.md` file (or
inline text) describing what they care about. Bullets/numbered items become SURVEY
signals; prose paragraphs become FREE_TEXT.
"""

from __future__ import annotations

import os
import re
from typing import ClassVar

from pydantic import BaseModel

from ..models import Signal, SignalKind
from .base import AuthFreeSource, AuthState, FetchResult, SourceConfig
from .registry import register

_BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")
_HEADING_RE = re.compile(r"^\s*(#{1,6})\s+(.*)$")
_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_EMPHASIS_RE = re.compile(r"[*_`]+")


class MarkdownPrefsOptions(BaseModel):
    path: str = ""          # path to a .md file
    text: str = ""          # inline markdown, used when path is empty/missing


@register
class MarkdownPrefsSource(AuthFreeSource):
    source_id: ClassVar[str] = "markdown_prefs"
    display_name: ClassVar[str] = "Interests file (Markdown)"
    config_schema: ClassVar[type[BaseModel]] = MarkdownPrefsOptions

    def fetch(
        self, cfg: SourceConfig, auth: AuthState, *, cursor: str | None
    ) -> FetchResult:
        opts = MarkdownPrefsOptions.model_validate(cfg.options)
        warnings: list[str] = []

        content = ""
        if opts.path and os.path.isfile(opts.path):
            try:
                with open(opts.path, encoding="utf-8") as fh:
                    content = fh.read()
            except OSError as exc:
                warnings.append(f"could not read markdown file {opts.path}: {exc}")
        elif opts.text:
            content = opts.text
        else:
            warnings.append("markdown_prefs: no file at `path` and no inline `text`")
            return FetchResult(signals=[], cursor=None, warnings=warnings)

        signals = self._parse(content, cfg)
        return FetchResult(signals=signals, cursor=None, warnings=warnings)

    def _parse(self, content: str, cfg: SourceConfig) -> list[Signal]:
        signals: list[Signal] = []
        section: str | None = None
        paragraph: list[str] = []
        idx = 0

        def flush_paragraph() -> None:
            nonlocal idx
            if not paragraph:
                return
            text = _clean(" ".join(paragraph))
            paragraph.clear()
            if not text:
                return
            hint = [section] if section else []
            signals.append(
                Signal.make(
                    user_id=cfg.user_id,
                    source_id=self.source_id,
                    kind=SignalKind.FREE_TEXT,
                    text=text,
                    external_id=f"md:{idx}",
                    entities_hint=hint,
                )
            )
            idx += 1

        for raw_line in content.splitlines():
            line = raw_line.rstrip()
            if not line.strip():
                flush_paragraph()
                continue

            heading = _HEADING_RE.match(line)
            if heading:
                flush_paragraph()
                section = _clean(heading.group(2))
                continue

            bullet = _BULLET_RE.match(line)
            if bullet:
                flush_paragraph()
                text = _clean(bullet.group(1))
                if not text:
                    continue
                hint = [text]
                if section:
                    hint.append(section)
                signals.append(
                    Signal.make(
                        user_id=cfg.user_id,
                        source_id=self.source_id,
                        kind=SignalKind.SURVEY,
                        text=text,
                        external_id=f"md:{idx}",
                        entities_hint=hint,
                    )
                )
                idx += 1
                continue

            paragraph.append(line.strip())

        flush_paragraph()
        return signals


def _clean(text: str) -> str:
    """Strip common markdown emphasis/link markup, keeping the readable text."""
    text = _LINK_RE.sub(r"\1", text)
    text = _EMPHASIS_RE.sub("", text)
    return text.strip()
