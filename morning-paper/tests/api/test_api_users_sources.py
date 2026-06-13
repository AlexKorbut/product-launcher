from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from morning_paper.api.app import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_user_update_roundtrip(client: TestClient):
    resp = client.put("/v1/users/demo", json={"theme": "times-classic", "output_lang": "en"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["theme"] == "times-classic"
    assert body["output_lang"] == "en"

    got = client.get("/v1/users/demo")
    assert got.status_code == 200
    assert got.json()["output_lang"] == "en"
    assert got.json()["theme"] == "times-classic"


def test_source_config_roundtrip(client: TestClient):
    resp = client.put(
        "/v1/users/demo/sources/manual", json={"options": {"free_text": "AI"}}
    )
    assert resp.status_code == 200

    got = client.get("/v1/users/demo/sources/manual")
    assert got.status_code == 200
    assert got.json()["enabled"] is True


def test_secret_options_redacted(client: TestClient):
    resp = client.put(
        "/v1/users/demo/sources/telegram",
        json={"options": {"session_string": "SECRET", "use_private_chats": True}},
    )
    assert resp.status_code == 200

    got = client.get("/v1/users/demo/sources/telegram")
    assert got.status_code == 200
    options = got.json()["options"]
    assert "session_string" not in options
    assert "SECRET" not in str(options)
    # non-secret options survive
    assert options.get("use_private_chats") is True
