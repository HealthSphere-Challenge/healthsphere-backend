import pytest

from app.core.settings import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="postgresql+psycopg://healthsphere_user:test@localhost:5432/healthsphere_test",
        app_environment="test",
    )
