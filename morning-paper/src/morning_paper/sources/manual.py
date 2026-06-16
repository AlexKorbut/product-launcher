"""Manual source — the zero-config default that works with NO social login.

The user types their interests in prose ("why I follow X") and/or picks topics in
onboarding. This turns those into Signals exactly like any other source, so the
profile builder treats a no-login user identically to a connected one. Solves the
cold-start problem (docs/03).
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, Field

from ..models import Signal, SignalKind
from .base import AuthFreeSource, AuthState, FetchResult, SourceConfig
from .registry import register


class ManualOptions(BaseModel):
    free_text: str = ""                       # prose: "I care about X because..."
    survey_topics: list[str] = Field(default_factory=list)  # taxonomy paths chosen in onboarding


@register
class ManualSource(AuthFreeSource):
    source_id: ClassVar[str] = "manual"
    display_name: ClassVar[str] = "Manual interests"
    config_schema: ClassVar[type[BaseModel]] = ManualOptions

    def fetch(
        self, cfg: SourceConfig, auth: AuthState, *, cursor: str | None
    ) -> FetchResult:
        opts = ManualOptions.model_validate(cfg.options)
        signals: list[Signal] = []

        if opts.free_text.strip():
            signals.append(
                Signal.make(
                    user_id=cfg.user_id,
                    source_id=self.source_id,
                    kind=SignalKind.FREE_TEXT,
                    text=opts.free_text.strip(),
                    external_id="free_text",
                )
            )

        for topic in opts.survey_topics:
            signals.append(
                Signal.make(
                    user_id=cfg.user_id,
                    source_id=self.source_id,
                    kind=SignalKind.SURVEY,
                    text=topic,
                    external_id=f"survey:{topic}",
                    entities_hint=[topic],
                )
            )

        # Manual entry is stateless; no incremental cursor.
        return FetchResult(signals=signals, cursor=None)
