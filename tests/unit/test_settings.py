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
