from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.ai_client import AiInferenceResponse, AiTransportError
from app.api.assessments import get_ai_client
from app.core.settings import Settings
from app.db.session import create_database_engine, create_session_factory, get_db
from app.main import create_app
from app.models import HealthProfile, RiskAssessment, SessionRecord, User

REQUEST_ID = "c4a760a8-7d0b-4f98-9652-244be1ebcc2e"


@pytest.fixture
def client() -> TestClient:
    url = __import__("os").environ["TEST_DATABASE_URL"]
    engine = create_database_engine(url)
    factory = create_session_factory(engine)
    with factory.begin() as db:
        db.execute(delete(RiskAssessment))
        db.execute(delete(SessionRecord))
        db.execute(delete(User))
    settings = Settings(database_url=url, app_environment="test")
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


def register(client, email="assessment@example.test"):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Correct-Horse-42", "display_name": "Assess"},
    )
    return response.json()["csrf_token"]


def completed(request_id: UUID) -> AiInferenceResponse:
    return AiInferenceResponse.model_validate(
        {
            "schema_version": "1.0",
            "request_id": str(request_id),
            "status": "completed",
            "result": {
                "target": "incident_essential_hypertension_5y_v1",
                "population": "eligible adult",
                "horizon": "1825 days",
                "score": 0.25,
                "score_type": "uncalibrated_experimental_probability_estimate",
                "calibrated": False,
                "label": None,
                "explanation": None,
                "limitations": ["synthetic"],
            },
            "reason": None,
            "provenance": {
                "model_name": "HealthSphere experimental hypertension XGBoost",
                "model_version": "hypertension_5y_v1.0.0",
                "feature_schema_version": "hypertension_features_v1",
                "preprocessing_version": "hypertension_preprocessing_v1",
                "calibration_version": None,
                "explanation_method": "global_native_xgboost_gain_only",
                "prediction_horizon_days": 1825,
                "calibrated": False,
                "calibration_status": "uncalibrated; synthetic",
                "generated_at": "2026-09-14T19:00:00Z",
            },
        }
    )


class FakeAiClient:
    def __init__(self, status="completed"):
        self.status = status
        self.calls = []

    def infer(self, request_id, subject_ref, features):
        self.calls.append((request_id, subject_ref, features))
        if self.status == "network_failure":
            raise AiTransportError("secret downstream detail")
        if self.status == "completed":
            return completed(request_id)
        return AiInferenceResponse.model_validate(
            {
                "schema_version": "1.0",
                "request_id": str(request_id),
                "status": self.status,
                "result": None,
                "reason": {"code": f"test_{self.status}", "missing_fields": None},
                "provenance": None,
            }
        )


def measurement(client, csrf, metric, value, unit):
    return client.post(
        "/api/v1/measurements",
        headers={"X-CSRF-Token": csrf},
        json={
            "metric": metric,
            "value": value,
            "unit": unit,
            "context": None,
            "measured_at": "2026-09-12T09:30:00Z",
            "source": "manual",
            "note": None,
        },
    )


def prepare_complete_user(client, email="assessment@example.test"):
    csrf = register(client, email)
    client.patch(
        "/api/v1/profile",
        headers={"X-CSRF-Token": csrf},
        json={
            "date_of_birth": "1990-06-15",
            "height_cm": 180,
            "sex_at_birth": "female",
            "smoking_status": "never",
        },
    )
    assert (
        measurement(
            client, csrf, "blood_pressure", {"systolic": 128, "diastolic": 82}, "mmHg"
        ).status_code
        == 201
    )
    assert measurement(client, csrf, "heart_rate", 76, "bpm").status_code == 201
    assert measurement(client, csrf, "weight", 81, "kg").status_code == 201
    return csrf


@pytest.mark.integration
def test_completed_assessment_persists_provenance_snapshot_and_is_idempotent(client):
    fake = FakeAiClient()
    client.app.dependency_overrides[get_ai_client] = lambda: fake
    csrf = prepare_complete_user(client)
    headers = {"X-CSRF-Token": csrf, "X-Request-ID": REQUEST_ID}
    created = client.post("/api/v1/assessments", headers=headers)
    assert created.status_code == 200
    body = created.json()
    assert body["status"] == "completed"
    assert body["result"]["score"] == 0.25
    assert body["result"]["calibrated"] is False
    assert body["result"]["data_source_type"] == "synthetic_model"
    assert client.post("/api/v1/assessments", headers=headers).json()["id"] == body["id"]
    assert len(fake.calls) == 1
    assert client.get(f"/api/v1/assessments/{body['id']}").json() == body
    assert client.get("/api/v1/assessments").json()["items"] == [body]
    assert client.get("/api/v1/dashboard").json()["latest_assessment"] == body
    paths = client.get("/openapi.json").json()["paths"]
    assert set(paths["/api/v1/assessments"]) == {"get", "post"}
    assert set(paths["/api/v1/assessments/{assessment_id}"]) == {"get"}

    engine = create_database_engine(__import__("os").environ["TEST_DATABASE_URL"])
    with create_session_factory(engine)() as db:
        stored = db.scalar(select(RiskAssessment))
        assert stored.model_version == "hypertension_5y_v1.0.0"
        assert stored.feature_schema_version == "hypertension_features_v1"
        assert stored.score_type == "uncalibrated_experimental_probability_estimate"
        assert stored.input_snapshot == fake.calls[0][2].model_dump()
        assert stored.input_snapshot["bmi"] == 25.0
        assert stored.provenance_snapshot["model_version"] == "hypertension_5y_v1.0.0"
        assert stored.created_at.tzinfo is not None
    engine.dispose()
    register(client, "other-assessment@example.test")
    assert client.get(f"/api/v1/assessments/{body['id']}").status_code == 404


@pytest.mark.integration
@pytest.mark.parametrize("status", ["insufficient_data", "ineligible", "unavailable"])
def test_remote_non_completed_status_never_persists(client, status):
    fake = FakeAiClient(status)
    client.app.dependency_overrides[get_ai_client] = lambda: fake
    csrf = prepare_complete_user(client)
    response = client.post(
        "/api/v1/assessments",
        headers={"X-CSRF-Token": csrf, "X-Request-ID": REQUEST_ID},
    )
    assert response.json()["status"] == status
    assert response.json()["result"] is None
    assert client.get("/api/v1/assessments").json()["items"] == []


@pytest.mark.integration
def test_local_missing_minor_network_auth_csrf_and_ownership(client):
    fake = FakeAiClient()
    client.app.dependency_overrides[get_ai_client] = lambda: fake
    assert client.post("/api/v1/assessments").status_code == 401
    csrf = register(client)
    assert client.post("/api/v1/assessments").status_code == 403
    missing = client.post("/api/v1/assessments", headers={"X-CSRF-Token": csrf})
    assert missing.json()["status"] == "insufficient_data" and not fake.calls

    engine = create_database_engine(__import__("os").environ["TEST_DATABASE_URL"])
    with create_session_factory(engine).begin() as db:
        profile = db.scalar(select(HealthProfile))
        profile.date_of_birth = date(datetime.now(UTC).year - 17, 1, 1)
    engine.dispose()
    bp = measurement(client, csrf, "blood_pressure", {"systolic": 120, "diastolic": 80}, "mmHg")
    assert bp.status_code == 201
    minor = client.post("/api/v1/assessments", headers={"X-CSRF-Token": csrf})
    assert minor.json()["status"] == "ineligible"

    failing = FakeAiClient("network_failure")
    client.app.dependency_overrides[get_ai_client] = lambda: failing
    complete_csrf = prepare_complete_user(client, "network-assessment@example.test")
    network = client.post("/api/v1/assessments", headers={"X-CSRF-Token": complete_csrf})
    assert network.status_code == 503
    assert network.json()["error"]["code"] == "ai_unavailable"
    assert "secret downstream detail" not in network.text
