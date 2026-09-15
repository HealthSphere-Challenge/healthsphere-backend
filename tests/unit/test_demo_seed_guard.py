import pytest

from app.core.settings import Settings
from app.scripts.seed_demo import ASSESSMENT_REQUEST_ID, DemoSeedError, require_safe_environment


@pytest.mark.parametrize("environment", ["development", "test"])
def test_demo_seed_allows_non_production_environments(environment: str) -> None:
    require_safe_environment(environment)


@pytest.mark.parametrize("environment", ["production", "staging", ""])
def test_demo_seed_fails_closed_outside_known_safe_environments(environment: str) -> None:
    with pytest.raises(DemoSeedError, match="development or test"):
        require_safe_environment(environment)


def test_demo_password_is_not_exposed_by_settings_repr() -> None:
    password = "Never-Render-This-42"
    settings = Settings(
        database_url="postgresql+psycopg://test:test@localhost:5432/healthsphere_test",
        app_environment="test",
        demo_password=password,
    )
    assert password not in repr(settings)


def test_assessment_preparation_uses_a_stable_uuid4_request_id() -> None:
    assert ASSESSMENT_REQUEST_ID.version == 4
