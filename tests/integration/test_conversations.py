from datetime import UTC, datetime

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
