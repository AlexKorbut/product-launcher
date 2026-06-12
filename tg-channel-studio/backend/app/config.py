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

    # --- Generation (LLM provider) ---
    # Default provider used when a channel doesn't override it.
    # Supported: "anthropic" | "openai" (OpenAI-compatible, incl. OpenRouter/DeepSeek/local).
    llm_provider: str = "anthropic"
    generation_max_tokens: int = 16000

    # Anthropic
    anthropic_api_key: str = ""
    generation_model: str = "claude-opus-4-8"   # default Anthropic model
    price_input_per_mtok: float = 5.00          # Anthropic input $/1M
    price_output_per_mtok: float = 25.00        # Anthropic output $/1M

    # OpenAI-compatible (set base_url for OpenRouter / DeepSeek / Together / local)
    openai_api_key: str = ""
    openai_base_url: str = ""                    # empty => api.openai.com
    openai_model: str = "gpt-4o"
    openai_price_input_per_mtok: float = 2.50    # tune to your model/provider
    openai_price_output_per_mtok: float = 10.00

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

    # --- Email (verification, password reset, invites) ---
    # If smtp_host is empty, emails are logged to stdout (dev mode).
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "no-reply@tgchannelstudio.com"

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
