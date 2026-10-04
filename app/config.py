from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_prefix="REPLYSENSE_", env_file=".env")

    database_url: str = "sqlite:///./replysense.db"
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 15.0
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
