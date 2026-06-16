from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from morning_paper.api.app import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_themes(client: TestClient):
    resp = client.get("/v1/themes")
    assert resp.status_code == 200
    data = resp.json()
    assert data, "expected at least one theme"
    for item in data:
        assert "id" in item
        assert "display_name" in item
        assert "colors" in item
        assert "fonts" not in item  # privacy: no font files/licenses leaked


def test_sources(client: TestClient):
    resp = client.get("/v1/sources")
    assert resp.status_code == 200
    data = resp.json()
    ids = {s["source_id"] for s in data}
    assert "manual" in ids
    for s in data:
        assert isinstance(s["config_schema"], dict)
