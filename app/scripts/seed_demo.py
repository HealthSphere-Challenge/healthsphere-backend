"""Deterministic development/demo data for manual HealthSphere verification."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai_client import HealthSphereAiClient
from app.assessment_service import AssessmentService
from app.core.errors import DomainError
from app.core.settings import Settings, get_settings
from app.db.session import create_database_engine, create_session_factory
from app.models import (
    Conversation,
    ConversationMessage,
    ConversationRole,
    HealthProfile,
    Measurement,
    MetricType,
    SexAtBirth,
    User,
)
from app.services import hash_password, verify_password

SEED_REFERENCE_DATE = date(2026, 9, 15)
DEMO_EMAILS = (
    "demo.complete@example.com",
    "demo.elevated@example.com",
    "demo.incomplete@example.com",
    "demo.assessment@example.com",
    "demo.assistant@example.com",
)
ASSESSMENT_REQUEST_ID = UUID("f5d21b60-7b67-4b19-8d65-19d6022a9c01")


class DemoSeedError(RuntimeError):
    """A safe, user-facing demo seed failure."""


@dataclass(frozen=True)
class MeasurementSeed:
    key: str
    metric: MetricType
    measured_at: datetime
    numeric_value: Decimal | None = None
    systolic: int | None = None
    diastolic: int | None = None


@dataclass(frozen=True)
class PersonaSeed:
    key: str
    email: str
    display_name: str
    date_of_birth: date | None
    sex_at_birth: SexAtBirth | None
    height_cm: float | None
    activity_level: str | None
    typical_sleep_minutes: int | None
    smoking_status: str | None
    measurements: tuple[MeasurementSeed, ...]

    @property
    def user_id(self) -> UUID:
        return demo_id(f"user/{self.key}")

    @property
    def profile_id(self) -> UUID:
        return demo_id(f"profile/{self.key}")


@dataclass
class SeedResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0


def demo_id(key: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"healthsphere-demo/{key}")


def at(day: int) -> datetime:
    return datetime(2026, 8, day, 9, 0, tzinfo=UTC)


PERSONAS = (
    PersonaSeed(
        "complete",
        DEMO_EMAILS[0],
        "Demo Complete",
        date(1990, 1, 15),
        SexAtBirth.female,
        175.0,
        "moderate",
        450,
        "never",
        (
            MeasurementSeed("bp-1", MetricType.blood_pressure, at(1), systolic=124, diastolic=80),
            MeasurementSeed("bp-2", MetricType.blood_pressure, at(8), systolic=121, diastolic=78),
            MeasurementSeed("bp-3", MetricType.blood_pressure, at(15), systolic=118, diastolic=76),
            MeasurementSeed("hr-1", MetricType.heart_rate, at(1), Decimal("66")),
            MeasurementSeed("hr-2", MetricType.heart_rate, at(8), Decimal("68")),
            MeasurementSeed("hr-3", MetricType.heart_rate, at(15), Decimal("70")),
            MeasurementSeed("weight-1", MetricType.weight, at(1), Decimal("73.0")),
            MeasurementSeed("weight-2", MetricType.weight, at(8), Decimal("72.6")),
            MeasurementSeed("weight-3", MetricType.weight, at(15), Decimal("72.0")),
        ),
    ),
    PersonaSeed(
        "elevated",
        DEMO_EMAILS[1],
        "Demo Elevated",
        date(1974, 3, 1),
        SexAtBirth.male,
        174.0,
        "light",
        390,
        "former",
        (
            MeasurementSeed("bp-1", MetricType.blood_pressure, at(2), systolic=142, diastolic=90),
            MeasurementSeed("bp-2", MetricType.blood_pressure, at(9), systolic=145, diastolic=92),
            MeasurementSeed("bp-3", MetricType.blood_pressure, at(16), systolic=148, diastolic=94),
            MeasurementSeed("hr-1", MetricType.heart_rate, at(2), Decimal("74")),
            MeasurementSeed("hr-2", MetricType.heart_rate, at(9), Decimal("76")),
            MeasurementSeed("hr-3", MetricType.heart_rate, at(16), Decimal("78")),
            MeasurementSeed("weight-1", MetricType.weight, at(2), Decimal("87.0")),
            MeasurementSeed("weight-2", MetricType.weight, at(9), Decimal("86.5")),
            MeasurementSeed("weight-3", MetricType.weight, at(16), Decimal("86.0")),
        ),
    ),
    PersonaSeed(
        "incomplete",
        DEMO_EMAILS[2],
        "Demo Incomplete",
        date(1988, 7, 12),
        SexAtBirth.prefer_not_to_say,
        168.0,
        "moderate",
        420,
        "never",
        (MeasurementSeed("weight-1", MetricType.weight, at(10), Decimal("69.0")),),
    ),
    PersonaSeed(
        "assessment",
        DEMO_EMAILS[3],
        "Demo Assessment",
        date(1981, 11, 20),
        SexAtBirth.female,
        165.0,
        "active",
        465,
        "never",
        (
            MeasurementSeed("bp-1", MetricType.blood_pressure, at(12), systolic=132, diastolic=84),
            MeasurementSeed("hr-1", MetricType.heart_rate, at(12), Decimal("72")),
            MeasurementSeed("weight-1", MetricType.weight, at(12), Decimal("67.0")),
        ),
    ),
    PersonaSeed(
        "assistant",
        DEMO_EMAILS[4],
        "Demo Assistant",
        date(1994, 5, 5),
        SexAtBirth.prefer_not_to_say,
        171.0,
        "light",
        420,
        "never",
        (MeasurementSeed("hr-1", MetricType.heart_rate, at(14), Decimal("67")),),
    ),
)


def require_safe_environment(environment: str) -> None:
    if environment not in {"development", "test"}:
        raise DemoSeedError("Demo data is allowed only in development or test environments.")


def _assign(row: object, values: dict[str, object]) -> bool:
    changed = False
    for field, value in values.items():
        if getattr(row, field) != value:
            setattr(row, field, value)
            changed = True
    return changed


def _record(result: SeedResult, created: bool, changed: bool = False) -> None:
    if created:
        result.created += 1
    elif changed:
        result.updated += 1
    else:
        result.skipped += 1


def _owned_user(db: Session, persona: PersonaSeed) -> User | None:
    by_id = db.get(User, persona.user_id)
    by_email = db.scalar(select(User).where(User.email == persona.email))
    if by_id is not None and by_id.email != persona.email:
        raise DemoSeedError(f"Reserved demo identifier collision for {persona.email}.")
    if by_email is not None and by_email.id != persona.user_id:
        raise DemoSeedError(f"Reserved demo email collision for {persona.email}.")
    return by_id or by_email


def seed_demo(db: Session, environment: str, password: str) -> SeedResult:
    require_safe_environment(environment)
    if not 12 <= len(password) <= 128:
        raise DemoSeedError("HEALTHSPHERE_DEMO_PASSWORD must contain 12 to 128 characters.")

    result = SeedResult()
    for persona in PERSONAS:
        user = _owned_user(db, persona)
        if user is None:
            user = User(
                id=persona.user_id,
                email=persona.email,
                password_hash=hash_password(password),
                display_name=persona.display_name,
            )
            db.add(user)
            db.flush()
            _record(result, True)
        else:
            changed = _assign(user, {"display_name": persona.display_name})
            if not verify_password(user.password_hash, password):
                user.password_hash = hash_password(password)
                changed = True
            _record(result, False, changed)

        profile = db.scalar(select(HealthProfile).where(HealthProfile.user_id == user.id))
        profile_values = {
            "date_of_birth": persona.date_of_birth,
            "sex_at_birth": persona.sex_at_birth,
            "height_cm": persona.height_cm,
            "allergies": [],
            "medications": [],
            "medical_conditions": [],
            "activity_level": persona.activity_level,
            "typical_sleep_minutes": persona.typical_sleep_minutes,
            "smoking_status": persona.smoking_status,
        }
        if profile is None:
            profile = HealthProfile(id=persona.profile_id, user_id=user.id, **profile_values)
            db.add(profile)
            _record(result, True)
        elif profile.id != persona.profile_id:
            raise DemoSeedError(f"Profile ownership collision for {persona.email}.")
        else:
            _record(result, False, _assign(profile, profile_values))

        for measurement in persona.measurements:
            identifier = demo_id(f"measurement/{persona.key}/{measurement.key}")
            row = db.get(Measurement, identifier)
            values = {
                "user_id": user.id,
                "metric": measurement.metric,
                "numeric_value": measurement.numeric_value,
                "systolic": measurement.systolic,
                "diastolic": measurement.diastolic,
                "glucose_context": None,
                "measured_at": measurement.measured_at,
                "recorded_at": measurement.measured_at + timedelta(minutes=5),
                "source": "manual",
                "note": "Synthetic HS-021 demo fixture.",
            }
            if row is None:
                db.add(Measurement(id=identifier, **values))
                _record(result, True)
            elif row.user_id != user.id:
                raise DemoSeedError(f"Measurement ownership collision for {persona.email}.")
            else:
                _record(result, False, _assign(row, values))

    _seed_conversation(db, result)
    db.flush()
    return result


def _seed_conversation(db: Session, result: SeedResult) -> None:
    persona = PERSONAS[-1]
    conversation_id = demo_id("conversation/assistant/general")
    created_at = datetime(2026, 9, 15, 10, 0, tzinfo=UTC)
    conversation = db.get(Conversation, conversation_id)
    values = {
        "user_id": persona.user_id,
        "created_at": created_at,
        "updated_at": created_at + timedelta(minutes=1),
        "expires_at": created_at + timedelta(days=30),
    }
    if conversation is None:
        conversation = Conversation(id=conversation_id, **values)
        db.add(conversation)
        _record(result, True)
    elif conversation.user_id != persona.user_id:
        raise DemoSeedError("Conversation ownership collision for the Assistant persona.")
    else:
        _record(result, False, _assign(conversation, values))

    messages = (
        (
            "user",
            "What is blood pressure?",
            None,
            None,
        ),
        (
            "assistant",
            "Blood pressure is the force of circulating blood against artery walls. "
            "This is a synthetic demo response for interface testing.",
            "answer",
            {"source_type": "hs021_demo_fixture"},
        ),
    )
    for index, (role, content, response_type, provenance) in enumerate(messages):
        identifier = demo_id(f"conversation-message/assistant/general/{index}")
        row = db.get(ConversationMessage, identifier)
        message_values = {
            "conversation_id": conversation_id,
            "role": ConversationRole(role),
            "content": content,
            "response_type": response_type,
            "sources": [] if role == "assistant" else None,
            "safety": {"urgent": False, "reason": None} if role == "assistant" else None,
            "uncertainty": None,
            "agent_request_id": None,
            "provenance": provenance,
            "created_at": created_at + timedelta(minutes=index),
        }
        if row is None:
            db.add(ConversationMessage(id=identifier, **message_values))
            _record(result, True)
        elif row.conversation_id != conversation_id:
            raise DemoSeedError("Conversation message ownership collision.")
        else:
            _record(result, False, _assign(row, message_values))


def reset_demo(db: Session, environment: str) -> int:
    require_safe_environment(environment)
    deleted = 0
    for persona in PERSONAS:
        result = db.execute(
            delete(User).where(User.id == persona.user_id, User.email == persona.email)
        )
        deleted += result.rowcount or 0
    return deleted


def prepare_assessment(db: Session, settings: Settings) -> str:
    require_safe_environment(settings.app_environment)
    if not settings.ai_service_url or not settings.ai_internal_token:
        raise DemoSeedError(
            "Assessment preparation requires HEALTHSPHERE_AI_SERVICE_URL and "
            "HEALTHSPHERE_AI_INTERNAL_TOKEN."
        )
    user = _owned_user(db, PERSONAS[3])
    if user is None:
        raise DemoSeedError("Run the base demo seed before preparing an assessment.")
    client = HealthSphereAiClient(
        settings.ai_service_url,
        settings.ai_internal_token,
        settings.ai_timeout_seconds,
        settings.ai_connect_timeout_seconds,
    )
    try:
        response = AssessmentService(db, client).create(user, ASSESSMENT_REQUEST_ID)
    except DomainError as exc:
        raise DemoSeedError(str(exc)) from None
    if response.status != "completed":
        raise DemoSeedError(f"AI assessment preparation returned {response.status}.")
    return str(response.id)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset", action="store_true", help="Delete only deterministic demo users."
    )
    parser.add_argument(
        "--prepare-assessment",
        action="store_true",
        help="Call the configured AI through the real backend assessment service.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    environment = os.getenv("HEALTHSPHERE_APP_ENVIRONMENT", "development").casefold()
    require_safe_environment(environment)
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    factory = create_session_factory(engine)
    try:
        with factory.begin() as db:
            if args.reset:
                deleted = reset_demo(db, settings.app_environment)
                print(f"Demo users removed: {deleted}")
                return 0
            password = settings.demo_password
            if password is None:
                raise DemoSeedError("HEALTHSPHERE_DEMO_PASSWORD is required.")
            result = seed_demo(db, settings.app_environment, password)
        assessment_id = None
        if args.prepare_assessment:
            with factory() as db:
                try:
                    assessment_id = prepare_assessment(db, settings)
                    db.commit()
                except Exception:
                    db.rollback()
                    raise
        print(f"Created: {result.created}")
        print(f"Updated: {result.updated}")
        print(f"Skipped: {result.skipped}")
        print(f"Demo users available: {', '.join(DEMO_EMAILS)}")
        if assessment_id:
            print(f"Assessment prepared: {assessment_id}")
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DemoSeedError as exc:
        raise SystemExit(f"Demo seed refused: {exc}") from None
