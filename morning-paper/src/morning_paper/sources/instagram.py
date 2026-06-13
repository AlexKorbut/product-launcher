"""Instagram connector. Parses an offline "Download Your Information" export
(JSON). A Graph API hook exists but Graph is heavily restricted, so the export is
the documented path. `requires_auth` stays True because the user must log in to
Instagram to request the export.
"""

from __future__ import annotations

import json
import os
from typing import Any, ClassVar

from pydantic import BaseModel

from ..models import Signal, SignalKind
from .base import AuthState, FetchResult, SourceConfig
from .registry import register


class InstagramOptions(BaseModel):
    export_dir: str = ""     # unzipped "Download Your Information" folder
    access_token: str = ""   # optional Graph API token (not required)


# (filename substring, SignalKind) — matched against any JSON file under export_dir.
_FILE_KINDS: list[tuple[str, SignalKind]] = [
    ("following", SignalKind.SUBSCRIPTION),
    ("saved_posts", SignalKind.SAVE),
    ("your_topics", SignalKind.SURVEY),
    ("recommended_topics", SignalKind.FREE_TEXT),
    ("liked_posts", SignalKind.REACTION),
]


@register
class InstagramSource:
    source_id: ClassVar[str] = "instagram"
    display_name: ClassVar[str] = "Instagram"
    requires_auth: ClassVar[bool] = True
    config_schema: ClassVar[type[BaseModel]] = InstagramOptions

    def auth_begin(self, cfg: SourceConfig) -> AuthState:
        return AuthState(source_id=cfg.source_id, user_id=cfg.user_id, status="pending")

    def auth_complete(self, cfg: SourceConfig, payload: dict) -> AuthState:
        raise NotImplementedError

    def health(self, cfg: SourceConfig, auth: AuthState) -> str:
        opts = InstagramOptions.model_validate(cfg.options)
        return "ok" if (opts.export_dir or opts.access_token) else "reauth"

    def fetch(
        self, cfg: SourceConfig, auth: AuthState, *, cursor: str | None = None
    ) -> FetchResult:
        opts = InstagramOptions.model_validate(cfg.options)
        warnings: list[str] = []
        signals: list[Signal] = []

        if opts.export_dir and os.path.isdir(opts.export_dir):
            for path in _iter_json_files(opts.export_dir):
                kind = _kind_for(os.path.basename(path))
                if kind is None:
                    continue
                try:
                    with open(path, encoding="utf-8") as fh:
                        data = json.load(fh)
                except (OSError, ValueError) as exc:
                    warnings.append(f"instagram: could not parse {path}: {exc}")
                    continue
                for value in _extract_values(data):
                    signals.append(
                        Signal.make(
                            user_id=cfg.user_id,
                            source_id=self.source_id,
                            kind=kind,
                            text=value,
                            external_id=f"ig:{kind.value}:{value}",
                            entities_hint=[value],
                        )
                    )
            if not signals and not warnings:
                warnings.append("instagram: no recognized export files found")
            return FetchResult(signals=signals, cursor=cursor, warnings=warnings)

        if opts.access_token:
            warnings.append(
                "Instagram Graph API not yet wired; use the data export."
            )
            return FetchResult(signals=[], cursor=cursor, warnings=warnings)

        warnings.append("instagram: set `export_dir` to the unzipped data export")
        return FetchResult(signals=[], cursor=cursor, warnings=warnings)


def _iter_json_files(root: str):
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if name.lower().endswith(".json"):
                yield os.path.join(dirpath, name)


def _kind_for(filename: str) -> SignalKind | None:
    low = filename.lower()
    for needle, kind in _FILE_KINDS:
        if needle in low:
            return kind
    return None


def _extract_values(data: Any) -> list[str]:
    """Pull `value` strings out of IG's nested string_map_data/string_list_data shape.

    The export wraps entries as e.g.
        {"string_list_data": [{"value": "acct", "href": "...", "timestamp": 1}]}
    or {"string_map_data": {"Name": {"value": "..."}}}. We walk recursively and
    collect every "value" string we find, deduping while preserving order.
    """
    found: list[str] = []
    seen: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            val = node.get("value")
            if isinstance(val, str) and val.strip():
                v = val.strip()
                if v not in seen:
                    seen.add(v)
                    found.append(v)
            for child in node.values():
                if isinstance(child, (dict, list)):
                    walk(child)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    return found
