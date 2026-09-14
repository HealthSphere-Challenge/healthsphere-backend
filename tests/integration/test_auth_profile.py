import hashlib
import os
from datetime import UTC, datetime, timedelta

import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError

from app.core.settings import Settings
from app.db.session import create_database_engine, create_session_factory, get_db
from app.main import create_app
from app.models import HealthProfile, SessionRecord, User


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
    cookie = client.cookies.get("healthsphere_session")
    assert cookie is not None and len(cookie) >= 43
    engine = create_database_engine(os.environ["TEST_DATABASE_URL"])
    factory = create_session_factory(engine)
    with factory() as db:
        user = db.query(User).filter_by(email="alex@example.test").one()
        session = db.query(SessionRecord).filter_by(user_id=user.id).one()
        assert user.password_hash.startswith("$argon2id$")
        assert session.token_hash == hashlib.sha256(cookie.encode()).hexdigest()
        assert cookie not in session.token_hash
        user.password_hash = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1).hash(
            "Correct-Horse-42"
        )
        weak_hash = user.password_hash
        db.commit()
    assert (
        "HttpOnly"
        in client.post(
            "/api/v1/auth/login",
            json={"email": "alex@example.test", "password": "Correct-Horse-42"},
        ).headers["set-cookie"]
    )
    with factory() as db:
        assert db.query(User).filter_by(email="alex@example.test").one().password_hash != weak_hash
    engine.dispose()
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
    assert client.get("/api/v1/auth/me").status_code == 200


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
    mass_assignment = client.patch(
        "/api/v1/profile",
        headers={"X-CSRF-Token": csrf},
        json={"user_id": "00000000-0000-4000-8000-000000000000"},
    )
    assert (mass_assignment.status_code, mass_assignment.json()["error"]["code"]) == (
        422,
        "validation_error",
    )
    engine = create_database_engine(os.environ["TEST_DATABASE_URL"])
    with create_session_factory(engine)() as db:
        stored = db.query(HealthProfile).one()
        assert stored.allergies == []
        assert stored.medications is None
        assert stored.medical_conditions == ["hypertension"]
    engine.dispose()


@pytest.mark.integration
def test_openapi_exposes_only_the_approved_hs006_routes(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    expected = {
        "/api/v1/auth/register": {"post"},
        "/api/v1/auth/login": {"post"},
        "/api/v1/auth/logout": {"post"},
        "/api/v1/auth/me": {"get"},
        "/api/v1/profile": {"get", "patch"},
    }
    assert {path: set(paths[path]) for path in expected} == expected
    assert "/api/v1/me" not in paths


@pytest.mark.integration
def test_database_rejects_non_normalized_email(client: TestClient) -> None:
    engine = create_database_engine(os.environ["TEST_DATABASE_URL"])
    with create_session_factory(engine)() as db:
        db.add(
            User(email="Mixed@Example.test", password_hash="not-a-real-hash", display_name="Test")
        )
        with pytest.raises(IntegrityError):
            db.flush()
    engine.dispose()


@pytest.mark.integration
def test_logs_and_safe_errors_exclude_sensitive_values(client: TestClient, caplog) -> None:
    password = "Do-Not-Log-Password-42"
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "private@example.test", "password": password, "display_name": "Private"},
    )
    csrf = response.json()["csrf_token"]
    client.patch(
        "/api/v1/profile",
        headers={"X-CSRF-Token": csrf},
        json={"date_of_birth": "1990-01-02", "allergies": ["private-allergy"]},
    )
    logged = " ".join(record.getMessage() for record in caplog.records)
    for sensitive in (password, csrf, "private-allergy", "1990-01-02"):
        assert sensitive not in logged
    error = client.post(
        "/api/v1/auth/login",
        json={"email": "private@example.test", "password": "incorrect"},
    ).json()["error"]
    assert set(error) == {
        "code",
        "message",
        "details",
        "request_id",
        "retry_after_seconds",
    }
    assert "traceback" not in str(error).lower() and "sql" not in str(error).lower()


def measurement_payload(metric: str, value, unit: str, context=None) -> dict:
    return {
        "metric": metric,
        "value": value,
        "unit": unit,
        "context": context,
        "measured_at": "2026-09-12T09:30:00+02:00",
        "source": "manual",
        "note": None,
    }


@pytest.mark.integration
def test_measurement_auth_validation_creation_and_retrieval(client: TestClient) -> None:
    payload = measurement_payload("heart_rate", 68, "bpm")
    assert client.post("/api/v1/measurements", json=payload).status_code == 401
    _, csrf = register(client)
    assert client.post("/api/v1/measurements", json=payload).status_code == 403
    created = client.post("/api/v1/measurements", headers={"X-CSRF-Token": csrf}, json=payload)
    assert created.status_code == 201
    body = created.json()
    assert body["metric"] == "heart_rate" and body["unit"] == "bpm"
    assert body["measured_at"].startswith("2026-09-12T07:30:00")
    assert body["recorded_at"] != body["measured_at"]
    assert client.get(f"/api/v1/measurements/{body['id']}").json() == body
    listed = client.get("/api/v1/measurements").json()
    assert listed == {"items": [body], "next_cursor": None}


@pytest.mark.integration
def test_measurement_shapes_context_and_bmi_input_are_rejected(client: TestClient) -> None:
    _, csrf = register(client)
    invalid = [
        measurement_payload("blood_pressure", {"systolic": 118}, "mmHg"),
        measurement_payload("blood_glucose", 92.5, "mg/dL"),
        measurement_payload("heart_rate", 68, "kg"),
        measurement_payload("heart_rate", 0, "bpm"),
        measurement_payload("bmi", 24.2, "kg/m2"),
        {**measurement_payload("weight", 72.5, "kg"), "measured_at": "2026-09-12T09:30:00"},
    ]
    for payload in invalid:
        response = client.post("/api/v1/measurements", headers={"X-CSRF-Token": csrf}, json=payload)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.integration
def test_dashboard_empty_latest_bmi_and_all_canonical_metrics(client: TestClient) -> None:
    _, csrf = register(client)
    empty = client.get("/api/v1/dashboard").json()
    assert all(value is None for value in empty["latest_measurements"].values())
    client.patch(
        "/api/v1/profile",
        headers={"X-CSRF-Token": csrf},
        json={"date_of_birth": "1990-01-01", "height_cm": 180},
    )
    payloads = [
        measurement_payload("heart_rate", 68, "bpm"),
        measurement_payload("blood_pressure", {"systolic": 118, "diastolic": 76}, "mmHg"),
        measurement_payload("weight", 81, "kg"),
        measurement_payload("blood_glucose", 92.5, "mg/dL", "fasting"),
        measurement_payload("sleep_duration", 450, "min"),
        measurement_payload("physical_activity_duration", 30, "min"),
    ]
    for payload in payloads:
        assert (
            client.post(
                "/api/v1/measurements", headers={"X-CSRF-Token": csrf}, json=payload
            ).status_code
            == 201
        )
    dashboard = client.get("/api/v1/dashboard").json()["latest_measurements"]
    assert dashboard["blood_pressure"]["value"] == {"systolic": 118, "diastolic": 76}
    assert dashboard["bmi"]["value"] == 25.0
    assert dashboard["bmi"]["derived_from_measurement_id"] == dashboard["weight"]["id"]


@pytest.mark.integration
def test_measurement_ownership_and_sensitive_logging(client: TestClient, caplog) -> None:
    _, csrf = register(client, "owner@example.test")
    payload = {**measurement_payload("weight", 72.5, "kg"), "note": "private-note"}
    identifier = client.post(
        "/api/v1/measurements", headers={"X-CSRF-Token": csrf}, json=payload
    ).json()["id"]
    register(client, "other@example.test")
    denied = client.get(f"/api/v1/measurements/{identifier}")
    assert (denied.status_code, denied.json()["error"]["code"]) == (
        404,
        "resource_not_found",
    )
    assert client.get("/api/v1/measurements").json()["items"] == []
    assert "private-note" not in " ".join(record.getMessage() for record in caplog.records)


@pytest.mark.integration
def test_session_expiration_idle_logout_ownership_and_cors(client: TestClient) -> None:
    _, csrf = register(client, "first@example.test")
    first_profile = client.get("/api/v1/profile").json()["id"]
    assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401
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
    assert client.get("/api/v1/auth/me").json()["error"]["code"] == "session_expired"
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
    assert client.get("/api/v1/auth/me").json()["error"]["code"] == "session_expired"
    engine.dispose()
