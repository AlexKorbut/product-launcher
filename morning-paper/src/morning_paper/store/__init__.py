"""Pluggable object store: local filesystem or S3."""

from __future__ import annotations

from .base import ObjectStore
from .local import LocalObjectStore
from .s3 import S3ObjectStore


def get_object_store(url: str | None = None) -> ObjectStore:
    """Resolve an ObjectStore from a url (or settings if None).

    s3://... -> S3ObjectStore; file://... or bare path -> LocalObjectStore.
    """
    if url is None:
        from ..config import get_settings

        url = get_settings().secrets.mp_object_store_url
    if url.startswith("s3://"):
        return S3ObjectStore(url)
    return LocalObjectStore(url)


__all__ = [
    "ObjectStore",
    "LocalObjectStore",
    "S3ObjectStore",
    "get_object_store",
]
