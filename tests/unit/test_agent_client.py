from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest

from app.agent_client import (
    AgentContractError,
    AgentHealthContext,
    AgentRequest,
    AgentTransportError,
    HealthSphereAgentClient,
)


def request_payload() -> AgentRequest:
    return AgentRequest(
        request_id=uuid4(),
        conversation_ref=uuid4(),
        user_message="What does this mean?",
        recent_turns=[],
        health_context=AgentHealthContext(profile=None, measurements=[]),
    )


def response_json(request_id: object) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "request_id": str(request_id),
        "response_type": "follow_up",
        "content": "Could you clarify your question?",
        "sources": [],
        "safety": {"urgent": False, "reason": None},
        "uncertainty": None,
        "provenance": {
            "corpus_version": "v1",
            "retrieval_version": "v1",
            "prompt_version": "v1",
            "model_provider": "test",
            "model_name": "test",
            "generated_at": datetime.now(UTC).isoformat(),
        },
    }


def test_client_sends_auth_and_matching_request_id(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = request_payload()
    captured: dict[str, object] = {}

    def post(url: str, **kwargs: object) -> httpx.Response:
        captured.update(url=url, **kwargs)
        return httpx.Response(
            200, json=response_json(payload.request_id), request=httpx.Request("POST", url)
        )

    monkeypatch.setattr(httpx, "post", post)
    result = HealthSphereAgentClient("http://agent", "secret", 30, 2).respond(payload)
    assert result.request_id == payload.request_id
    assert captured["headers"] == {
        "Authorization": "Bearer secret",
        "X-Request-ID": str(payload.request_id),
    }


def test_client_rejects_mismatched_request_id(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = request_payload()
    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, **kwargs: httpx.Response(
            200, json=response_json(uuid4()), request=httpx.Request("POST", url)
        ),
    )
    with pytest.raises(AgentContractError):
        HealthSphereAgentClient("http://agent", "secret", 30, 2).respond(payload)


def test_client_does_not_retry_transport_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def fail(url: str, **kwargs: object) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx, "post", fail)
    with pytest.raises(AgentTransportError):
        HealthSphereAgentClient("http://agent", "secret", 30, 2).respond(request_payload())
    assert calls == 1
