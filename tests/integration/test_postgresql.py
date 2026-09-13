import os
from urllib.parse import urlsplit

import pytest
from sqlalchemy import text

from app.db.session import create_database_engine, create_session_factory


def database_identity(url: str) -> tuple[str | None, int | None, str]:
    parsed = urlsplit(url.replace("postgresql+psycopg://", "postgresql://", 1))
    return parsed.hostname, parsed.port, parsed.path


@pytest.mark.integration
def test_postgresql_connectivity_uses_isolated_database() -> None:
    test_url = os.getenv("TEST_DATABASE_URL")
    if not test_url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    development_url = os.getenv("DATABASE_URL")
    if development_url and database_identity(test_url) == database_identity(development_url):
        pytest.fail("TEST_DATABASE_URL must not identify the development database")
    if not test_url.startswith("postgresql+psycopg://"):
        pytest.fail("TEST_DATABASE_URL must use postgresql+psycopg")

    engine = create_database_engine(test_url)
    try:
        with create_session_factory(engine)() as session:
            assert (
                session.execute(text("select current_database()"), {})
                .scalar_one()
                .endswith("_test")
            )
    finally:
        engine.dispose()
