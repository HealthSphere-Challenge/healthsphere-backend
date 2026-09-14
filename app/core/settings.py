from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="HEALTHSPHERE_",
        extra="forbid",
        case_sensitive=False,
        populate_by_name=True,
    )

    app_environment: str = Field(default="development", pattern="^(development|test|production)$")
    debug: bool = False
    log_level: str = "INFO"
    database_url: str = Field(validation_alias="DATABASE_URL")
    test_database_url: str | None = Field(default=None, validation_alias="TEST_DATABASE_URL")
    ai_service_url: str | None = None
    agent_service_url: str | None = None
    cors_origins: tuple[str, ...] = ()
    session_cookie_name: str = "healthsphere_session"
    session_absolute_seconds: int = 604800
    session_idle_seconds: int = 86400
    session_cookie_secure: bool | None = None

    @field_validator("database_url")
    @classmethod
    def require_postgresql_psycopg(cls, value: str) -> str:
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use postgresql+psycopg")
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            value = tuple(origin.strip() for origin in value.split(",") if origin.strip())
        return value

    @field_validator("cors_origins")
    @classmethod
    def reject_wildcard_origins(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if "*" in value:
            raise ValueError("credentialed CORS cannot use a wildcard origin")
        if any(not origin.startswith(("http://", "https://")) for origin in value):
            raise ValueError("CORS origins must use http or https")
        return value

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("LOG_LEVEL is invalid")
        return normalized


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
