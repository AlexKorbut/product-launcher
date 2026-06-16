"""Telegram Desktop export source. Auth-free; parses the `result.json` a user gets
from "Export chat history" / "Export Telegram data" (full export or single chat).
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, ClassVar

from pydantic import BaseModel

from ..models import Signal, SignalKind
from .base import AuthFreeSource, AuthState, FetchResult, SourceConfig
from .registry import register

_PRIVATE_TYPES = {"personal_chat", "private_group", "private_supergroup", "bot_chat"}
_PUBLIC_TYPES = {"public_channel", "public_supergroup"}
_MAX_MESSAGES_PER_CHAT = 500


class TelegramExportOptions(BaseModel):
    path: str = ""                 # path to result.json (full or single-chat export)
    include_private: bool = False  # include personal/private chat message bodies


@register
class TelegramExportSource(AuthFreeSource):
    source_id: ClassVar[str] = "telegram_export"
    display_name: ClassVar[str] = "Telegram export (JSON)"
    config_schema: ClassVar[type[BaseModel]] = TelegramExportOptions

    def fetch(
        self, cfg: SourceConfig, auth: AuthState, *, cursor: str | None
    ) -> FetchResult:
        opts = TelegramExportOptions.model_validate(cfg.options)
        warnings: list[str] = []

        if not opts.path or not os.path.isfile(opts.path):
            warnings.append(f"telegram_export: no file at {opts.path!r}")
            return FetchResult(signals=[], cursor=cursor, warnings=warnings)

        try:
            with open(opts.path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            warnings.append(f"telegram_export: could not parse {opts.path}: {exc}")
            return FetchResult(signals=[], cursor=cursor, warnings=warnings)

        since = _parse_cursor(cursor)
        latest = since
        signals: list[Signal] = []

        for chat in _iter_chats(data):
            try:
                chat_signals, chat_latest = self._parse_chat(
                    chat, cfg, opts, since, warnings
                )
            except Exception as exc:  # defensive: one bad chat must not abort the rest
                warnings.append(f"telegram_export: skipped a chat: {exc}")
                continue
            signals.extend(chat_signals)
            if chat_latest and (latest is None or chat_latest > latest):
                latest = chat_latest

        return FetchResult(
            signals=signals,
            cursor=latest.isoformat() if latest else cursor,
            warnings=warnings,
        )

    def _parse_chat(
        self,
        chat: dict[str, Any],
        cfg: SourceConfig,
        opts: TelegramExportOptions,
        since: datetime | None,
        warnings: list[str],
    ) -> tuple[list[Signal], datetime | None]:
        signals: list[Signal] = []
        chat_type = chat.get("type") or ""
        name = chat.get("name") or chat.get("title") or ""
        chat_id = chat.get("id", name)
        is_private = chat_type in _PRIVATE_TYPES
        is_saved = chat_type == "saved_messages"
        latest: datetime | None = None

        if chat_type in _PUBLIC_TYPES and name:
            signals.append(
                Signal.make(
                    user_id=cfg.user_id,
                    source_id=self.source_id,
                    kind=SignalKind.SUBSCRIPTION,
                    text=name,
                    external_id=f"tgx:sub:{chat_id}",
                    entities_hint=[name],
                )
            )

        messages = chat.get("messages")
        if not isinstance(messages, list):
            return signals, latest

        for msg in messages[-_MAX_MESSAGES_PER_CHAT:]:
            if not isinstance(msg, dict) or msg.get("type") != "message":
                continue

            when = _parse_msg_date(msg)
            if since and when and when <= since:
                continue
            if when and (latest is None or when > latest):
                latest = when

            text = _flatten_text(msg.get("text"))
            forwarded_from = msg.get("forwarded_from")
            msg_id = msg.get("id", "")
            external_id = f"tgx:{chat_id}:{msg_id}"

            if forwarded_from:
                hint = [forwarded_from] if isinstance(forwarded_from, str) else []
                signals.append(
                    self._make(
                        cfg,
                        SignalKind.FORWARD,
                        text,
                        external_id,
                        when,
                        is_private=is_private,
                        entities_hint=hint,
                    )
                )
                continue

            if not text:
                continue

            if is_saved:
                signals.append(
                    self._make(cfg, SignalKind.SAVE, text, external_id, when)
                )
                continue

            if is_private:
                if not opts.include_private:
                    continue
                signals.append(
                    self._make(
                        cfg, SignalKind.MESSAGE, text, external_id, when, is_private=True
                    )
                )
                continue

            signals.append(self._make(cfg, SignalKind.MESSAGE, text, external_id, when))

        return signals, latest

    def _make(
        self,
        cfg: SourceConfig,
        kind: SignalKind,
        text: str,
        external_id: str,
        when: datetime | None,
        *,
        is_private: bool = False,
        entities_hint: list[str] | None = None,
    ) -> Signal:
        kw: dict[str, Any] = {"is_private": is_private}
        if when:
            kw["created_at"] = when
        if entities_hint:
            kw["entities_hint"] = entities_hint
        return Signal.make(
            user_id=cfg.user_id,
            source_id=self.source_id,
            kind=kind,
            text=text,
            external_id=external_id,
            **kw,
        )


def _iter_chats(data: Any):
    """Yield chat dicts from either a full export or a single-chat export."""
    if not isinstance(data, dict):
        return
    # Single-chat export: the top-level object is itself a chat.
    if "messages" in data and "type" in data:
        yield data
        return
    chats = (data.get("chats") or {}).get("list")
    if isinstance(chats, list):
        yield from (c for c in chats if isinstance(c, dict))
    left = (data.get("left_chats") or {}).get("list")
    if isinstance(left, list):
        yield from (c for c in left if isinstance(c, dict))


def _flatten_text(text: Any) -> str:
    """Telegram `text` is a string OR a list of (string | {"text": "..."}) parts."""
    if isinstance(text, str):
        return text.strip()
    if isinstance(text, list):
        parts: list[str] = []
        for part in text:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                piece = part.get("text")
                if isinstance(piece, str):
                    parts.append(piece)
        return "".join(parts).strip()
    return ""


def _parse_msg_date(msg: dict[str, Any]) -> datetime | None:
    unixtime = msg.get("date_unixtime")
    if unixtime is not None:
        try:
            return datetime.fromtimestamp(int(unixtime))
        except (ValueError, TypeError, OSError):
            pass
    raw = msg.get("date")
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return None
    return None


def _parse_cursor(cursor: str | None) -> datetime | None:
    if not cursor:
        return None
    try:
        return datetime.fromisoformat(cursor)
    except ValueError:
        return None
