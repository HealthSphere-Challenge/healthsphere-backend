from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared metadata root for approved future models."""


from app import models as models  # noqa: E402,F401
