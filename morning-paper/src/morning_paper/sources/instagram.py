from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel

from .base import AuthState, FetchResult, SourceConfig
from .registry import register


class InstagramOptions(BaseModel):
    access_token: str = ""


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
        return "error"

    def fetch(self, cfg: SourceConfig, auth: AuthState, *, cursor: str | None = None) -> FetchResult:
        return FetchResult(
            signals=[],
            cursor=cursor,
            warnings=["Instagram connector not yet implemented."],
        )
