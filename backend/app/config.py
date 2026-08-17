"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime configuration."""

    app_env: str = "development"
    demo_user_id: str = "user-1001"
    payment_approval_limit: float = Field(default=5000, gt=0)
    cors_origins: str = "http://localhost:5173"

    azure_openai_endpoint: str | None = None
    azure_openai_deployment: str = "gpt-4.1"
    azure_document_intelligence_endpoint: str | None = None
    azure_document_intelligence_api_key: str | None = None
    mcp_server_url: str = "http://localhost:8001/mcp"

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin]


@lru_cache
def get_settings() -> Settings:
    return Settings()
