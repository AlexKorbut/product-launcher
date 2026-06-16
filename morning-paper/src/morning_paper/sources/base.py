"""The InterestSource plugin contract.

The pipeline depends only on this Protocol — never on a concrete connector — so a
new source is added by writing a module and registering it, with zero pipeline
edits. Auth-free sources (manual, rss) implement the auth_* methods trivially.
"""

from __future__ import annotations

from typing import Any, ClassVar, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from ..models import Signal

AuthStatus = Literal["none", "pending", "connected", "expired", "error"]
HealthStatus = Literal["ok", "reauth", "error"]


class SourceConfig(BaseModel):
    """Per-user, per-source configuration (no secrets — those live behind AuthState)."""

    source_id: str
    user_id: str
    enabled: bool = True
    options: dict[str, Any] = Field(default_factory=dict)


class AuthState(BaseModel):
    """Connection state for a source. The actual secret lives in an encrypted
    store; only a pointer (`secret_ref`) is kept here."""

    source_id: str
    user_id: str
    status: AuthStatus = "none"
    secret_ref: str | None = None


class FetchResult(BaseModel):
    signals: list[Signal] = Field(default_factory=list)
    cursor: str | None = None       # opaque resume token persisted for the next run
    warnings: list[str] = Field(default_factory=list)


@runtime_checkable
class InterestSource(Protocol):
    """Implemented by every connector. Class attrs describe the source; instance
    methods drive auth and the nightly incremental fetch."""

    source_id: ClassVar[str]
    display_name: ClassVar[str]
    requires_auth: ClassVar[bool]
    config_schema: ClassVar[type[BaseModel]]

    def auth_begin(self, cfg: SourceConfig) -> AuthState: ...

    def auth_complete(self, cfg: SourceConfig, payload: dict) -> AuthState: ...

    def health(self, cfg: SourceConfig, auth: AuthState) -> HealthStatus: ...

    def fetch(
        self, cfg: SourceConfig, auth: AuthState, *, cursor: str | None
    ) -> FetchResult: ...


class AuthFreeSource:
    """Mixin giving no-op auth for sources that need no login (manual, rss)."""

    requires_auth: ClassVar[bool] = False

    def auth_begin(self, cfg: SourceConfig) -> AuthState:
        return AuthState(source_id=cfg.source_id, user_id=cfg.user_id, status="connected")

    def auth_complete(self, cfg: SourceConfig, payload: dict) -> AuthState:
        return AuthState(source_id=cfg.source_id, user_id=cfg.user_id, status="connected")

    def health(self, cfg: SourceConfig, auth: AuthState) -> HealthStatus:
        return "ok"
