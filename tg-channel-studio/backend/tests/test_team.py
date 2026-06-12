from sqlalchemy import select

from app.db import SessionLocal
from app.models import Invitation
from tests.conftest import auth, signup


async def _invite_token(org_email: str) -> str:
    async with SessionLocal() as s:
        inv = await s.scalar(select(Invitation).order_by(Invitation.id.desc()))
        return inv.token


async def test_invite_accept_and_switch_org(client):
    owner = await signup(client, "owner@test.io")
    member = await signup(client, "member@test.io")

    # owner invites the member
    r = await client.post("/api/team/invite", headers=auth(owner),
                          json={"email": "member@test.io", "role": "editor"})
    assert r.status_code == 201, r.text
    token = await _invite_token("owner@test.io")

    # member accepts -> gets a token scoped to the owner's org
    r = await client.post("/api/auth/accept-invite", headers=auth(member), json={"token": token})
    assert r.status_code == 200, r.text
    joined_tok = r.json()["access_token"]

    # member now belongs to two orgs
    orgs = (await client.get("/api/auth/orgs", headers=auth(joined_tok))).json()
    assert len(orgs) == 2

    # team members list shows both, owner sees roles
    members = (await client.get("/api/team/members", headers=auth(owner))).json()
    emails = {m["email"]: m["role"] for m in members}
    assert emails["owner@test.io"] == "owner"
    assert emails["member@test.io"] == "editor"


async def test_editor_cannot_manage_team(client):
    owner = await signup(client, "o2@test.io")
    member = await signup(client, "m2@test.io")
    r = await client.post("/api/team/invite", headers=auth(owner), json={"email": "m2@test.io"})
    token = await _invite_token("o2@test.io")
    await client.post("/api/auth/accept-invite", headers=auth(member), json={"token": token})

    # member switches into owner's org, then tries to invite -> forbidden (editor)
    orgs = (await client.get("/api/auth/orgs", headers=auth(member))).json()
    owner_org = next(o for o in orgs if o["role"] == "editor")["org_id"]
    sw = await client.post("/api/auth/switch-org", headers=auth(member), json={"org_id": owner_org})
    member_in_org = sw.json()["access_token"]
    r = await client.post("/api/team/invite", headers=auth(member_in_org), json={"email": "x@test.io"})
    assert r.status_code == 403


async def test_accept_wrong_email_rejected(client):
    owner = await signup(client, "o3@test.io")
    other = await signup(client, "o4@test.io")
    await client.post("/api/team/invite", headers=auth(owner), json={"email": "someone@test.io"})
    token = await _invite_token("o3@test.io")
    r = await client.post("/api/auth/accept-invite", headers=auth(other), json={"token": token})
    assert r.status_code == 403


async def test_switch_to_foreign_org_rejected(client):
    a = await signup(client, "a5@test.io")
    await signup(client, "b5@test.io")
    # a is only in its own org; switching to org 999 must fail
    r = await client.post("/api/auth/switch-org", headers=auth(a), json={"org_id": 999})
    assert r.status_code == 403
