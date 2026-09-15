"""Strict backend-only client for the HealthSphere safety agent."""

from datetime import datetime
from typing import Literal
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentTurn(StrictModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class AgentAssessment(StrictModel):
    target_id: str
    score: float = Field(ge=0, le=1)
    score_type: str
    calibrated: Literal[False]
    model_version: str
    prediction_horizon_days: Literal[1825]


class AgentHealthContext(StrictModel):
    profile: dict[str, object] | None
    measurements: list[dict[str, object]] = Field(max_length=20)
    assessment: AgentAssessment | None = None


class AgentRequest(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    request_id: UUID
    conversation_ref: UUID
    user_message: str = Field(min_length=1, max_length=2000)
    recent_turns: list[AgentTurn] = Field(max_length=6)
    health_context: AgentHealthContext


class AgentSource(StrictModel):
    source_id: str
    title: str
    url: str | None


class AgentSafety(StrictModel):
    urgent: bool
    reason: str | None


class AgentProvenance(StrictModel):
    corpus_version: str
    retrieval_version: str
    prompt_version: str
    model_provider: str
    model_name: str
    generated_at: datetime


class AgentResponse(StrictModel):
    schema_version: Literal["1.0"]
    request_id: UUID
    response_type: Literal["answer", "follow_up", "abstention", "urgent"]
    content: str
    sources: list[AgentSource]
    safety: AgentSafety
    uncertainty: str | None
    provenance: AgentProvenance

    @model_validator(mode="after")
    def validate_state(self) -> "AgentResponse":
        if self.response_type == "answer" and not self.sources:
            raise ValueError("answer responses require sources")
        if (self.response_type == "urgent") != self.safety.urgent:
            raise ValueError("urgent response and safety flag must agree")
        return self


class AgentTransportError(Exception):
    pass


class AgentContractError(Exception):
    pass


class HealthSphereAgentClient:
    def __init__(self, base_url: str, token: str, timeout: float, connect_timeout: float):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = httpx.Timeout(timeout, connect=connect_timeout)

    def respond(self, payload: AgentRequest) -> AgentResponse:
        try:
            response = httpx.post(
                f"{self.base_url}/internal/v1/agent/responses",
                json=payload.model_dump(mode="json"),
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "X-Request-ID": str(payload.request_id),
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            raise AgentTransportError from exc
        try:
            result = AgentResponse.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise AgentContractError from exc
        if result.request_id != payload.request_id:
            raise AgentContractError("request_id mismatch")
        return result
