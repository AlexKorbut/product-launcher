"""Per-user source configuration — the link between connectors and the pipeline.

Each user enables one or more interest sources (manual, markdown_prefs,
telegram_export, telegram, instagram, rss, ...), each with its own `options`
(file paths, channel ids, a Telethon session string, ...) and an incremental
`cursor`. The pipeline's ingest stage reads this to know what to fetch.

This is intentionally file-backed (JSON under the object-store root) so the whole
product works with zero infrastructure. When a Postgres DB is configured it can be
mirrored there, but nothing here requires it.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .config import PROJECT_ROOT, get_settings


@dataclass
class SourceAccount:
    source_id: str
    enabled: bool = True
    options: dict = field(default_factory=dict)
    cursor: str | None = None
    secret_ref: str | None = None
    status: str = "connected"


@dataclass
class UserAccounts:
    user_id: str
    output_lang: str = "ru"
    theme: str = "times-classic"
    tz: str = "UTC"
    deliver_channel: str = "file"
    sources: dict[str, SourceAccount] = field(default_factory=dict)


def _users_dir() -> Path:
    """Resolve the JSON store dir from the object-store url (file://) or default."""
    url = get_settings().secrets.mp_object_store_url or ""
    if url.startswith("file://"):
        root = Path(url[len("file://") :])
    elif url and "://" not in url:
        root = Path(url)
    else:
        root = PROJECT_ROOT / ".data" / "objects"
    d = root.parent / "users" if root.name == "objects" else root / "users"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _path(user_id: str) -> Path:
    safe = user_id.replace("/", "_")
    return _users_dir() / f"{safe}.json"


def load(user_id: str) -> UserAccounts:
    p = _path(user_id)
    if not p.exists():
        return UserAccounts(user_id=user_id)
    data = json.loads(p.read_text(encoding="utf-8"))
    sources = {
        sid: SourceAccount(source_id=sid, **{k: v for k, v in sa.items() if k != "source_id"})
        for sid, sa in data.get("sources", {}).items()
    }
    return UserAccounts(
        user_id=data["user_id"],
        output_lang=data.get("output_lang", "ru"),
        theme=data.get("theme", "times-classic"),
        tz=data.get("tz", "UTC"),
        deliver_channel=data.get("deliver_channel", "file"),
        sources=sources,
    )


def save(acc: UserAccounts) -> None:
    p = _path(acc.user_id)
    payload = {
        "user_id": acc.user_id,
        "output_lang": acc.output_lang,
        "theme": acc.theme,
        "tz": acc.tz,
        "deliver_channel": acc.deliver_channel,
        "sources": {sid: asdict(sa) for sid, sa in acc.sources.items()},
    }
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def set_source(
    user_id: str,
    source_id: str,
    *,
    options: dict | None = None,
    enabled: bool = True,
    secret_ref: str | None = None,
    merge_options: bool = True,
) -> UserAccounts:
    """Create/update one source's config for a user and persist."""
    acc = load(user_id)
    existing = acc.sources.get(source_id)
    new_options = dict(existing.options) if (existing and merge_options) else {}
    if options:
        new_options.update(options)
    acc.sources[source_id] = SourceAccount(
        source_id=source_id,
        enabled=enabled,
        options=new_options,
        cursor=existing.cursor if existing else None,
        secret_ref=secret_ref if secret_ref is not None else (existing.secret_ref if existing else None),
        status="connected",
    )
    save(acc)
    return acc


def update_cursor(user_id: str, source_id: str, cursor: str | None) -> None:
    acc = load(user_id)
    sa = acc.sources.get(source_id)
    if sa is None:
        return
    sa.cursor = cursor
    save(acc)


def enabled_sources(user_id: str) -> list[SourceAccount]:
    return [sa for sa in load(user_id).sources.values() if sa.enabled]
