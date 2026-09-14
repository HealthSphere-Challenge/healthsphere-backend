from datetime import UTC, date, datetime
from typing import Literal
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str
    display_name: str
    created_at: datetime


class ProfilePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date_of_birth: date | None = None
    sex_at_birth: Literal["female", "male", "intersex", "prefer_not_to_say"] | None = None
    height_cm: float | None = Field(default=None, ge=50, le=260)
    allergies: list[str] | None = None
    medications: list[str] | None = None
    medical_conditions: list[str] | None = Field(
        default=None, validation_alias=AliasChoices("medical_conditions", "chronic_conditions")
    )
    activity_level: Literal["sedentary", "light", "moderate", "active", "very_active"] | None = None
    typical_sleep_minutes: int | None = Field(default=None, ge=0, le=1440)
    smoking_status: Literal["never", "former", "current", "prefer_not_to_say"] | None = None

    @field_validator("allergies", "medications", "medical_conditions")
    @classmethod
    def validate_lists(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        cleaned = [item.strip() for item in value]
        if len(cleaned) > 50 or any(not item or len(item) > 100 for item in cleaned):
            raise ValueError("Provide at most 50 non-empty values of 100 characters or fewer")
        return cleaned


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    date_of_birth: date | None
    sex_at_birth: str | None
    height_cm: float | None
    allergies: list[str] | None
    medications: list[str] | None
    medical_conditions: list[str] | None
    activity_level: str | None
    typical_sleep_minutes: int | None
    smoking_status: str | None
    age_years: int | None = None
    latest_weight: None = None
    bmi: None = None
    updated_at: datetime


class AccountResponse(BaseModel):
    user: UserResponse
    profile: ProfileResponse
    csrf_token: str


MetricName = Literal[
    "heart_rate",
    "blood_pressure",
    "weight",
    "blood_glucose",
    "sleep_duration",
    "physical_activity_duration",
]
GlucoseContextValue = Literal["fasting", "postprandial", "random", "unknown"]


class BloodPressureValue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    systolic: int = Field(strict=True, gt=0)
    diastolic: int = Field(strict=True, gt=0)


class MeasurementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metric: MetricName
    value: int | float | BloodPressureValue
    unit: Literal["bpm", "mmHg", "kg", "mg/dL", "min"]
    context: GlucoseContextValue | None = None
    measured_at: datetime
    source: Literal["manual"] = "manual"
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("measured_at")
    @classmethod
    def explicit_offset(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Provide an RFC 3339 timestamp with an explicit offset")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def metric_shape(self) -> "MeasurementCreate":
        expected_units = {
            "heart_rate": "bpm",
            "blood_pressure": "mmHg",
            "weight": "kg",
            "blood_glucose": "mg/dL",
            "sleep_duration": "min",
            "physical_activity_duration": "min",
        }
        if self.unit != expected_units[self.metric]:
            raise ValueError("Use the canonical unit for this metric")
        if self.metric == "blood_pressure":
            if not isinstance(self.value, BloodPressureValue):
                raise ValueError("Blood pressure requires paired systolic and diastolic integers")
        elif isinstance(self.value, (BloodPressureValue, bool)):
            raise ValueError("This metric requires one positive numeric value")
        elif self.value <= 0:
            raise ValueError("Measurement values must be positive")
        if self.metric == "blood_glucose" and self.context is None:
            raise ValueError("Blood glucose context is required")
        if self.metric != "blood_glucose" and self.context is not None:
            raise ValueError("Context is only supported for blood glucose")
        if self.metric in {
            "heart_rate",
            "sleep_duration",
            "physical_activity_duration",
        } and (not isinstance(self.value, int) or isinstance(self.value, bool)):
            raise ValueError("This metric requires an integer value")
        return self


class MeasurementResponse(BaseModel):
    id: UUID
    metric: MetricName | Literal["bmi"]
    value: float | int | BloodPressureValue
    unit: Literal["bpm", "mmHg", "kg", "kg/m2", "mg/dL", "min"]
    context: GlucoseContextValue | None
    measured_at: datetime
    recorded_at: datetime
    source: Literal["manual", "derived"]
    note: str | None


class MeasurementListResponse(BaseModel):
    items: list[MeasurementResponse]
    next_cursor: str | None


class BmiProjection(BaseModel):
    value: float
    unit: Literal["kg/m2"] = "kg/m2"
    derived_from_measurement_id: UUID


class DashboardResponse(BaseModel):
    generated_at: datetime
    latest_measurements: dict[str, MeasurementResponse | BmiProjection | None]
    latest_assessment: "AssessmentResponse | None" = None


class AssessmentResult(BaseModel):
    target_id: Literal["incident_essential_hypertension_5y_v1"]
    feature_schema_version: Literal["hypertension_features_v1"]
    model_version: Literal["hypertension_5y_v1.0.0"]
    preprocessing_version: Literal["hypertension_preprocessing_v1"]
    prediction_horizon_days: Literal[1825]
    score: float = Field(ge=0, le=1, allow_inf_nan=False)
    score_type: Literal["uncalibrated_experimental_probability_estimate"]
    calibrated: Literal[False]
    data_source_type: Literal["synthetic_model"] = "synthetic_model"


class AssessmentReason(BaseModel):
    code: str
    missing_fields: list[str] | None = None


class AssessmentResponse(BaseModel):
    id: UUID
    status: Literal["completed", "insufficient_data", "ineligible", "unavailable"]
    result: AssessmentResult | None
    reason: AssessmentReason | None
    created_at: datetime


class AssessmentListResponse(BaseModel):
    items: list[AssessmentResponse]
    next_cursor: str | None
