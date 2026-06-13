"""Shared test fixtures. `pythonpath=["src"]` (pyproject) makes morning_paper importable."""

from __future__ import annotations

import pytest

from morning_paper.config import get_settings


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path, monkeypatch):
    """Point the object store and DB at a per-test tmp dir so file-backed state
    (accounts, .data, sqlite) never leaks between tests or into the real repo.

    `get_settings()` is `@lru_cache`d, so we clear it around the env change.
    """
    monkeypatch.setenv("MP_OBJECT_STORE_URL", f"file://{tmp_path}/objects")
    monkeypatch.setenv("MP_DB_URL", f"sqlite:///{tmp_path}/mp.db")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
