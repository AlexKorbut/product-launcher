"""Typed settings: non-secret config from config/settings.toml, secrets from env."""

from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # morning-paper/
CONFIG_DIR = PROJECT_ROOT / "config"
THEMES_DIR = PROJECT_ROOT / "themes"
RENDERER_DIR = PROJECT_ROOT / "renderer"


class Defaults(BaseModel):
    output_lang: str = "ru"
    theme: str = "times-classic"
    page_format: str = "a4"


class ModelRouting(BaseModel):
    tagging: str = "claude-haiku-4-5"
    summarize: str = "claude-sonnet-4-6"
    editorial: str = "claude-opus-4-8"


class LLMOptions(BaseModel):
    use_batch: bool = True
    use_prompt_cache: bool = True


class FileConfig(BaseModel):
    """The parsed contents of settings.toml."""

    defaults: Defaults = Defaults()
    models: ModelRouting = ModelRouting()
    llm: LLMOptions = LLMOptions()
    embeddings: dict = {}
    retrieval: dict = {}


class Secrets(BaseSettings):
    """Secrets and connection strings, pulled from the environment / .env."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    anthropic_api_key: str | None = None
    voyage_api_key: str | None = None
    mp_db_url: str | None = None
    mp_object_store_url: str = "file://./.data/objects"
    tg_api_id: str | None = None
    tg_api_hash: str | None = None
    newsapi_key: str | None = None
    telegram_bot_token: str | None = None
    resend_api_key: str | None = None


class Settings(BaseModel):
    file: FileConfig
    secrets: Secrets


def _load_file_config() -> FileConfig:
    path = CONFIG_DIR / "settings.toml"
    if not path.exists():
        return FileConfig()
    with path.open("rb") as fh:
        return FileConfig.model_validate(tomllib.load(fh))


@lru_cache
def get_settings() -> Settings:
    return Settings(file=_load_file_config(), secrets=Secrets())
