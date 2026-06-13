"""Object store protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ObjectStore(Protocol):
    """Pluggable blob store (local filesystem or S3-compatible)."""

    def put(self, key: str, data: bytes, *, content_type: str | None = None) -> str: ...
    def put_file(self, key: str, path: str, *, content_type: str | None = None) -> str: ...
    def get(self, key: str) -> bytes: ...
    def exists(self, key: str) -> bool: ...
    def url(self, key: str) -> str:
        """A resolvable URI (file:// or s3://...)."""
        ...

    def open_path(self, key: str) -> str | None:
        """Local filesystem path if available, else None."""
        ...
