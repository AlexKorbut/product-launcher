
from app.db import SessionLocal
from app.services import billing, credits
from app.services.dedup import content_hash, looks_like_ad, passes_filters
from app.services.schedule import next_slot
from app.models import Channel
from datetime import datetime, timezone
from tests.conftest import auth, signup


async def _org_id(client, token) -> int:
    return (await client.get("/api/auth/me", headers=auth(token))).json()["org_id"]


async def test_credit_debit_and_gate(client):
    tok = await signup(client, "credit@test.io")
    org_id = await _org_id(client, tok)
    async with SessionLocal() as s:
        assert await credits.get_balance(s, org_id) == 500
        await credits.debit(s, org_id, 200, ref="post:1")
        await s.commit()
        assert await credits.get_balance(s, org_id) == 300
        # drain to zero
        await credits.debit(s, org_id, 300, ref="post:2")
        await s.commit()
        assert await credits.get_balance(s, org_id) == 0

    # generation blocked at zero balance (402)
    r = await client.post("/api/channels", headers=auth(tok), json={
        "name": "C", "username": "c_chan", "bot_token": "1:AAA"})
    chan = r.json()["id"]
    r = await client.post("/api/posts/generate", headers=auth(tok), json={"channel_id": chan})
    assert r.status_code == 402, r.text


async def test_stripe_webhook_idempotent(client, monkeypatch):
    tok = await signup(client, "pay@test.io")
    org_id = await _org_id(client, tok)

    fake_event = {
        "id": "evt_123",
        "type": "checkout.session.completed",
        "data": {"object": {
            "metadata": {"org_id": str(org_id), "price_id": "price_test"},
            "customer": "cus_1",
        }},
    }
    monkeypatch.setattr(billing, "verify_webhook", lambda payload, sig: fake_event)

    r = await client.post("/api/billing/webhook", content=b"{}",
                          headers={"stripe-signature": "t"})
    assert r.json()["granted"] is True
    bal = (await client.get("/api/billing/balance", headers=auth(tok))).json()["credit_balance"]
    assert bal == 500 + 1000

    # replay same event -> no double grant
    r = await client.post("/api/billing/webhook", content=b"{}",
                          headers={"stripe-signature": "t"})
    assert r.json()["granted"] is False
    bal2 = (await client.get("/api/billing/balance", headers=auth(tok))).json()["credit_balance"]
    assert bal2 == 1500


async def test_ledger_records_movements(client):
    tok = await signup(client, "ledger@test.io")
    r = await client.get("/api/billing/ledger", headers=auth(tok))
    kinds = [row["kind"] for row in r.json()]
    assert "bonus" in kinds  # welcome credits recorded


def test_filters_and_dedup():
    assert content_hash("Привет,  мир!") == content_hash("привет мир")
    assert looks_like_ad("Промокод STUDIO даёт скидку")
    ok, _ = passes_filters("short", {}, {"min_length": 100})
    assert not ok
    ok, _ = passes_filters("x" * 200, {}, {"min_length": 100, "exclude_keywords": ["казино"]})
    assert ok


def test_schedule_avoids_quiet_hours():
    ch = Channel(name="t", username="t", bot_token_encrypted="", posts_per_day=4,
                 quiet_hours_start=23, quiet_hours_end=8, tz_offset_minutes=180)
    slot = next_slot(ch, after=datetime(2026, 6, 12, 12, 0, tzinfo=timezone.utc))
    local_hour = (slot.hour + 3) % 24
    assert not (local_hour >= 23 or local_hour < 8)
