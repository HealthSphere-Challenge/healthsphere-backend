from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models import HealthProfile, Measurement, MetricType, RiskAssessment, SessionRecord, User


class AuthRepository:
    def __init__(self, db: Session):
        self.db = db

    def user_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def user_by_id(self, user_id: UUID) -> User | None:
        return self.db.get(User, user_id)

    def session_by_hash(self, token_hash: str) -> SessionRecord | None:
        return self.db.scalar(select(SessionRecord).where(SessionRecord.token_hash == token_hash))

    def add_user(self, user: User) -> None:
        self.db.add(user)
        self.db.flush()

    def add_session(self, record: SessionRecord) -> None:
        self.db.add(record)
        self.db.flush()

    def revoke(self, record: SessionRecord, now: datetime) -> None:
        record.revoked_at = now
        self.db.flush()


class ProfileRepository:
    def __init__(self, db: Session):
        self.db = db

    def by_user_id(self, user_id: UUID) -> HealthProfile | None:
        return self.db.scalar(select(HealthProfile).where(HealthProfile.user_id == user_id))

    def add(self, profile: HealthProfile) -> None:
        self.db.add(profile)
        self.db.flush()


class MeasurementRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, measurement: Measurement) -> None:
        self.db.add(measurement)
        self.db.flush()

    def by_id_for_user(self, measurement_id: UUID, user_id: UUID) -> Measurement | None:
        return self.db.scalar(
            select(Measurement).where(
                Measurement.id == measurement_id, Measurement.user_id == user_id
            )
        )

    def list_for_user(
        self, user_id: UUID, cursor: tuple[datetime, UUID] | None, limit: int
    ) -> list[Measurement]:
        statement = select(Measurement).where(Measurement.user_id == user_id)
        if cursor:
            measured_at, measurement_id = cursor
            statement = statement.where(
                or_(
                    Measurement.measured_at < measured_at,
                    and_(
                        Measurement.measured_at == measured_at,
                        Measurement.id < measurement_id,
                    ),
                )
            )
        return list(
            self.db.scalars(
                statement.order_by(Measurement.measured_at.desc(), Measurement.id.desc()).limit(
                    limit
                )
            )
        )

    def latest_by_metric(self, user_id: UUID) -> dict[MetricType, Measurement]:
        rows = self.db.scalars(
            select(Measurement)
            .where(Measurement.user_id == user_id)
            .order_by(Measurement.measured_at.desc(), Measurement.id.desc())
        )
        latest: dict[MetricType, Measurement] = {}
        for row in rows:
            latest.setdefault(row.metric, row)
        return latest


class AssessmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, assessment: RiskAssessment) -> None:
        self.db.add(assessment)
        self.db.flush()

    def by_request_for_user(self, request_id: UUID, user_id: UUID) -> RiskAssessment | None:
        return self.db.scalar(
            select(RiskAssessment).where(
                RiskAssessment.request_id == request_id, RiskAssessment.user_id == user_id
            )
        )

    def by_id_for_user(self, assessment_id: UUID, user_id: UUID) -> RiskAssessment | None:
        return self.db.scalar(
            select(RiskAssessment).where(
                RiskAssessment.id == assessment_id, RiskAssessment.user_id == user_id
            )
        )

    def list_for_user(
        self, user_id: UUID, cursor: tuple[datetime, UUID] | None, limit: int
    ) -> list[RiskAssessment]:
        statement = select(RiskAssessment).where(RiskAssessment.user_id == user_id)
        if cursor:
            created_at, assessment_id = cursor
            statement = statement.where(
                or_(
                    RiskAssessment.created_at < created_at,
                    and_(
                        RiskAssessment.created_at == created_at,
                        RiskAssessment.id < assessment_id,
                    ),
                )
            )
        return list(
            self.db.scalars(
                statement.order_by(
                    RiskAssessment.created_at.desc(), RiskAssessment.id.desc()
                ).limit(limit)
            )
        )
