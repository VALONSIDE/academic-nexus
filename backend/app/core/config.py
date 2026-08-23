from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded only from environment variables / .env."""

    # Resolve the repository root in local development. Containers receive the same
    # values from Compose and therefore do not need a copied .env file.
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "AcademicNexus"
    app_env: str = "development"
    # Public deployments must opt in explicitly only where the API schema is
    # intentionally exposed. The local example enables this for development.
    api_docs_enabled: bool = False
    # Product release label shown by OpenAPI and operational tooling.
    # NR means Not Released / 尚未发布.
    app_version: str = "alpha-0823-NR"
    database_url: str = "postgresql+psycopg://academicnexus:academicnexus@localhost:5432/academicnexus"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret_key: str
    access_key_pepper: str
    access_token_expire_minutes: int = 30
    cors_origins: str = "http://localhost,http://localhost:5173"
    initial_admin_email: str
    initial_admin_password: str
    initial_admin_username: str = "ACADEMICNEXUS_ADMIN"
    default_tenant_slug: str = "academicnexus-pilot"
    default_tenant_name: str = "AcademicNexus Pilot"
    minimax_api_key: str = ""
    minimax_base_url: str = "https://api.minimaxi.com/anthropic"
    minimax_model: str = "MiniMax-M3"
    minimax_light_model: str = "MiniMax-M2.5-highspeed"
    minimax_standard_model: str = "MiniMax-M2.7"
    minimax_expert_model: str = "MiniMax-M3"
    ai_daily_project_limit: int = 500
    # Legacy-named quota columns are synchronized to the subscription-cycle
    # allowance. Every account starts with ten normal-plan credits per cycle.
    ai_default_daily_user_limit: int = 10
    ai_default_credit_balance: int = 10
    ai_context_message_limit: int = 16
    ai_context_character_limit: int = 24000
    ai_max_output_tokens: int = 1200
    resource_storage_path: str = "/app/storage/resources"
    resource_max_upload_mb: int = 200
    mentor_resource_default_quota_mb: int = 200

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
