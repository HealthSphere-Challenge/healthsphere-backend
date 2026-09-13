from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str
    display_name: str
    created_at: datetime


class ProfilePatch(BaseModel):
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
