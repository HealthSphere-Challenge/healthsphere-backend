import pytest
from pydantic import ValidationError

from app.core.settings import Settings


def test_database_url_requires_postgresql_psycopg() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite:///local.db")


def test_credentialed_cors_rejects_wildcard() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="postgresql+psycopg://user:pass@localhost/db", cors_origins=("*",))


def test_cors_parses_explicit_origins() -> None:
    settings = Settings(
        database_url="postgresql+psycopg://user:pass@localhost/db",
        cors_origins="http://localhost:5173",
    )
    assert settings.cors_origins == ("http://localhost:5173",)


def test_production_requires_ai_service_configuration() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url="postgresql+psycopg://user:pass@localhost/db",
            app_environment="production",
        )
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://user:pass@localhost/db",
        app_environment="production",
        ai_service_url="http://ai:8001/",
        ai_internal_token="configured-outside-git",
        agent_service_url="http://agent:8010/",
        agent_internal_token="configured-outside-git",
    )
    assert settings.ai_service_url == "http://ai:8001"
