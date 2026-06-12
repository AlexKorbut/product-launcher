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
    public_base_url: str = "http://localhost:3000"   # used in referral links / OG
    cors_origins: str = "*"                          # comma-separated allowlist in prod

    # --- Auth ---
    jwt_ttl_hours: int = 720  # 30 days
    signup_bonus_credits: int = 500       # welcome credits for a new organization
    referral_bonus_credits: int = 300     # credits granted to referrer + referee

    # --- Anthropic / generation ---
    anthropic_api_key: str = ""
    generation_model: str = "claude-opus-4-8"
    generation_max_tokens: int = 16000
    price_input_per_mtok: float = 5.00
    price_output_per_mtok: float = 25.00

    # --- Credits / billing economics ---
    # credits charged per post = ceil(cost_usd * markup / credit_price_usd)
    credit_price_usd: float = 0.01     # 1 credit = $0.01 of customer value
    generation_markup: float = 3.0     # 3x markup on raw model cost → margin

    # --- Stripe ---
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    # Map Stripe Price ID -> credits granted on successful purchase.
    # JSON object string, e.g. {"price_starter": 1000, "price_pro": 5000}
    stripe_price_credits: str = "{}"

    # --- Telegram userbot (Telethon, MTProto) ---
    telegram_api_id: int = 0
    telegram_api_hash: str = ""
    telethon_session: str = "userbot"

    # --- Worker tuning ---
    ingest_jitter_sec: int = 20
    generator_poll_sec: int = 30
    publisher_poll_sec: int = 20
    max_rewrite_similarity: float = 0.75

    # --- Redis (rate-limiting, locks); optional ---
    redis_url: str = ""

    # --- Observability ---
    sentry_dsn: str = ""

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()] or ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
