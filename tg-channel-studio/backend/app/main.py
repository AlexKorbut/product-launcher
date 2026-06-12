"""FastAPI application entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, channels, dashboard, donors, posts
from app.config import get_settings

app = FastAPI(title=get_settings().app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # frontend is served behind the same reverse proxy in prod
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(channels.router)
app.include_router(donors.router)
app.include_router(posts.router)
app.include_router(dashboard.router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
