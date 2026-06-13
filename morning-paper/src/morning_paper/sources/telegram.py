"""Telegram connector via Telethon (optional dep, imported lazily).

The CLI runs `interactive_login` once to obtain a StringSession, stores it in the
source options, and `fetch` then uses it read-only. Importing this module must
never fail when telethon is absent, so every telethon import is inside a method.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, ClassVar

from pydantic import BaseModel, Field

from ..models import Signal, SignalKind
from .base import AuthState, FetchResult, SourceConfig
from .registry import register


class TelegramOptions(BaseModel):
    use_private_chats: bool = False
    channel_ids: list[str] = Field(default_factory=list)
    session_string: str = ""        # Telethon StringSession; set by the CLI after login
    limit_per_chat: int = 50


async def interactive_login(
    api_id: int,
    api_hash: str,
    *,
    phone: str | None = None,
    code_cb=None,
    password_cb=None,
) -> str:
    """Run Telethon interactive login, return a StringSession string."""
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
    except ImportError as exc:  # optional dep
        raise RuntimeError("pip install 'morning-paper[telegram]'") from exc

    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.start(phone=phone, code_callback=code_cb, password=password_cb)
    session_string = client.session.save()
    await client.disconnect()
    return session_string


@register
class TelegramSource:
    source_id: ClassVar[str] = "telegram"
    display_name: ClassVar[str] = "Telegram"
    requires_auth: ClassVar[bool] = True
    config_schema: ClassVar[type[BaseModel]] = TelegramOptions

    def auth_begin(self, cfg: SourceConfig) -> AuthState:
        return AuthState(source_id=cfg.source_id, user_id=cfg.user_id, status="pending")

    def auth_complete(self, cfg: SourceConfig, payload: dict) -> AuthState:
        raise NotImplementedError("Use CLI: mp connect-telegram")

    def health(self, cfg: SourceConfig, auth: AuthState) -> str:
        opts = TelegramOptions.model_validate(cfg.options)
        return "ok" if opts.session_string else "reauth"

    def fetch(
        self, cfg: SourceConfig, auth: AuthState, *, cursor: str | None = None
    ) -> FetchResult:
        opts = TelegramOptions.model_validate(cfg.options)
        if not opts.session_string:
            return FetchResult(
                signals=[],
                cursor=cursor,
                warnings=["Telegram not connected. Run `mp connect-telegram`."],
            )

        try:
            return _run_async(self._collect(cfg, opts, cursor))
        except Exception as exc:  # never raise out of fetch
            return FetchResult(
                signals=[],
                cursor=cursor,
                warnings=[f"Telegram fetch failed: {exc}"],
            )

    async def _collect(
        self, cfg: SourceConfig, opts: TelegramOptions, cursor: str | None
    ) -> FetchResult:
        import os

        from telethon import TelegramClient
        from telethon.sessions import StringSession

        # A saved StringSession still needs the app's api_id/api_hash to connect;
        # the CLI provides them via env (the schema deliberately holds no secrets).
        api_id = int(os.environ.get("TELEGRAM_API_ID", "0") or "0")
        api_hash = os.environ.get("TELEGRAM_API_HASH", "")

        since = _parse_cursor(cursor)
        latest = since
        signals: list[Signal] = []
        warnings: list[str] = []

        client = TelegramClient(StringSession(opts.session_string), api_id, api_hash)
        await client.connect()
        try:
            if not await client.is_user_authorized():
                return FetchResult(
                    signals=[],
                    cursor=cursor,
                    warnings=["Telegram session expired. Run `mp connect-telegram`."],
                )

            selected: list[Any] = []
            async for dialog in client.iter_dialogs():
                if dialog.is_channel or dialog.is_group:
                    signals.append(
                        Signal.make(
                            user_id=cfg.user_id,
                            source_id=self.source_id,
                            kind=SignalKind.SUBSCRIPTION,
                            text=dialog.name or "",
                            external_id=f"tg:sub:{dialog.id}",
                            entities_hint=[dialog.name] if dialog.name else [],
                        )
                    )
                selected.append(dialog)

            if opts.channel_ids:
                wanted = set(opts.channel_ids)
                targets = [
                    d for d in selected if str(d.id) in wanted or d.name in wanted
                ]
            else:
                targets = [d for d in selected if d.is_channel or d.is_group]

            for dialog in targets:
                is_private = bool(getattr(dialog, "is_user", False))
                is_saved = bool(getattr(dialog, "is_self", False))
                async for msg in client.iter_messages(
                    dialog.entity, limit=opts.limit_per_chat
                ):
                    when = getattr(msg, "date", None)
                    if since and when and when <= since:
                        continue
                    if when and (latest is None or when > latest):
                        latest = when

                    text = (getattr(msg, "message", None) or "").strip()
                    external_id = f"tg:{dialog.id}:{msg.id}"

                    if getattr(msg, "forward", None):
                        signals.append(
                            self._sig(
                                cfg, SignalKind.FORWARD, text, external_id, when,
                                is_private=is_private,
                            )
                        )
                        continue
                    if is_saved:
                        signals.append(
                            self._sig(cfg, SignalKind.SAVE, text, external_id, when)
                        )
                        continue
                    if getattr(msg, "reactions", None):
                        signals.append(
                            self._sig(
                                cfg, SignalKind.REACTION, text, external_id, when,
                                is_private=is_private,
                            )
                        )
                        continue
                    if is_private:
                        if not opts.use_private_chats or not text:
                            continue
                        signals.append(
                            self._sig(
                                cfg, SignalKind.MESSAGE, text, external_id, when,
                                is_private=True,
                            )
                        )
        finally:
            await client.disconnect()

        return FetchResult(
            signals=signals,
            cursor=latest.isoformat() if latest else cursor,
            warnings=warnings,
        )

    def _sig(
        self,
        cfg: SourceConfig,
        kind: SignalKind,
        text: str,
        external_id: str,
        when: datetime | None,
        *,
        is_private: bool = False,
    ) -> Signal:
        kw: dict[str, Any] = {"is_private": is_private}
        if when:
            kw["created_at"] = when
        return Signal.make(
            user_id=cfg.user_id,
            source_id=self.source_id,
            kind=kind,
            text=text,
            external_id=external_id,
            **kw,
        )


def _run_async(coro) -> FetchResult:
    """Run a coroutine even when an event loop is already running in this thread."""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


def _parse_cursor(cursor: str | None) -> datetime | None:
    if not cursor:
        return None
    try:
        return datetime.fromisoformat(cursor)
    except ValueError:
        return None
