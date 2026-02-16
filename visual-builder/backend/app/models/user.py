"""User model for authentication."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, String, Text

from app.db.database import Base


class UserAccount(Base):
    """User account with password authentication."""

    __tablename__ = "user_accounts"

    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    role = Column(String(20), nullable=False, default="viewer")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
    )
