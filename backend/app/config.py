"""Application configuration loaded from the environment.

Every integration secret is optional at import time so the app and its tests can
boot without a full environment; the code paths that need a value raise a clear
error when it is missing.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Core
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/nextoffer",
        description="Async SQLAlchemy URL for Azure Database for PostgreSQL.",
    )
    frontend_url: str = "http://localhost:3000"
    auth_secret: str = Field(default="dev-insecure-change-me", description="Shared HS256 secret with the frontend.")
    token_encryption_key: str = Field(
        default="",
        description="Fernet key for encrypting stored Google refresh tokens (used from milestone 1).",
    )

    # Microsoft Foundry (Azure AI Foundry) — OpenAI-compatible endpoint
    foundry_endpoint: str = ""
    foundry_api_key: str = ""
    foundry_api_version: str = ""
    foundry_deployment: str = "gpt-5.6-terra"

    # Google OAuth (used from milestone 1)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_oauth_redirect_uri: str = "http://localhost:8000/google/callback"

    # Agent behaviour
    agent_max_tool_iterations: int = 6
    chat_history_window: int = 20

@lru_cache
def get_settings() -> Settings:
    return Settings()
