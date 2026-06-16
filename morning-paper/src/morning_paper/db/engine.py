"""Engine / session factory. SQLAlchemy imported lazily."""

from __future__ import annotations

from typing import Any

_ENGINES: dict[str, Any] = {}


def _has_pgvector() -> bool:
    try:
        import pgvector  # noqa: F401

        return True
    except ImportError:
        return False


HAS_PGVECTOR = _has_pgvector()


def _resolve_url(url: str | None) -> str:
    if url is not None:
        return url
    from ..config import PROJECT_ROOT, get_settings

    configured = get_settings().secrets.mp_db_url
    if configured:
        return configured
    data_dir = PROJECT_ROOT / ".data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{data_dir / 'morning_paper.db'}"


def get_engine(url: str | None = None):
    """Return a cached SQLAlchemy engine for the resolved url."""
    from sqlalchemy import create_engine  # lazy

    resolved = _resolve_url(url)
    if resolved not in _ENGINES:
        _ENGINES[resolved] = create_engine(resolved, future=True)
    return _ENGINES[resolved]


def get_session(url: str | None = None, *, engine=None):
    """Return a new Session bound to the given (or resolved) engine."""
    from sqlalchemy.orm import sessionmaker  # lazy

    if engine is None:
        engine = get_engine(url)
    return sessionmaker(bind=engine, future=True)()
