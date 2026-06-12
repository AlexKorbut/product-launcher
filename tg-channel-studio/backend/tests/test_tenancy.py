from tests.conftest import auth, signup


async def test_org_isolation(client):
    """Org A must never see org B's channels or posts."""
    tok_a = await signup(client, "a@test.io")
    tok_b = await signup(client, "b@test.io")

    r = await client.post("/api/channels", headers=auth(tok_a), json={
        "name": "A-канал", "username": "a_chan", "bot_token": "1:AAA", "topic": "tech"})
    assert r.status_code == 201, r.text
    chan_a = r.json()["id"]

    # B sees nothing
    r = await client.get("/api/channels", headers=auth(tok_b))
    assert r.json() == []
    # B cannot fetch A's channel by id
    r = await client.get(f"/api/channels/{chan_a}", headers=auth(tok_b))
    assert r.status_code == 404
    # B cannot delete A's channel
    r = await client.delete(f"/api/channels/{chan_a}", headers=auth(tok_b))
    assert r.status_code == 404
    # A still sees it
    r = await client.get("/api/channels", headers=auth(tok_a))
    assert len(r.json()) == 1


async def test_auth_required(client):
    r = await client.get("/api/channels")
    assert r.status_code == 401
    r = await client.get("/api/dashboard")
    assert r.status_code == 401


async def test_signup_grants_welcome_credits(client):
    tok = await signup(client, "fresh@test.io")
    r = await client.get("/api/auth/me", headers=auth(tok))
    assert r.json()["credit_balance"] == 500


async def test_referral_bonus(client):
    tok_ref = await signup(client, "ref@test.io")
    code = (await client.get("/api/auth/me", headers=auth(tok_ref))).json()["referral_code"]
    bal_before = (await client.get("/api/auth/me", headers=auth(tok_ref))).json()["credit_balance"]

    tok_new = await signup(client, "new@test.io", ref=code)
    new_bal = (await client.get("/api/auth/me", headers=auth(tok_new))).json()["credit_balance"]
    ref_bal = (await client.get("/api/auth/me", headers=auth(tok_ref))).json()["credit_balance"]

    assert new_bal == 500 + 300   # welcome + referral
    assert ref_bal == bal_before + 300


async def test_donor_subscription_scoping(client):
    tok = await signup(client, "donor@test.io")
    r = await client.post("/api/channels", headers=auth(tok), json={
        "name": "C", "username": "c_chan", "bot_token": "1:AAA"})
    chan = r.json()["id"]
    r = await client.post("/api/donors", headers=auth(tok), json={
        "username": "https://t.me/some_source", "channel_ids": [chan],
        "filters": {"min_length": 50}})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["username"] == "some_source"
    assert d["channel_ids"] == [chan]
    # duplicate add rejected
    r = await client.post("/api/donors", headers=auth(tok), json={"username": "some_source"})
    assert r.status_code == 409
