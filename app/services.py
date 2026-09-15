import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.core.settings import Settings
from app.models import GlucoseContext, HealthProfile, Measurement, MetricType, SessionRecord, User
from app.repositories import AuthRepository, MeasurementRepository, ProfileRepository
from app.schemas import (
    BloodPressureValue,
    BmiProjection,
    MeasurementCreate,
    MeasurementListResponse,
    MeasurementResponse,
    ProfilePatch,
    RegisterRequest,
)

_passwords = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


def hash_password(password: str) -> str:
    """Hash a password with the application's authoritative password hasher."""
    return _passwords.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Verify a password without exposing Argon2 details to callers."""
    try:
        return _passwords.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


@dataclass
class AuthenticatedSession:
    user: User
    record: SessionRecord
    session_token: str | None = None
    csrf_token: str | None = None


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class AuthService:
    def __init__(self, db: Session, settings: Settings):
        self.settings = settings
        self.auth = AuthRepository(db)
        self.profiles = ProfileRepository(db)

    def register(self, request: RegisterRequest) -> AuthenticatedSession:
        email = normalize_email(str(request.email))
        if self.auth.user_by_email(email):
            raise DomainError(
                409, "email_already_registered", "An account already uses this email address."
            )
        user = User(
            email=email,
            password_hash=hash_password(request.password),
            display_name=request.display_name.strip(),
        )
        try:
            self.auth.add_user(user)
            self.profiles.add(HealthProfile(user_id=user.id))
        except IntegrityError as exc:
            raise DomainError(
                409, "email_already_registered", "An account already uses this email address."
            ) from exc
        return self._create_session(user)

    def login(self, email: str, password: str) -> AuthenticatedSession:
        user = self.auth.user_by_email(normalize_email(email))
        stored = user.password_hash if user else hash_password("invalid credential padding")
        valid = verify_password(stored, password)
        if not user or not valid:
            raise DomainError(401, "invalid_credentials", "Email or password is incorrect.")
        if _passwords.check_needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
        return self._create_session(user)

    def _create_session(self, user: User) -> AuthenticatedSession:
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        record = SessionRecord(
            user_id=user.id,
            token_hash=digest(token),
            csrf_hash=digest(csrf),
            created_at=now,
            last_used_at=now,
            expires_at=now + timedelta(seconds=self.settings.session_absolute_seconds),
        )
        self.auth.add_session(record)
        return AuthenticatedSession(user, record, token, csrf)

    def authenticate(self, token: str | None) -> AuthenticatedSession:
        if not token:
            raise DomainError(401, "authentication_required", "Authentication is required.")
        record = self.auth.session_by_hash(digest(token))
        now = datetime.now(UTC)
        if not record or record.revoked_at or record.expires_at <= now:
            raise DomainError(401, "session_expired", "The session is invalid or expired.")
        if record.last_used_at + timedelta(seconds=self.settings.session_idle_seconds) <= now:
            record.revoked_at = now
            raise DomainError(401, "session_expired", "The session is invalid or expired.")
        user = self.auth.user_by_id(record.user_id)
        if not user:
            raise DomainError(401, "authentication_required", "Authentication is required.")
        record.last_used_at = now
        return AuthenticatedSession(user, record)

    def require_csrf(self, authenticated: AuthenticatedSession, csrf: str | None) -> None:
        if not csrf or not hmac.compare_digest(authenticated.record.csrf_hash, digest(csrf)):
            raise DomainError(403, "csrf_failed", "CSRF validation failed.")

    def revoke(self, authenticated: AuthenticatedSession) -> None:
        self.auth.revoke(authenticated.record, datetime.now(UTC))


def age_years(born: date | None, today: date | None = None) -> int | None:
    if born is None:
        return None
    current = today or datetime.now(UTC).date()
    return current.year - born.year - ((current.month, current.day) < (born.month, born.day))


class ProfileService:
    def __init__(self, db: Session):
        self.repo = ProfileRepository(db)

    def get(self, user: User) -> HealthProfile:
        profile = self.repo.by_user_id(user.id)
        if not profile:
            raise DomainError(404, "resource_not_found", "Profile was not found.")
        return profile

    def patch(self, user: User, request: ProfilePatch) -> HealthProfile:
        profile = self.get(user)
        updates = request.model_dump(exclude_unset=True)
        if (
            "date_of_birth" in updates
            and updates["date_of_birth"] is not None
            and age_years(updates["date_of_birth"]) < 18
        ):
            raise DomainError(
                422, "validation_error", "HealthSphere accounts require an age of 18 or older."
            )
        for field, value in updates.items():
            setattr(profile, field, value)
        return profile


UNITS = {
    MetricType.heart_rate: "bpm",
    MetricType.blood_pressure: "mmHg",
    MetricType.weight: "kg",
    MetricType.blood_glucose: "mg/dL",
    MetricType.sleep_duration: "min",
    MetricType.physical_activity_duration: "min",
}


def measurement_response(measurement: Measurement) -> MeasurementResponse:
    if measurement.metric == MetricType.blood_pressure:
        value: float | int | BloodPressureValue = BloodPressureValue(
            systolic=measurement.systolic, diastolic=measurement.diastolic
        )
    elif measurement.metric in {
        MetricType.heart_rate,
        MetricType.sleep_duration,
        MetricType.physical_activity_duration,
    }:
        value = int(measurement.numeric_value)
    else:
        value = float(measurement.numeric_value)
    return MeasurementResponse(
        id=measurement.id,
        metric=measurement.metric.value,
        value=value,
        unit=UNITS[measurement.metric],
        context=(
            measurement.glucose_context.value
            if isinstance(measurement.glucose_context, GlucoseContext)
            else measurement.glucose_context
        ),
        measured_at=measurement.measured_at.astimezone(UTC),
        recorded_at=measurement.recorded_at.astimezone(UTC),
        source="manual",
        note=measurement.note,
    )


def encode_cursor(measurement: Measurement) -> str:
    payload = json.dumps(
        [measurement.measured_at.isoformat(), str(measurement.id)], separators=(",", ":")
    ).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def decode_cursor(cursor: str | None) -> tuple[datetime, UUID] | None:
    if cursor is None:
        return None
    try:
        payload = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        timestamp, identifier = json.loads(payload)
        parsed = datetime.fromisoformat(timestamp)
        if parsed.tzinfo is None:
            raise ValueError
        return parsed, UUID(identifier)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise DomainError(400, "invalid_request", "The pagination cursor is invalid.") from exc


class MeasurementService:
    PAGE_SIZE = 50

    def __init__(self, db: Session):
        self.repo = MeasurementRepository(db)
        self.profiles = ProfileRepository(db)

    def create(self, user: User, request: MeasurementCreate) -> MeasurementResponse:
        metric = MetricType(request.metric)
        if metric == MetricType.blood_pressure:
            assert isinstance(request.value, BloodPressureValue)
            numeric, systolic, diastolic = None, request.value.systolic, request.value.diastolic
        else:
            assert not isinstance(request.value, BloodPressureValue)
            numeric, systolic, diastolic = Decimal(str(request.value)), None, None
        measurement = Measurement(
            user_id=user.id,
            metric=metric,
            numeric_value=numeric,
            systolic=systolic,
            diastolic=diastolic,
            glucose_context=request.context,
            measured_at=request.measured_at,
            source="manual",
            note=request.note,
        )
        self.repo.add(measurement)
        return measurement_response(measurement)

    def get(self, user: User, measurement_id: UUID) -> MeasurementResponse:
        measurement = self.repo.by_id_for_user(measurement_id, user.id)
        if measurement is None:
            raise DomainError(404, "resource_not_found", "Measurement was not found.")
        return measurement_response(measurement)

    def list(self, user: User, cursor: str | None) -> MeasurementListResponse:
        rows = self.repo.list_for_user(user.id, decode_cursor(cursor), self.PAGE_SIZE + 1)
        has_more = len(rows) > self.PAGE_SIZE
        visible = rows[: self.PAGE_SIZE]
        return MeasurementListResponse(
            items=[measurement_response(row) for row in visible],
            next_cursor=encode_cursor(visible[-1]) if has_more else None,
        )

    def dashboard(
        self, user: User
    ) -> tuple[dict[str, MeasurementResponse | BmiProjection | None], datetime]:
        latest = self.repo.latest_by_metric(user.id)
        values: dict[str, MeasurementResponse | BmiProjection | None] = {
            metric.value: measurement_response(latest[metric]) if metric in latest else None
            for metric in MetricType
        }
        weight = latest.get(MetricType.weight)
        profile = self.profiles.by_user_id(user.id)
        bmi = None
        if weight and profile and profile.height_cm:
            bmi = BmiProjection(
                value=round(float(weight.numeric_value) / (profile.height_cm / 100) ** 2, 2),
                derived_from_measurement_id=weight.id,
            )
        values["bmi"] = bmi
        return values, datetime.now(UTC)
