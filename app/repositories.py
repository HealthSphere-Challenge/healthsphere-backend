from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import HealthProfile, SessionRecord, User


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
