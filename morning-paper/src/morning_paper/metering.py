"""Best-effort cost/usage metering. A metering failure must NEVER break an issue."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .economics import UsageEvent, cost_of
from .llm.client import AnthropicClient


@runtime_checkable
class UsageSink(Protocol):
    def record(self, event: UsageEvent) -> None: ...


class NullUsageSink:
    """Discards every event."""

    def record(self, event: UsageEvent) -> None:
        return None


class ListUsageSink:
    """Collects events in memory (handy for tests)."""

    def __init__(self) -> None:
        self.events: list[UsageEvent] = []

    def record(self, event: UsageEvent) -> None:
        self.events.append(event)


class DBUsageSink:
    """Persists events via the repository, swallowing all errors."""

    def __init__(self, *, url=None, engine=None) -> None:
        self._url = url
        self._engine = engine

    def record(self, event: UsageEvent) -> None:
        try:
            from .db.repository import record_usage

            record_usage(
                user_id=event.user_id,
                issue_id=event.issue_id,
                stage=event.stage,
                model=event.model,
                tokens_in=event.tokens_in,
                tokens_out=event.tokens_out,
                cached_in=event.cached_in,
                batch=event.batch,
                cost_usd=event.cost_usd,
                url=self._url,
                engine=self._engine,
            )
        except Exception:
            pass


class MeteredClient(AnthropicClient):
    """AnthropicClient that records token usage for each call to a sink."""

    def __init__(
        self,
        *,
        user_id: str,
        issue_id: str | None,
        stage: str,
        sink: UsageSink,
        api_key: str | None = None,
    ) -> None:
        super().__init__(api_key)
        self.user_id = user_id
        self.issue_id = issue_id
        self.stage = stage
        self.sink = sink

    def _create(self, **kwargs):
        resp = super()._create(**kwargs)
        try:
            usage = getattr(resp, "usage", None)
            if usage is not None:
                tin = getattr(usage, "input_tokens", 0) or 0
                tout = getattr(usage, "output_tokens", 0) or 0
                cin = getattr(usage, "cache_read_input_tokens", 0) or 0
                model = kwargs.get("model") or getattr(resp, "model", "")
                cost = cost_of(model, tin, tout, cached_in=cin)
                self.sink.record(
                    UsageEvent(
                        self.user_id,
                        self.issue_id,
                        self.stage,
                        model,
                        tin,
                        tout,
                        cin,
                        False,
                        cost,
                    )
                )
        except Exception:
            pass
        return resp

    def with_stage(self, stage: str) -> "MeteredClient":
        """New MeteredClient sharing user/issue/sink but a different stage."""
        new = MeteredClient(
            user_id=self.user_id,
            issue_id=self.issue_id,
            stage=stage,
            sink=self.sink,
        )
        new._client = self._client
        return new


def default_sink() -> UsageSink:
    try:
        import sqlalchemy  # noqa: F401

        return DBUsageSink()
    except Exception:
        return NullUsageSink()


def metered_client(
    user_id: str,
    issue_id: str | None,
    stage: str,
    *,
    sink: UsageSink | None = None,
) -> MeteredClient:
    if sink is None:
        sink = default_sink()
    from .config import get_settings

    api_key = get_settings().secrets.anthropic_api_key
    return MeteredClient(
        user_id=user_id,
        issue_id=issue_id,
        stage=stage,
        sink=sink,
        api_key=api_key,
    )
