"""Configuration loaded from environment (.env)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Two connection strings: the app runs as app_user (under RLS);
    # provisioner (BYPASSRLS) is used ONLY for signup / migrations.
    app_database_url: str = (
        "postgresql+asyncpg://app_user:apppass@127.0.0.1:5432/lineofsight"
    )
    provisioner_database_url: str = (
        "postgresql+asyncpg://provisioner:provpass@127.0.0.1:5432/lineofsight"
    )

    jwt_secret: str = "change-me-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_ttl_minutes: int = 60 * 12

    # AI formula assistant
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"

    # pgvector dimension — MUST match your embedding model (1024 = Voyage voyage-3)
    embedding_dim: int = 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
