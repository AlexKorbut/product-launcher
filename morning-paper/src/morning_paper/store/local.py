"""Local filesystem object store (stdlib only)."""

from __future__ import annotations

import shutil
from pathlib import Path


class LocalObjectStore:
    """Store blobs under a root directory. Keys may contain '/' for nesting."""

    def __init__(self, url: str | None = None, *, root: str | Path | None = None) -> None:
        if root is not None:
            self.root = Path(root)
        elif url is not None:
            self.root = _root_from_url(url)
        else:
            from ..config import PROJECT_ROOT

            self.root = PROJECT_ROOT / ".data" / "objects"
        self.root = self.root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.root / key

    def put(self, key: str, data: bytes, *, content_type: str | None = None) -> str:
        dest = self._path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return self.url(key)

    def put_file(self, key: str, path: str, *, content_type: str | None = None) -> str:
        dest = self._path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
        return self.url(key)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def url(self, key: str) -> str:
        return self._path(key).resolve().as_uri()

    def open_path(self, key: str) -> str | None:
        return str(self._path(key).resolve())


def _root_from_url(url: str) -> Path:
    """Parse a file:// URL or bare path into a root directory."""
    if url.startswith("file://"):
        rest = url[len("file://"):]
        # file://./.data -> "./.data"; file:///abs -> "/abs"
        return Path(rest)
    return Path(url)
