"""LocalObjectStore round-trips, stdlib only, no network."""

from __future__ import annotations

from pathlib import Path

from morning_paper.store import LocalObjectStore, get_object_store


def test_put_get_roundtrip(tmp_path):
    store = LocalObjectStore(root=tmp_path)
    uri = store.put("a/b/c.bin", b"hello")
    assert uri.startswith("file://")
    assert store.get("a/b/c.bin") == b"hello"


def test_exists(tmp_path):
    store = LocalObjectStore(root=tmp_path)
    assert store.exists("missing.txt") is False
    store.put("present.txt", b"x")
    assert store.exists("present.txt") is True


def test_put_file(tmp_path):
    src = tmp_path / "src.txt"
    src.write_bytes(b"from file")
    store = LocalObjectStore(root=tmp_path / "store")
    store.put_file("copied.txt", str(src))
    assert store.get("copied.txt") == b"from file"


def test_url_is_file_uri(tmp_path):
    store = LocalObjectStore(root=tmp_path)
    store.put("k.txt", b"v")
    assert store.url("k.txt").startswith("file://")


def test_open_path_is_real_path(tmp_path):
    store = LocalObjectStore(root=tmp_path)
    store.put("nested/k.txt", b"v")
    p = store.open_path("nested/k.txt")
    assert p is not None
    assert Path(p).read_bytes() == b"v"


def test_url_parsing_and_factory(tmp_path):
    root = tmp_path / "objs"
    store = get_object_store(f"file://{root}")
    assert isinstance(store, LocalObjectStore)
    store.put("x.txt", b"y")
    assert store.get("x.txt") == b"y"
    assert Path(store.open_path("x.txt")).exists()
