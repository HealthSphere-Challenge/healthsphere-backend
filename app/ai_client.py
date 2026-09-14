"""Typed consumer for the authoritative HS-002 backend-to-AI contract."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

TARGET_ID = "incident_essential_hypertension_5y_v1"
FEATURE_SCHEMA = "hypertension_features_v1"
MODEL_VERSION = "hypertension_5y_v1.0.0"
PREPROCESSING_VERSION = "hypertension_preprocessing_v1"
SCORE_TYPE = "uncalibrated_experimental_probability_estimate"


class AiContractError(RuntimeError):
    pass


class AiTransportError(RuntimeError):
    pass


class AiFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")
    age_years: float | None
    systolic_blood_pressure: float | None
    diastolic_blood_pressure: float | None
    heart_rate: float | None
    bmi: float | None
    sex_at_birth: Literal["male", "female", "unknown"]
    smoking_status: Literal["never", "former", "current", "unknown"]


class AiReason(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    missing_fields: list[str] | None = None


class AiResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target: Literal["incident_essential_hypertension_5y_v1"]
    population: str
    horizon: str
    score: float = Field(ge=0, le=1, allow_inf_nan=False)
    score_type: Literal["uncalibrated_experimental_probability_estimate"]
    calibrated: Literal[False]
    label: None
    explanation: None
    limitations: list[str]


class AiProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_name: str
    model_version: Literal["hypertension_5y_v1.0.0"]
    feature_schema_version: Literal["hypertension_features_v1"]
    preprocessing_version: Literal["hypertension_preprocessing_v1"]
    calibration_version: None
    explanation_method: str
    prediction_horizon_days: Literal[1825]
    calibrated: Literal[False]
    calibration_status: str
    generated_at: datetime


class AiInferenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"]
    request_id: UUID
    status: Literal["completed", "insufficient_data", "ineligible", "unavailable"]
    result: AiResult | None
    reason: AiReason | None
    provenance: AiProvenance | None

    @model_validator(mode="after")
    def validate_status_shape(self) -> AiInferenceResponse:
        if self.status == "completed":
            if self.result is None or self.provenance is None or self.reason is not None:
                raise ValueError("completed response requires result and provenance only")
        elif self.result is not None or self.reason is None or self.provenance is not None:
            raise ValueError("non-completed response requires a reason and no result/provenance")
        return self


class HealthSphereAiClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        timeout_seconds: float = 10.0,
        connect_timeout_seconds: float = 2.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = httpx.Timeout(timeout_seconds, connect=connect_timeout_seconds)
        self.transport = transport

    def infer(
        self, request_id: UUID, subject_ref: UUID, features: AiFeatures
    ) -> AiInferenceResponse:
        body = {
            "schema_version": "1.0",
            "request_id": str(request_id),
            "subject_ref": str(subject_ref),
            "features": features.model_dump(),
        }
        try:
            with httpx.Client(
                base_url=self.base_url, timeout=self.timeout, transport=self.transport
            ) as client:
                response = client.post(
                    "/internal/v1/inferences",
                    json=body,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "X-Request-ID": str(request_id),
                    },
                )
                response.raise_for_status()
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise AiTransportError("AI service could not be reached.") from exc
        except httpx.HTTPStatusError as exc:
            raise AiTransportError("AI service rejected the request.") from exc
        try:
            parsed = AiInferenceResponse.model_validate(response.json())
        except (ValueError, TypeError) as exc:
            raise AiContractError("AI response is incompatible.") from exc
        if parsed.request_id != request_id:
            raise AiContractError("AI response request ID does not match.")
        return parsed
