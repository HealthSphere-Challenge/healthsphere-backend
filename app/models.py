from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SexAtBirth(StrEnum):
    female = "female"
    male = "male"
    intersex = "intersex"
    prefer_not_to_say = "prefer_not_to_say"


class MetricType(StrEnum):
    heart_rate = "heart_rate"
    blood_pressure = "blood_pressure"
    weight = "weight"
    blood_glucose = "blood_glucose"
    sleep_duration = "sleep_duration"
    physical_activity_duration = "physical_activity_duration"


class GlucoseContext(StrEnum):
    fasting = "fasting"
    postprandial = "postprandial"
    random = "random"
    unknown = "unknown"


class User(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    profile: Mapped["HealthProfile"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    __table_args__ = (CheckConstraint("email = lower(email)", name="ck_users_email_normalized"),)


class SessionRecord(Base):
    __tablename__ = "sessions"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    csrf_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        Index("ix_sessions_user_active", "user_id", "revoked_at"),
        Index("ix_sessions_expires_at", "expires_at"),
    )


class HealthProfile(Base):
    __tablename__ = "health_profiles"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    sex_at_birth: Mapped[SexAtBirth | None] = mapped_column(Enum(SexAtBirth, name="sex_at_birth"))
    height_cm: Mapped[float | None] = mapped_column(Float)
    allergies: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    medications: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    medical_conditions: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    activity_level: Mapped[str | None] = mapped_column(String(32))
    typical_sleep_minutes: Mapped[int | None]
    smoking_status: Mapped[str | None] = mapped_column(String(32))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    user: Mapped[User] = relationship(back_populates="profile")
    __table_args__ = (UniqueConstraint("user_id", name="uq_health_profiles_user_id"),)


class Measurement(Base):
    __tablename__ = "measurements"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    metric: Mapped[MetricType] = mapped_column(Enum(MetricType, name="metric_type"))
    numeric_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    systolic: Mapped[int | None] = mapped_column(Integer)
    diastolic: Mapped[int | None] = mapped_column(Integer)
    glucose_context: Mapped[GlucoseContext | None] = mapped_column(
        Enum(GlucoseContext, name="glucose_context")
    )
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    note: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        CheckConstraint(
            "numeric_value IS NULL OR numeric_value > 0", name="ck_measurements_positive_numeric"
        ),
        CheckConstraint(
            "systolic IS NULL OR systolic > 0", name="ck_measurements_positive_systolic"
        ),
        CheckConstraint(
            "diastolic IS NULL OR diastolic > 0", name="ck_measurements_positive_diastolic"
        ),
        CheckConstraint(
            "(metric = 'blood_pressure' AND numeric_value IS NULL "
            "AND systolic IS NOT NULL AND diastolic IS NOT NULL) OR "
            "(metric <> 'blood_pressure' AND numeric_value IS NOT NULL "
            "AND systolic IS NULL AND diastolic IS NULL)",
            name="ck_measurements_value_shape",
        ),
        CheckConstraint(
            "(metric = 'blood_glucose' AND glucose_context IS NOT NULL) OR "
            "(metric <> 'blood_glucose' AND glucose_context IS NULL)",
            name="ck_measurements_context_shape",
        ),
        Index("ix_measurements_user_measured", "user_id", "measured_at", "id"),
    )


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    request_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    target_id: Mapped[str] = mapped_column(String(80), nullable=False)
    feature_schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    preprocessing_version: Mapped[str] = mapped_column(String(80), nullable=False)
    prediction_horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(12, 10), nullable=False)
    score_type: Mapped[str] = mapped_column(String(80), nullable=False)
    calibrated: Mapped[bool] = mapped_column(Boolean, nullable=False)
    input_snapshot: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    provenance_snapshot: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 1", name="ck_risk_assessments_score_range"),
        UniqueConstraint("user_id", "request_id", name="uq_risk_assessments_user_request"),
        Index("ix_risk_assessments_user_created", "user_id", "created_at", "id"),
    )
