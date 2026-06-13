"""Persistence layer: Postgres+pgvector (or SQLite for dev) via SQLAlchemy."""

from __future__ import annotations

from .engine import HAS_PGVECTOR, get_engine, get_session
from .repository import (
    get_source_accounts,
    init_db,
    load_profile,
    record_issue,
    save_profile,
    save_signals,
    update_cursor,
    upsert_source_account,
    upsert_user,
)

__all__ = [
    "HAS_PGVECTOR",
    "get_engine",
    "get_session",
    "init_db",
    "upsert_user",
    "get_source_accounts",
    "upsert_source_account",
    "update_cursor",
    "save_signals",
    "save_profile",
    "load_profile",
    "record_issue",
]
