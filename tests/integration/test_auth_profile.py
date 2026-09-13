import hashlib
import os
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, update

from app.core.settings import Settings
from app.db.session import create_database_engine, create_session_factory, get_db
from app.main import create_app
from app.models import SessionRecord, User


@pytest.fixture
def client() -> TestClient:
    url = os.environ["TEST_DATABASE_URL"]
    engine = create_database_engine(url)
    factory = create_session_factory(engine)
    with factory.begin() as db:
        db.execute(delete(SessionRecord))
        db.execute(delete(User))
    settings = Settings(
        database_url=url, app_environment="test", cors_origins=("http://localhost:5173",)
    )
    app = create_app(settings)

    def test_db():
        with factory() as db:
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise

    app.dependency_overrides[get_db] = test_db
    with TestClient(app) as test_client:
        yield test_client
    engine.dispose()


def register(client: TestClient, email: str = "alex@example.test") -> tuple[dict, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Correct-Horse-42", "display_name": "Alex"},
    )
    assert response.status_code == 201
    return response.json(), response.json()["csrf_token"]


@pytest.mark.integration
def test_registration_duplicate_login_me_and_failure(client: TestClient) -> None:
    body, _ = register(client, "ALEX@example.test")
    assert body["user"]["email"] == "alex@example.test"
    assert body["profile"]["date_of_birth"] is None
    assert (
        "HttpOnly"
        in client.post(
            "/api/v1/auth/login",
            json={"email": "alex@example.test", "password": "Correct-Horse-42"},
        ).headers["set-cookie"]
    )
    duplicate = client.post(
        "/api/v1/auth/register",
        json={
            "email": "alex@example.test",
            "password": "Correct-Horse-42",
            "display_name": "Other",
        },
    )
    assert (duplicate.status_code, duplicate.json()["error"]["code"]) == (
        409,
        "email_already_registered",
    )
    failure = client.post(
        "/api/v1/auth/login", json={"email": "alex@example.test", "password": "wrong"}
    )
    assert (failure.status_code, failure.json()["error"]["code"]) == (401, "invalid_credentials")
    assert client.get("/api/v1/me").status_code == 200


@pytest.mark.integration
def test_profile_patch_csrf_age_and_semantics(client: TestClient) -> None:
    _, csrf = register(client)
    denied = client.patch("/api/v1/profile", json={"allergies": []})
    assert (denied.status_code, denied.json()["error"]["code"]) == (403, "csrf_failed")
    underage = client.patch(
        "/api/v1/profile",
        headers={"X-CSRF-Token": csrf},
        json={
            "date_of_birth": datetime.now(UTC)
            .date()
            .replace(year=datetime.now(UTC).year - 17)
            .isoformat()
        },
    )
    assert underage.status_code == 422
    saved = client.patch(
        "/api/v1/profile",
        headers={"X-CSRF-Token": csrf},
        json={
            "date_of_birth": "1990-06-15",
            "allergies": [],
            "medications": None,
            "medical_conditions": ["hypertension"],
        },
    )
    assert saved.status_code == 200
    assert saved.json()["allergies"] == [] and saved.json()["medications"] is None
    unchanged = client.patch(
        "/api/v1/profile", headers={"X-CSRF-Token": csrf}, json={"height_cm": 172.5}
    )
    assert unchanged.json()["allergies"] == []
    assert client.get("/api/v1/profile").json()["medical_conditions"] == ["hypertension"]


@pytest.mark.integration
def test_session_expiration_idle_logout_ownership_and_cors(client: TestClient) -> None:
    _, csrf = register(client, "first@example.test")
    first_profile = client.get("/api/v1/profile").json()["id"]
    assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 204
    assert client.get("/api/v1/me").status_code == 401
    register(client, "second@example.test")
    assert client.get("/api/v1/profile").json()["id"] != first_profile
    assert (
        client.options(
            "/api/v1/profile",
            headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "PATCH"},
        ).headers["access-control-allow-origin"]
        == "http://localhost:5173"
    )
    cookie = client.cookies.get("healthsphere_session")
    engine = create_database_engine(os.environ["TEST_DATABASE_URL"])
    with create_session_factory(engine).begin() as db:
        db.execute(
            update(SessionRecord)
            .where(SessionRecord.token_hash == hashlib.sha256(cookie.encode()).hexdigest())
            .values(last_used_at=datetime.now(UTC) - timedelta(days=2))
        )
    assert client.get("/api/v1/me").json()["error"]["code"] == "session_expired"
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "second@example.test", "password": "Correct-Horse-42"},
    )
    assert login.status_code == 200
    cookie = client.cookies.get("healthsphere_session")
    with create_session_factory(engine).begin() as db:
        db.execute(
            update(SessionRecord)
            .where(SessionRecord.token_hash == hashlib.sha256(cookie.encode()).hexdigest())
            .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
    assert client.get("/api/v1/me").json()["error"]["code"] == "session_expired"
    engine.dispose()
