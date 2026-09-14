"""Feature construction and assessment orchestration for HS-012."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.ai_client import (
    AiContractError,
    AiFeatures,
    AiInferenceResponse,
    AiTransportError,
    HealthSphereAiClient,
)
from app.core.errors import DomainError
from app.models import HealthProfile, Measurement, MetricType, RiskAssessment, User
from app.repositories import AssessmentRepository, MeasurementRepository, ProfileRepository
from app.schemas import (
    AssessmentListResponse,
    AssessmentReason,
    AssessmentResponse,
    AssessmentResult,
)
from app.services import decode_cursor


@dataclass(frozen=True)
class FeatureBuild:
    features: AiFeatures
    missing_required: list[str]
    age: int | None


def calculate_age(born: date | None, assessed_on: date) -> int | None:
    if born is None:
        return None
    return (
        assessed_on.year
        - born.year
        - ((assessed_on.month, assessed_on.day) < (born.month, born.day))
    )


class HypertensionFeatureBuilder:
    def build(
        self,
        profile: HealthProfile,
        latest: dict[MetricType, Measurement],
        assessed_at: datetime,
    ) -> FeatureBuild:
        age = calculate_age(profile.date_of_birth, assessed_at.astimezone(UTC).date())
        blood_pressure = latest.get(MetricType.blood_pressure)
        heart_rate = latest.get(MetricType.heart_rate)
        weight = latest.get(MetricType.weight)
        systolic = blood_pressure.systolic if blood_pressure else None
        diastolic = blood_pressure.diastolic if blood_pressure else None
        bmi = None
        if weight is not None and profile.height_cm:
            numeric_weight = weight.numeric_value
            if numeric_weight is not None:
                bmi = round(float(numeric_weight) / (profile.height_cm / 100) ** 2, 2)
        sex = getattr(profile.sex_at_birth, "value", profile.sex_at_birth)
        if sex not in {"female", "male"}:
            sex = "unknown"
        smoking = profile.smoking_status
        if smoking not in {"never", "former", "current"}:
            smoking = "unknown"
        features = AiFeatures(
            age_years=float(age) if age is not None else None,
            systolic_blood_pressure=float(systolic) if systolic is not None else None,
            diastolic_blood_pressure=float(diastolic) if diastolic is not None else None,
            heart_rate=(float(heart_rate.numeric_value) if heart_rate is not None else None),
            bmi=bmi,
            sex_at_birth=sex,
            smoking_status=smoking,
        )
        required = ("age_years", "systolic_blood_pressure", "diastolic_blood_pressure")
        missing = [name for name in required if getattr(features, name) is None]
        return FeatureBuild(features=features, missing_required=missing, age=age)


def assessment_response(assessment: RiskAssessment) -> AssessmentResponse:
    return AssessmentResponse(
        id=assessment.id,
        status="completed",
        result=AssessmentResult(
            target_id=assessment.target_id,
            feature_schema_version=assessment.feature_schema_version,
            model_version=assessment.model_version,
            preprocessing_version=assessment.preprocessing_version,
            prediction_horizon_days=assessment.prediction_horizon_days,
            score=float(assessment.score),
            score_type=assessment.score_type,
            calibrated=assessment.calibrated,
        ),
        reason=None,
        created_at=assessment.created_at.astimezone(UTC),
    )


class AssessmentService:
    PAGE_SIZE = 50

    def __init__(self, db: Session, ai_client: HealthSphereAiClient | None = None):
        self.db = db
        self.ai_client = ai_client
        self.assessments = AssessmentRepository(db)
        self.profiles = ProfileRepository(db)
        self.measurements = MeasurementRepository(db)
        self.builder = HypertensionFeatureBuilder()

    def create(self, user: User, request_id: UUID) -> AssessmentResponse:
        if self.ai_client is None:
            raise RuntimeError("AI client is required to create an assessment")
        existing = self.assessments.by_request_for_user(request_id, user.id)
        if existing is not None:
            return assessment_response(existing)
        assessed_at = datetime.now(UTC)
        profile = self.profiles.by_user_id(user.id)
        if profile is None:
            raise DomainError(404, "resource_not_found", "Profile was not found.")
        built = self.builder.build(
            profile, self.measurements.latest_by_metric(user.id), assessed_at
        )
        if built.missing_required:
            return self._outcome(
                request_id,
                assessed_at,
                "insufficient_data",
                "minimum_inputs_missing",
                built.missing_required,
            )
        if built.age is not None and built.age < 18:
            return self._outcome(request_id, assessed_at, "ineligible", "adult_population_required")

        # End the read/authentication transaction before the remote network call.
        self.db.commit()
        try:
            remote = self.ai_client.infer(request_id, uuid4(), built.features)
        except AiTransportError as exc:
            raise DomainError(
                503, "ai_unavailable", "The assessment service is unavailable."
            ) from exc
        except AiContractError as exc:
            raise DomainError(
                502, "ai_contract_error", "The assessment response was incompatible."
            ) from exc
        if remote.status != "completed":
            assert remote.reason is not None
            return self._outcome(
                request_id,
                assessed_at,
                remote.status,
                remote.reason.code,
                remote.reason.missing_fields,
            )
        return self._persist_completed(user.id, request_id, assessed_at, built.features, remote)

    def _persist_completed(
        self,
        user_id: UUID,
        request_id: UUID,
        assessed_at: datetime,
        features: AiFeatures,
        remote: AiInferenceResponse,
    ) -> AssessmentResponse:
        assert remote.result is not None and remote.provenance is not None
        assessment = RiskAssessment(
            user_id=user_id,
            request_id=request_id,
            target_id=remote.result.target,
            feature_schema_version=remote.provenance.feature_schema_version,
            model_version=remote.provenance.model_version,
            preprocessing_version=remote.provenance.preprocessing_version,
            prediction_horizon_days=remote.provenance.prediction_horizon_days,
            score=Decimal(str(remote.result.score)),
            score_type=remote.result.score_type,
            calibrated=remote.result.calibrated,
            input_snapshot=features.model_dump(),
            provenance_snapshot=remote.provenance.model_dump(mode="json"),
            created_at=assessed_at,
        )
        self.assessments.add(assessment)
        return assessment_response(assessment)

    @staticmethod
    def _outcome(
        request_id: UUID,
        created_at: datetime,
        status: str,
        code: str,
        missing_fields: list[str] | None = None,
    ) -> AssessmentResponse:
        return AssessmentResponse(
            id=request_id,
            status=status,
            result=None,
            reason=AssessmentReason(code=code, missing_fields=missing_fields),
            created_at=created_at,
        )

    def get(self, user: User, assessment_id: UUID) -> AssessmentResponse:
        assessment = self.assessments.by_id_for_user(assessment_id, user.id)
        if assessment is None:
            raise DomainError(404, "resource_not_found", "Assessment was not found.")
        return assessment_response(assessment)

    def list(self, user: User, cursor: str | None) -> AssessmentListResponse:
        rows = self.assessments.list_for_user(user.id, decode_cursor(cursor), self.PAGE_SIZE + 1)
        has_more = len(rows) > self.PAGE_SIZE
        visible = rows[: self.PAGE_SIZE]
        return AssessmentListResponse(
            items=[assessment_response(row) for row in visible],
            next_cursor=self._encode_cursor(visible[-1]) if has_more else None,
        )

    @staticmethod
    def _encode_cursor(assessment: RiskAssessment) -> str:
        payload = json.dumps(
            [assessment.created_at.isoformat(), str(assessment.id)], separators=(",", ":")
        ).encode()
        return base64.urlsafe_b64encode(payload).decode().rstrip("=")
