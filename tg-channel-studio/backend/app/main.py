"""FastAPI application entrypoint."""
import sqlalchemy
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, billing, channels, dashboard, donors, posts, raw, team
from app.config import get_settings
from app.db import get_engine

settings = get_settings()

if settings.sentry_dsn:
    import sentry_sdk

    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)

app = FastAPI(title=settings.app_name, version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(channels.router)
app.include_router(donors.router)
app.include_router(posts.router)
app.include_router(raw.router)
app.include_router(team.router)
app.include_router(billing.router)
app.include_router(dashboard.router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/ready")
async def ready() -> dict:
    """Readiness probe — verifies the database is reachable."""
    async with get_engine().connect() as conn:
        await conn.execute(sqlalchemy.text("SELECT 1"))
    return {"status": "ready"}
