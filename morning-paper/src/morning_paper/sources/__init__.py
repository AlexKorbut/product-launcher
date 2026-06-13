"""Interest sources package.

Importing the package self-registers the built-in sources so the registry is
populated without callers having to import each module.
"""

from . import manual, rss, telegram, instagram  # noqa: F401  (import side effect: registration)
from .base import (
    AuthState,
    FetchResult,
    HealthStatus,
    InterestSource,
    SourceConfig,
)
from .registry import all_source_ids, all_sources, get_source, register

__all__ = [
    "AuthState",
    "FetchResult",
    "HealthStatus",
    "InterestSource",
    "SourceConfig",
    "all_source_ids",
    "all_sources",
    "get_source",
    "register",
]
