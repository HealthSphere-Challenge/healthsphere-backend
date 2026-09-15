import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.assessment_service import HypertensionFeatureBuilder
from app.db.session import create_database_engine, create_session_factory
from app.models import (
    Conversation,
    ConversationMessage,
    HealthProfile,
    Measurement,
    MetricType,
    RiskAssessment,
    User,
)
from app.repositories import MeasurementRepository
from app.scripts.seed_demo import DEMO_EMAILS, PERSONAS, reset_demo, seed_demo
from app.services import hash_password, verify_password

pytestmark = pytest.mark.integration


@pytest.fixture
def demo_db():
    engine = create_database_engine(os.environ["TEST_DATABASE_URL"])
    factory = create_session_factory(engine)
    with factory.begin() as db:
        reset_demo(db, "test")
    try:
        yield factory
    finally:
        with factory.begin() as db:
            reset_demo(db, "test")
        engine.dispose()


def test_seed_is_idempotent_owned_hashed_and_assessment_ready(demo_db) -> None:
    password = "Local-Demo-Only-42"
    with demo_db.begin() as db:
        first = seed_demo(db, "test", password)
    with demo_db.begin() as db:
        second = seed_demo(db, "test", password)

    assert first.created > 0
    assert second.created == 0
    assert second.updated == 0
    with demo_db() as db:
        users = list(db.scalars(select(User).where(User.email.in_(DEMO_EMAILS))))
        assert len(users) == len(PERSONAS)
        assert {user.id for user in users} == {persona.user_id for persona in PERSONAS}
        assert all(user.password_hash != password for user in users)
        assert all(user.password_hash.startswith("$argon2id$") for user in users)
        assert all(verify_password(user.password_hash, password) for user in users)

        profiles = list(
            db.scalars(
                select(HealthProfile).where(HealthProfile.user_id.in_([u.id for u in users]))
            )
        )
        assert len(profiles) == len(PERSONAS)
        assert {profile.user_id for profile in profiles} == {user.id for user in users}
        assert all(profile.medical_conditions == [] for profile in profiles)

        measurements = list(
            db.scalars(select(Measurement).where(Measurement.user_id.in_([u.id for u in users])))
        )
        assert len(measurements) == sum(len(persona.measurements) for persona in PERSONAS)
        assert all(
            measurement.user_id in {user.id for user in users} for measurement in measurements
        )
        assert all(
            measurement.note == "Synthetic HS-021 demo fixture." for measurement in measurements
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(RiskAssessment)
                .where(RiskAssessment.user_id.in_([user.id for user in users]))
            )
            == 0
        )


def test_seed_history_order_incomplete_ml_and_conversation_fixture(demo_db) -> None:
    with demo_db.begin() as db:
        seed_demo(db, "test", "Local-Demo-Only-42")

    with demo_db() as db:
        complete = db.get(User, PERSONAS[0].user_id)
        assert complete is not None
        weights = list(
            db.scalars(
                select(Measurement)
                .where(
                    Measurement.user_id == complete.id,
                    Measurement.metric == MetricType.weight,
                )
                .order_by(Measurement.measured_at)
            )
        )
        assert [float(row.numeric_value) for row in weights] == [73.0, 72.6, 72.0]
        assert [row.measured_at for row in weights] == sorted(row.measured_at for row in weights)

        incomplete = db.get(User, PERSONAS[2].user_id)
        assert incomplete is not None
        profile = db.scalar(select(HealthProfile).where(HealthProfile.user_id == incomplete.id))
        assert profile is not None
        built = HypertensionFeatureBuilder().build(
            profile,
            MeasurementRepository(db).latest_by_metric(incomplete.id),
            datetime(2026, 9, 15, tzinfo=UTC),
        )
        assert built.missing_required == [
            "systolic_blood_pressure",
            "diastolic_blood_pressure",
        ]

        conversation = db.scalar(
            select(Conversation).where(Conversation.user_id == PERSONAS[4].user_id)
        )
        assert conversation is not None
        messages = list(
            db.scalars(
                select(ConversationMessage)
                .where(ConversationMessage.conversation_id == conversation.id)
                .order_by(ConversationMessage.created_at)
            )
        )
        assert [message.role.value for message in messages] == ["user", "assistant"]
        assert messages[1].provenance == {"source_type": "hs021_demo_fixture"}
        assert messages[1].agent_request_id is None


def test_reset_removes_only_exact_demo_identities(demo_db) -> None:
    unrelated_id = uuid4()
    with demo_db.begin() as db:
        seed_demo(db, "test", "Local-Demo-Only-42")
        db.add(
            User(
                id=unrelated_id,
                email="unrelated@example.test",
                password_hash=hash_password("Unrelated-Test-Only-42"),
                display_name="Unrelated",
            )
        )
    with demo_db.begin() as db:
        assert reset_demo(db, "test") == len(PERSONAS)
    with demo_db() as db:
        assert db.get(User, unrelated_id) is not None
        assert (
            db.scalar(select(func.count()).select_from(User).where(User.email.in_(DEMO_EMAILS)))
            == 0
        )
    with demo_db.begin() as db:
        db.delete(db.get(User, unrelated_id))
