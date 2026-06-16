"""Source discovery: a decorator registry plus entry-point scanning.

Built-in sources self-register on import (see this package's __init__). External
connectors can ship as separate packages exposing the `morning_paper.sources`
entry-point group.
"""

from __future__ import annotations

from importlib import metadata
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import InterestSource

_REGISTRY: dict[str, type] = {}
_ENTRYPOINTS_LOADED = False


def register(cls: type) -> type:
    """Class decorator: register a source by its `source_id` class attribute."""
    source_id = getattr(cls, "source_id", None)
    if not source_id:
        raise ValueError(f"{cls.__name__} is missing a `source_id` class attribute")
    if source_id in _REGISTRY and _REGISTRY[source_id] is not cls:
        raise ValueError(f"duplicate source_id {source_id!r}")
    _REGISTRY[source_id] = cls
    return cls


def _load_entrypoints() -> None:
    global _ENTRYPOINTS_LOADED
    if _ENTRYPOINTS_LOADED:
        return
    _ENTRYPOINTS_LOADED = True
    try:
        eps = metadata.entry_points(group="morning_paper.sources")
    except Exception:
        return
    for ep in eps:
        try:
            register(ep.load())
        except Exception:
            # A broken third-party plugin must not take down discovery.
            continue


def get_source(source_id: str) -> "InterestSource":
    _load_entrypoints()
    cls = _REGISTRY.get(source_id)
    if cls is None:
        raise KeyError(f"unknown source {source_id!r}; known: {sorted(_REGISTRY)}")
    return cls()


def all_source_ids() -> list[str]:
    _load_entrypoints()
    return sorted(_REGISTRY)


def all_sources() -> list[type]:
    """Source classes, for building the onboarding UI."""
    _load_entrypoints()
    return list(_REGISTRY.values())
