from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.agent_client import AgentResponse, AgentTransportError
from app.api.conversations import get_agent_client
from app.core.settings import Settings
from app.db.session import create_database_engine, create_session_factory, get_db
from app.main import create_app
from app.models import Conversation, ConversationMessage, RiskAssessment, SessionRecord, User


class FakeAgent:
    def __init__(self, response_type: str = "follow_up", fail: bool = False):
        self.response_type, self.fail, self.requests = response_type, fail, []

    def respond(self, payload):
        self.requests.append(payload)
        if self.fail:
            raise AgentTransportError
        urgent = self.response_type == "urgent"
        return AgentResponse.model_validate(
            {
                "schema_version": "1.0",
                "request_id": str(payload.request_id),
                "response_type": self.response_type,
                "content": "Safe test response",
                "sources": (
                    [{"source_id": "s1", "title": "Source", "url": "https://example.test"}]
                    if self.response_type == "answer"
                    else []
                ),
                "safety": {"urgent": urgent, "reason": "seek care" if urgent else None},
                "uncertainty": "limited context",
                "provenance": {
                    "corpus_version": "v1",
                    "retrieval_version": "v1",
                    "prompt_version": "v1",
                    "model_provider": "test",
                    "model_name": "test",
                    "generated_at": datetime.now(UTC).isoformat(),
                },
            }
        )


@pytest.fixture
def environment():
    url = __import__("os").environ["TEST_DATABASE_URL"]
    engine = create_database_engine(url)
    factory = create_session_factory(engine)
    with factory.begin() as db:
        db.execute(delete(ConversationMessage))
        db.execute(delete(Conversation))
        db.execute(delete(RiskAssessment))
        db.execute(delete(SessionRecord))
        db.execute(delete(User))
    app = create_app(Settings(database_url=url, app_environment="test"))

    def test_db():
        with factory() as db:
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise

    app.dependency_overrides[get_db] = test_db
    with TestClient(app) as client:
        yield client, app, factory
    engine.dispose()


def register(client: TestClient, email: str = "assistant@example.test") -> str:
    result = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Correct-Horse-42", "display_name": "Assistant User"},
    )
    return result.json()["csrf_token"]


def test_conversation_lifecycle_and_minimum_agent_context(environment) -> None:
    client, app, _ = environment
    csrf = register(client)
    fake = FakeAgent("answer")
    app.dependency_overrides[get_agent_client] = lambda: fake
    created = client.post("/api/v1/conversations", headers={"X-CSRF-Token": csrf})
    assert created.status_code == 201
    conversation_id = created.json()["id"]
    sent = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers={"X-CSRF-Token": csrf},
        json={"content": " Explain my readings. "},
    )
    assert sent.status_code == 200
    assert [message["role"] for message in sent.json()["messages"]] == ["user", "assistant"]
    assert sent.json()["messages"][1]["response_type"] == "answer"
    request = fake.requests[0]
    assert request.user_message == "Explain my readings."
    assert request.health_context.profile is None
    assert request.health_context.measurements == []
    assert request.health_context.assessment is None
    assert request.recent_turns == []
    assert client.get("/api/v1/conversations").json()["items"][0]["id"] == conversation_id
    assert (
        client.delete(
            f"/api/v1/conversations/{conversation_id}", headers={"X-CSRF-Token": csrf}
        ).status_code
        == 204
    )
    assert client.get(f"/api/v1/conversations/{conversation_id}").status_code == 404


def test_agent_outage_persists_neither_message(environment) -> None:
    client, app, factory = environment
    csrf = register(client)
    app.dependency_overrides[get_agent_client] = lambda: FakeAgent(fail=True)
    conversation_id = client.post("/api/v1/conversations", headers={"X-CSRF-Token": csrf}).json()[
        "id"
    ]
    response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers={"X-CSRF-Token": csrf},
        json={"content": "Hello"},
    )
    assert response.status_code == 503
    with factory() as db:
        assert list(db.scalars(select(ConversationMessage))) == []


@pytest.mark.parametrize("response_type", ["follow_up", "abstention", "urgent"])
def test_preserves_non_answer_response_states(environment, response_type: str) -> None:
    client, app, _ = environment
    csrf = register(client)
    app.dependency_overrides[get_agent_client] = lambda: FakeAgent(response_type)
    conversation_id = client.post("/api/v1/conversations", headers={"X-CSRF-Token": csrf}).json()[
        "id"
    ]
    response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers={"X-CSRF-Token": csrf},
        json={"content": "Help me understand."},
    )
    assistant = response.json()["messages"][1]
    assert assistant["response_type"] == response_type
    assert assistant["safety"]["urgent"] is (response_type == "urgent")


def test_other_users_conversations_are_hidden(environment) -> None:
    client, app, _ = environment
    csrf_a = register(client, "owner-a@example.test")
    conversation_id = client.post("/api/v1/conversations", headers={"X-CSRF-Token": csrf_a}).json()[
        "id"
    ]
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_a})
    csrf_b = register(client, "owner-b@example.test")
    assert client.get(f"/api/v1/conversations/{conversation_id}").status_code == 404
    assert (
        client.delete(
            f"/api/v1/conversations/{conversation_id}", headers={"X-CSRF-Token": csrf_b}
        ).status_code
        == 404
    )
    app.dependency_overrides[get_agent_client] = lambda: FakeAgent()
    assert (
        client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers={"X-CSRF-Token": csrf_b},
            json={"content": "Hello"},
        ).status_code
        == 404
    )


def test_conversations_require_authentication_and_csrf(environment) -> None:
    client, _, _ = environment
    assert client.get("/api/v1/conversations").status_code == 401
    register(client)
    assert client.post("/api/v1/conversations").status_code == 403


@pytest.mark.parametrize(
    "question",
    [
        "What health data is in my profile?",
        "donner les données da ma santé dans mon profil",
    ],
)
def test_profile_questions_use_authoritative_data_without_agent(environment, question: str) -> None:
    client, app, _ = environment
    csrf = register(client)
    client.patch(
        "/api/v1/profile",
        headers={"X-CSRF-Token": csrf},
        json={
            "height_cm": 180,
            "smoking_status": "never",
            "allergies": ["pollen"],
        },
    )
    fake = FakeAgent("answer")
    app.dependency_overrides[get_agent_client] = lambda: fake
    conversation_id = client.post("/api/v1/conversations", headers={"X-CSRF-Token": csrf}).json()[
        "id"
    ]
    response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers={"X-CSRF-Token": csrf},
        json={"content": question},
    )
    assistant = response.json()["messages"][1]
    assert "Height: 180 cm" in assistant["content"]
    assert "Smoking status: never" in assistant["content"]
    assert "pollen" in assistant["content"]
    assert assistant["sources"] == []
    assert "Williams syndrome" not in assistant["content"]
    assert fake.requests == []
    assert str(response.json()).find("assistant@example.test") == -1


def test_single_profile_field_returns_only_that_field(environment) -> None:
    client, app, _ = environment
    csrf = register(client)
    client.patch(
        "/api/v1/profile",
        headers={"X-CSRF-Token": csrf},
        json={
            "height_cm": 180,
            "smoking_status": "never",
        },
    )
    fake = FakeAgent()
    app.dependency_overrides[get_agent_client] = lambda: fake
    conversation_id = client.post("/api/v1/conversations", headers={"X-CSRF-Token": csrf}).json()[
        "id"
    ]
    assistant = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers={"X-CSRF-Token": csrf},
        json={"content": "What is my height?"},
    ).json()["messages"][1]
    assert assistant["content"].splitlines() == [
        "Your HealthSphere profile currently includes:",
        "• Height: 180 cm",
    ]
    assert fake.requests == []


def test_latest_blood_pressure_is_reported_without_interpretation_or_rag(environment) -> None:
    client, app, _ = environment
    csrf = register(client)
    client.post(
        "/api/v1/measurements",
        headers={"X-CSRF-Token": csrf},
        json={
            "metric": "blood_pressure",
            "value": {"systolic": 128, "diastolic": 82},
            "unit": "mmHg",
            "context": None,
            "measured_at": "2026-09-15T10:00:00Z",
            "source": "manual",
            "note": None,
        },
    )
    fake = FakeAgent("answer")
    app.dependency_overrides[get_agent_client] = lambda: fake
    conversation_id = client.post("/api/v1/conversations", headers={"X-CSRF-Token": csrf}).json()[
        "id"
    ]
    assistant = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers={"X-CSRF-Token": csrf},
        json={"content": "What is my latest blood pressure?"},
    ).json()["messages"][1]
    assert "128/82 mmHg" in assistant["content"]
    assert not any(
        word in assistant["content"].lower() for word in ("normal", "healthy", "hypertensive")
    )
    assert assistant["sources"] == []
    assert fake.requests == []


def test_missing_measurement_does_not_fall_back_to_rag(environment) -> None:
    client, app, _ = environment
    csrf = register(client)
    fake = FakeAgent("answer")
    app.dependency_overrides[get_agent_client] = lambda: fake
    conversation_id = client.post("/api/v1/conversations", headers={"X-CSRF-Token": csrf}).json()[
        "id"
    ]
    assistant = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers={"X-CSRF-Token": csrf},
        json={"content": "What is my latest heart rate?"},
    ).json()["messages"][1]
    assert "don't have a saved heart rate" in assistant["content"]
    assert assistant["sources"] == [] and fake.requests == []


def test_selected_assessment_keeps_approved_agent_context(environment) -> None:
    client, app, factory = environment
    csrf = register(client)
    with factory.begin() as db:
        user = db.scalar(select(User).where(User.email == "assistant@example.test"))
        assert user is not None
        assessment = RiskAssessment(
            user_id=user.id,
            request_id=UUID("77777777-7777-4777-8777-777777777777"),
            target_id="incident_essential_hypertension_5y_v1",
            feature_schema_version="hypertension_features_v1",
            model_version="hypertension_5y_v1.0.0",
            preprocessing_version="hypertension_preprocessing_v1",
            prediction_horizon_days=1825,
            score=Decimal("0.42"),
            score_type="uncalibrated_experimental_probability_estimate",
            calibrated=False,
            input_snapshot={},
            provenance_snapshot={},
            created_at=datetime.now(UTC),
        )
        db.add(assessment)
        db.flush()
        assessment_id = str(assessment.id)
    fake = FakeAgent("answer")
    app.dependency_overrides[get_agent_client] = lambda: fake
    conversation_id = client.post("/api/v1/conversations", headers={"X-CSRF-Token": csrf}).json()[
        "id"
    ]
    client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers={"X-CSRF-Token": csrf},
        json={"content": "Explain my selected assessment", "assessment_id": assessment_id},
    ).raise_for_status()
    context = fake.requests[0].health_context
    assert context.profile is None and context.measurements == []
    assert context.assessment is not None
    assert context.assessment.score == 0.42
