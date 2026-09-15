from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta
from typing import Literal, cast
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.agent_client import (
    AgentAssessment,
    AgentContractError,
    AgentHealthContext,
    AgentRequest,
    AgentTransportError,
    AgentTurn,
    HealthSphereAgentClient,
)
from app.assistant_context import AssistantContextMode, AssistantContextRouter
from app.core.errors import DomainError
from app.models import (
    Conversation,
    ConversationMessage,
    ConversationRole,
    HealthProfile,
    Measurement,
    MetricType,
    RiskAssessment,
    User,
)
from app.schemas import ConversationListResponse, ConversationMessageResponse, ConversationResponse
from app.services import age_years, decode_cursor


def message_response(row: ConversationMessage) -> ConversationMessageResponse:
    return ConversationMessageResponse(
        id=row.id,
        role=row.role.value,
        content=row.content,
        response_type=cast(
            Literal["answer", "follow_up", "abstention", "urgent"] | None,
            row.response_type,
        ),
        sources=row.sources or [],
        safety=row.safety,
        uncertainty=row.uncertainty,
        provenance=row.provenance,
        created_at=row.created_at,
    )


def conversation_response(row: Conversation) -> ConversationResponse:
    return ConversationResponse(
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        expires_at=row.expires_at,
        messages=[message_response(m) for m in row.messages],
    )


class ConversationService:
    PAGE_SIZE = 50
    RETENTION_DAYS = 30

    def __init__(self, db: Session, agent: HealthSphereAgentClient | None = None):
        self.db, self.agent = db, agent

    def create(self, user: User) -> ConversationResponse:
        now = datetime.now(UTC)
        row = Conversation(
            user_id=user.id,
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(days=self.RETENTION_DAYS),
        )
        self.db.add(row)
        self.db.flush()
        return conversation_response(row)

    def _owned(self, user: User, conversation_id: UUID) -> Conversation:
        row = self.db.scalar(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id,
                Conversation.expires_at > datetime.now(UTC),
            )
        )
        if row is None:
            raise DomainError(404, "resource_not_found", "Conversation was not found.")
        return row

    def get(self, user: User, conversation_id: UUID) -> ConversationResponse:
        return conversation_response(self._owned(user, conversation_id))

    def delete(self, user: User, conversation_id: UUID) -> None:
        row = self._owned(user, conversation_id)
        self.db.delete(row)

    def list(self, user: User, cursor: str | None) -> ConversationListResponse:
        parsed = decode_cursor(cursor)
        stmt = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.user_id == user.id, Conversation.expires_at > datetime.now(UTC))
        )
        if parsed:
            stamp, identifier = parsed
            stmt = stmt.where(
                or_(
                    Conversation.updated_at < stamp,
                    and_(Conversation.updated_at == stamp, Conversation.id < identifier),
                )
            )
        rows = list(
            self.db.scalars(
                stmt.order_by(Conversation.updated_at.desc(), Conversation.id.desc()).limit(
                    self.PAGE_SIZE + 1
                )
            )
        )
        visible, more = rows[: self.PAGE_SIZE], len(rows) > self.PAGE_SIZE
        next_cursor = None
        if more:
            raw = json.dumps(
                [visible[-1].updated_at.isoformat(), str(visible[-1].id)], separators=(",", ":")
            ).encode()
            next_cursor = base64.urlsafe_b64encode(raw).decode().rstrip("=")
        return ConversationListResponse(
            items=[conversation_response(r) for r in visible], next_cursor=next_cursor
        )

    def send(
        self, user: User, conversation_id: UUID, text: str, assessment_id: UUID | None
    ) -> ConversationResponse:
        row = self._owned(user, conversation_id)
        decision = AssistantContextRouter().route(text, assessment_id is not None)
        if decision.mode == AssistantContextMode.own_profile_data:
            return self._persist_deterministic(
                row, text, self._profile_answer(user, decision.requested_fields)
            )
        if decision.mode == AssistantContextMode.own_latest_measurements:
            return self._persist_deterministic(
                row, text, self._measurement_answer(user, decision.requested_fields)
            )
        if decision.mode == AssistantContextMode.unsupported_or_ambiguous:
            return self._persist_deterministic(
                row,
                text,
                "Please ask about a specific profile field, saved measurement, or HealthSphere "
                "assessment so I can use only the information you intend to access.",
                response_type="follow_up",
            )
        if self.agent is None:
            raise DomainError(503, "agent_unavailable", "The assistant service is unavailable.")
        assessment = None
        if assessment_id:
            assessment = self.db.scalar(
                select(RiskAssessment).where(
                    RiskAssessment.id == assessment_id, RiskAssessment.user_id == user.id
                )
            )
            if assessment is None:
                raise DomainError(404, "resource_not_found", "Assessment was not found.")
        payload = AgentRequest(
            request_id=uuid4(),
            conversation_ref=row.id,
            user_message=text,
            recent_turns=[
                AgentTurn(role=m.role.value, content=m.content) for m in row.messages[-6:]
            ],
            health_context=AgentHealthContext(
                profile=None,
                measurements=[],
                assessment=(
                    AgentAssessment(
                        target_id=assessment.target_id,
                        score=float(assessment.score),
                        score_type=assessment.score_type,
                        calibrated=False,
                        model_version=assessment.model_version,
                        prediction_horizon_days=cast(
                            Literal[1825], assessment.prediction_horizon_days
                        ),
                    )
                    if assessment
                    else None
                ),
            ),
        )
        self.db.commit()
        try:
            remote = self.agent.respond(payload)
        except AgentTransportError as exc:
            raise DomainError(
                503, "agent_unavailable", "The assistant service is unavailable."
            ) from exc
        except AgentContractError as exc:
            raise DomainError(
                502, "agent_contract_error", "The assistant response was incompatible."
            ) from exc
        now = datetime.now(UTC)
        self.db.add_all(
            [
                ConversationMessage(
                    conversation_id=row.id, role=ConversationRole.user, content=text, created_at=now
                ),
                ConversationMessage(
                    conversation_id=row.id,
                    role=ConversationRole.assistant,
                    content=remote.content,
                    response_type=remote.response_type,
                    sources=[s.model_dump(mode="json") for s in remote.sources],
                    safety=remote.safety.model_dump(mode="json"),
                    uncertainty=remote.uncertainty,
                    agent_request_id=remote.request_id,
                    provenance=remote.provenance.model_dump(mode="json"),
                    created_at=now + timedelta(microseconds=1),
                ),
            ]
        )
        row.updated_at = now
        self.db.flush()
        self.db.expire(row, ["messages"])
        return conversation_response(row)

    def _persist_deterministic(
        self,
        row: Conversation,
        user_text: str,
        answer: str,
        response_type: str = "answer",
    ) -> ConversationResponse:
        now = datetime.now(UTC)
        self.db.add_all(
            [
                ConversationMessage(
                    conversation_id=row.id,
                    role=ConversationRole.user,
                    content=user_text,
                    created_at=now,
                ),
                ConversationMessage(
                    conversation_id=row.id,
                    role=ConversationRole.assistant,
                    content=answer,
                    response_type=response_type,
                    sources=[],
                    safety={"urgent": False, "reason": None},
                    uncertainty=None,
                    provenance={"source_type": "application_data"},
                    created_at=now + timedelta(microseconds=1),
                ),
            ]
        )
        row.updated_at = now
        self.db.flush()
        self.db.expire(row, ["messages"])
        return conversation_response(row)

    def _profile_answer(self, user: User, fields: tuple[str, ...]) -> str:
        profile = self.db.scalar(select(HealthProfile).where(HealthProfile.user_id == user.id))
        if profile is None:
            return "I don't have a HealthSphere profile saved for you yet."
        selected = fields or (
            "date_of_birth",
            "sex_at_birth",
            "height_cm",
            "smoking_status",
            "allergies",
            "medications",
            "medical_conditions",
            "activity_level",
            "typical_sleep_minutes",
        )
        labels = {
            "date_of_birth": "Age",
            "sex_at_birth": "Sex at birth",
            "height_cm": "Height",
            "smoking_status": "Smoking status",
            "allergies": "Allergies",
            "medications": "Medications",
            "medical_conditions": "Medical conditions",
            "activity_level": "Activity level",
            "typical_sleep_minutes": "Typical sleep",
        }
        lines = []
        for field in selected:
            value: object = getattr(profile, field)
            if field == "date_of_birth":
                value = age_years(profile.date_of_birth)
            elif field == "height_cm" and value is not None:
                value = f"{value:g} cm"
            elif field == "typical_sleep_minutes" and value is not None:
                value = f"{value} minutes"
            elif isinstance(value, list):
                value = ", ".join(value) if value else "Not provided"
            elif hasattr(value, "value"):
                value = value.value
            if value is None:
                value = "Not provided"
            lines.append(f"• {labels[field]}: {value}")
        return "Your HealthSphere profile currently includes:\n" + "\n".join(lines)

    def _measurement_answer(self, user: User, fields: tuple[str, ...]) -> str:
        if not fields:
            return (
                "Which latest saved measurement would you like: blood pressure, heart rate, "
                "weight, blood glucose, sleep duration, or activity duration?"
            )
        metric = MetricType(fields[0])
        measurement = self.db.scalar(
            select(Measurement)
            .where(Measurement.user_id == user.id, Measurement.metric == metric)
            .order_by(Measurement.measured_at.desc(), Measurement.id.desc())
            .limit(1)
        )
        labels = {
            MetricType.blood_pressure: "blood pressure",
            MetricType.heart_rate: "heart rate",
            MetricType.weight: "weight",
            MetricType.blood_glucose: "blood glucose",
            MetricType.sleep_duration: "sleep duration",
            MetricType.physical_activity_duration: "physical activity duration",
        }
        if measurement is None:
            return f"I don't have a saved {labels[metric]} measurement for you yet."
        units = {
            MetricType.blood_pressure: "mmHg",
            MetricType.heart_rate: "bpm",
            MetricType.weight: "kg",
            MetricType.blood_glucose: "mg/dL",
            MetricType.sleep_duration: "minutes",
            MetricType.physical_activity_duration: "minutes",
        }
        value = (
            f"{measurement.systolic}/{measurement.diastolic}"
            if metric == MetricType.blood_pressure
            else f"{measurement.numeric_value:g}"
        )
        recorded = measurement.measured_at.astimezone(UTC).strftime("%B %-d, %Y at %H:%M UTC")
        return (
            f"Your latest saved {labels[metric]} is {value} {units[metric]}, "
            f"recorded on {recorded}."
        )
