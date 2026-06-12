"""Application configuration loaded from environment / .env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Core ---
    app_name: str = "TG Channel Studio"
    debug: bool = False
    secret_key: str = "change-me-in-production"  # JWT signing + Fernet key derivation
    database_url: str = "postgresql+asyncpg://studio:studio@localhost:5432/studio"

    # --- Admin auth (single-tenant MVP) ---
    admin_email: str = "admin@example.com"
    admin_password: str = "admin"
    jwt_ttl_hours: int = 24

    # --- Anthropic / generation ---
    anthropic_api_key: str = ""
    # Default to the most capable Opus-tier model; override per deployment if needed.
    generation_model: str = "claude-opus-4-8"
    generation_max_tokens: int = 16000
    # Price per 1M tokens (USD) for cost tracking; keep in sync with the chosen model.
    price_input_per_mtok: float = 5.00
    price_output_per_mtok: float = 25.00

    # --- Telegram userbot (Telethon, MTProto) — reads donor channels ---
    telegram_api_id: int = 0
    telegram_api_hash: str = ""
    telethon_session: str = "userbot"  # session name or StringSession contents

    # --- Worker tuning ---
    ingest_default_interval_min: int = 15
    ingest_jitter_sec: int = 20          # random delay between donor reads (anti-flood)
    generator_poll_sec: int = 30
    publisher_poll_sec: int = 20
    max_rewrite_similarity: float = 0.75  # anti-plagiarism: reject rewrites too close to source


@lru_cache
def get_settings() -> Settings:
    return Settings()
