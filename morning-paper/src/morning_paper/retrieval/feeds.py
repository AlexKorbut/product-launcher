from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from time import mktime
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class Candidate:
    id: str
    title: str
    body: str
    url: str
    lang: str
    source: str
    published_at: str
    score: float = 0.0
    tags: list[str] = field(default_factory=list)


def fetch_rss_candidates(
    feed_urls: list[str],
    *,
    max_per_feed: int = 20,
) -> list[Candidate]:
    """Fetch recent articles from RSS feeds. Returns Candidate list."""
    import feedparser

    candidates: list[Candidate] = []
    for url in feed_urls:
        try:
            parsed = feedparser.parse(url)
            source = parsed.feed.get("title") or url
            for entry in parsed.entries[:max_per_feed]:
                link = entry.get("link") or entry.get("id") or url
                stable_id = hashlib.sha256(link.encode()).hexdigest()[:16]
                title = entry.get("title") or ""
                body = entry.get("summary") or entry.get("description") or ""
                published_at = _entry_iso(entry)
                candidates.append(
                    Candidate(
                        id=stable_id,
                        title=title,
                        body=body,
                        url=link,
                        lang="",
                        source=source,
                        published_at=published_at,
                    )
                )
        except Exception as exc:
            logger.warning("failed to fetch feed %s: %s", url, exc)

    return candidates


def _entry_iso(entry) -> str:
    tm = entry.get("published_parsed") or entry.get("updated_parsed")
    if tm:
        try:
            dt = datetime.fromtimestamp(mktime(tm), tz=timezone.utc)
            return dt.isoformat()
        except Exception:
            pass
    return ""
