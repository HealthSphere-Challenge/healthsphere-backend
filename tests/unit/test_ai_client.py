from uuid import UUID

import httpx
import pytest

from app.ai_client import AiContractError, AiFeatures, AiTransportError, HealthSphereAiClient

REQUEST_ID = UUID("c4a760a8-7d0b-4f98-9652-244be1ebcc2e")
SUBJECT_REF = UUID("f630d635-64e2-432b-8175-60f61d220d4d")
FEATURES = AiFeatures(
    age_years=42,
    systolic_blood_pressure=128,
    diastolic_blood_pressure=82,
    heart_rate=None,
    bmi=None,
    sex_at_birth="unknown",
    smoking_status="unknown",
)


def completed(request_id: UUID = REQUEST_ID) -> dict:
    return {
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


def test_client_sends_exact_contract_auth_correlation_and_timeout():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return httpx.Response(200, json=completed())

    client = HealthSphereAiClient(
        "http://ai.test", "secret", transport=httpx.MockTransport(handler)
    )
    response = client.infer(REQUEST_ID, SUBJECT_REF, FEATURES)
    request = captured["request"]
    body = __import__("json").loads(request.content)
    assert request.url.path == "/internal/v1/inferences"
    assert request.headers["authorization"] == "Bearer secret"
    assert request.headers["x-request-id"] == body["request_id"] == str(REQUEST_ID)
    assert body["subject_ref"] == str(SUBJECT_REF)
    assert set(body["features"]) == set(AiFeatures.model_fields)
    assert not {"request_id", "subject_ref", "schema_version"} & set(body["features"])
    assert client.timeout.connect == 2 and client.timeout.read == 10
    assert response.status == "completed"


@pytest.mark.parametrize("status", ["insufficient_data", "ineligible", "unavailable"])
def test_client_parses_non_completed_statuses(status):
    payload = completed() | {
        "status": status,
        "result": None,
        "reason": {"code": f"example_{status}", "missing_fields": None},
        "provenance": None,
    }
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json=payload))
    assert (
        HealthSphereAiClient("http://ai.test", "secret", transport=transport)
        .infer(REQUEST_ID, SUBJECT_REF, FEATURES)
        .status
        == status
    )


@pytest.mark.parametrize(
    "mutation",
    [
        {"schema_version": "2.0"},
        {"status": "completed", "result": None},
        {"request_id": "5291676e-3037-4d38-8617-31e84391d71a"},
    ],
)
def test_client_rejects_malformed_or_incompatible_response(mutation):
    payload = completed() | mutation
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json=payload))
    with pytest.raises(AiContractError):
        HealthSphereAiClient("http://ai.test", "secret", transport=transport).infer(
            REQUEST_ID, SUBJECT_REF, FEATURES
        )


def test_client_maps_network_and_canonical_http_failure():
    def timeout(_request):
        raise httpx.ConnectTimeout("no service")

    with pytest.raises(AiTransportError):
        HealthSphereAiClient(
            "http://ai.test", "secret", transport=httpx.MockTransport(timeout)
        ).infer(REQUEST_ID, SUBJECT_REF, FEATURES)


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("result", "target", "wrong-target"),
        ("result", "score", 2.0),
        ("provenance", "model_version", "future-model"),
        ("provenance", "feature_schema_version", "future-schema"),
    ],
)
def test_client_rejects_unsupported_completed_semantics(section, field, value):
    payload = completed()
    payload[section][field] = value
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json=payload))
    with pytest.raises(AiContractError):
        HealthSphereAiClient("http://ai.test", "secret", transport=transport).infer(
            REQUEST_ID, SUBJECT_REF, FEATURES
        )
    with pytest.raises(AiTransportError):
        HealthSphereAiClient(
            "http://ai.test",
            "secret",
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(422, json={"error": {"code": "validation_error"}})
            ),
        ).infer(REQUEST_ID, SUBJECT_REF, FEATURES)
