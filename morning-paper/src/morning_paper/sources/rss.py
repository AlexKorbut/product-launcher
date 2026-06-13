"""RSS / newsletter source. Auth-free, incremental via a per-run timestamp cursor."""

from __future__ import annotations

from datetime import datetime, timezone
from time import mktime
from typing import ClassVar

from pydantic import BaseModel, Field

from ..models import Signal, SignalKind
from .base import AuthFreeSource, AuthState, FetchResult, SourceConfig
from .registry import register


class RssOptions(BaseModel):
    feeds: list[str] = Field(default_factory=list)  # feed URLs the user reads
    max_items_per_feed: int = 50


@register
class RssSource(AuthFreeSource):
    source_id: ClassVar[str] = "rss"
    display_name: ClassVar[str] = "RSS / newsletters"
    config_schema: ClassVar[type[BaseModel]] = RssOptions

    def fetch(
        self, cfg: SourceConfig, auth: AuthState, *, cursor: str | None
    ) -> FetchResult:
        import feedparser  # imported lazily so the package loads without the dep

        opts = RssOptions.model_validate(cfg.options)
        since = _parse_cursor(cursor)
        latest = since
        signals: list[Signal] = []
        warnings: list[str] = []

        for url in opts.feeds:
            parsed = feedparser.parse(url)
            if getattr(parsed, "bozo", False):
                warnings.append(f"feed parse issue: {url}")
            for entry in parsed.entries[: opts.max_items_per_feed]:
                published = _entry_dt(entry)
                if since and published and published <= since:
                    continue
                if published and (latest is None or published > latest):
                    latest = published
                text = " ".join(
                    p for p in (entry.get("title"), entry.get("summary")) if p
                ).strip()
                if not text:
                    continue
                signals.append(
                    Signal.make(
                        user_id=cfg.user_id,
                        source_id=self.source_id,
                        kind=SignalKind.READ,
                        text=text,
                        external_id=entry.get("id") or entry.get("link") or text,
                        created_at=published or datetime.now(timezone.utc),
                    )
                )

        return FetchResult(
            signals=signals,
            cursor=latest.isoformat() if latest else cursor,
            warnings=warnings,
        )


def _parse_cursor(cursor: str | None) -> datetime | None:
    if not cursor:
        return None
    try:
        return datetime.fromisoformat(cursor)
    except ValueError:
        return None


def _entry_dt(entry) -> datetime | None:
    tm = entry.get("published_parsed") or entry.get("updated_parsed")
    if not tm:
        return None
    return datetime.fromtimestamp(mktime(tm), tz=timezone.utc)
