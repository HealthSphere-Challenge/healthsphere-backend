import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.core.settings import Settings
from app.models import HealthProfile, SessionRecord, User
from app.repositories import AuthRepository, ProfileRepository
from app.schemas import ProfilePatch, RegisterRequest

_passwords = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


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
            password_hash=_passwords.hash(request.password),
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
        stored = user.password_hash if user else _passwords.hash("invalid credential padding")
        try:
            valid = _passwords.verify(stored, password)
        except (VerifyMismatchError, InvalidHashError):
            valid = False
        if not user or not valid:
            raise DomainError(401, "invalid_credentials", "Email or password is incorrect.")
        if _passwords.check_needs_rehash(user.password_hash):
            user.password_hash = _passwords.hash(password)
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
