from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel

from .base import AuthState, FetchResult, SourceConfig
from .registry import register


class TelegramOptions(BaseModel):
    use_private_chats: bool = False
    channel_ids: list[str] = []


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
        return "error"

    def fetch(self, cfg: SourceConfig, auth: AuthState, *, cursor: str | None = None) -> FetchResult:
        return FetchResult(
            signals=[],
            cursor=cursor,
            warnings=["Telegram connector not yet implemented. Run `mp connect-telegram`."],
        )
