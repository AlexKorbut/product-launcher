import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-long-enough-1234567890")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test")
os.environ.setdefault("STRIPE_PRICE_CREDITS", '{"price_test": 1000}')
os.environ.setdefault("SIGNUP_BONUS_CREDITS", "500")

import pytest_asyncio
import httpx

from app.db import Base, get_engine


@pytest_asyncio.fixture
async def client():
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    from app.main import app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        yield c


async def signup(client, email: str, ref: str | None = None) -> str:
    body = {"email": email, "password": "secret123", "org_name": email}
    if ref:
        body["referral_code"] = ref
    r = await client.post("/api/auth/signup", json=body)
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
