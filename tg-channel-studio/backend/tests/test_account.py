from app.security import create_purpose_token
from tests.conftest import auth, signup


async def test_email_verification_flow(client):
    tok = await signup(client, "verify@test.io")
    me = (await client.get("/api/auth/me", headers=auth(tok))).json()
    assert me["email_verified"] is False
    assert me["role"] == "owner"

    r = await client.post("/api/auth/request-verify", headers=auth(tok))
    assert r.json()["sent"] is True

    # forge a valid token (in real flow it arrives by email)
    vtoken = create_purpose_token(me["user_id"], "verify")
    r = await client.post("/api/auth/verify", json={"token": vtoken})
    assert r.json()["verified"] is True

    me2 = (await client.get("/api/auth/me", headers=auth(tok))).json()
    assert me2["email_verified"] is True


async def test_verify_rejects_wrong_purpose(client):
    tok = await signup(client, "wrong@test.io")
    uid = (await client.get("/api/auth/me", headers=auth(tok))).json()["user_id"]
    bad = create_purpose_token(uid, "reset")  # wrong purpose for /verify
    r = await client.post("/api/auth/verify", json={"token": bad})
    assert r.status_code == 400


async def test_password_reset_flow(client):
    await signup(client, "reset@test.io")
    # request-reset always 200 (no email enumeration)
    r = await client.post("/api/auth/request-reset", json={"email": "reset@test.io"})
    assert r.json()["sent"] is True
    r = await client.post("/api/auth/request-reset", json={"email": "nobody@test.io"})
    assert r.json()["sent"] is True

    uid = None
    # log in to discover user id
    login = await client.post("/api/auth/login", json={"email": "reset@test.io", "password": "secret123"})
    tok = login.json()["access_token"]
    uid = (await client.get("/api/auth/me", headers=auth(tok))).json()["user_id"]

    rtoken = create_purpose_token(uid, "reset")
    r = await client.post("/api/auth/reset", json={"token": rtoken, "password": "newpass123"})
    assert r.json()["reset"] is True

    # old password fails, new works
    assert (await client.post("/api/auth/login",
            json={"email": "reset@test.io", "password": "secret123"})).status_code == 401
    assert (await client.post("/api/auth/login",
            json={"email": "reset@test.io", "password": "newpass123"})).status_code == 200
