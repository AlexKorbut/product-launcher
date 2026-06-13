from __future__ import annotations

import shutil

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from morning_paper.api.app import create_app
from morning_paper.config import RENDERER_DIR
from morning_paper.sample import sample_render_document
from morning_paper.store import get_object_store

node_missing = shutil.which("node") is None
deps_missing = not (RENDERER_DIR / "node_modules").exists()

pytestmark = pytest.mark.skipif(
    node_missing or deps_missing,
    reason="Node and renderer deps required (run `make install-node`)",
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_render_document(client: TestClient):
    doc = sample_render_document("times-classic").model_dump(mode="json")
    resp = client.post("/v1/render", json={"document": doc})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["pdf_url"]
    assert body["page_count"] is None or body["page_count"] >= 1

    # The stored PDF must exist in the object store.
    url = body["pdf_url"]
    key = url.split("renders/", 1)[1]
    key = "renders/" + key
    store = get_object_store()
    assert store.open_path(key) is not None or store.exists(key)
