from functools import lru_cache

from pydantic import Field, field_validator, model_validator
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
    ai_internal_token: str | None = None
    ai_timeout_seconds: float = Field(default=10.0, gt=0, le=30)
    ai_connect_timeout_seconds: float = Field(default=2.0, gt=0, le=10)
    agent_service_url: str | None = None
    agent_internal_token: str | None = None
    agent_timeout_seconds: float = Field(default=30.0, gt=0, le=60)
    agent_connect_timeout_seconds: float = Field(default=2.0, gt=0, le=10)
    demo_password: str | None = Field(default=None, min_length=12, max_length=128, repr=False)
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

    @field_validator("ai_service_url", "agent_service_url", mode="before")
    @classmethod
    def validate_ai_url(cls, value: object) -> str | None:
        if value == "" or value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Service URL must be a string")
        if value is not None and not value.startswith(("http://", "https://")):
            raise ValueError("Service URL must use http or https")
        return value.rstrip("/")

    @model_validator(mode="after")
    def require_production_ai_configuration(self) -> "Settings":
        if self.app_environment == "production" and (
            not self.ai_service_url or not self.ai_internal_token
        ):
            raise ValueError("Production requires AI_SERVICE_URL and AI_INTERNAL_TOKEN")
        if self.app_environment == "production" and (
            not self.agent_service_url or not self.agent_internal_token
        ):
            raise ValueError("Production requires AGENT_SERVICE_URL and AGENT_INTERNAL_TOKEN")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
