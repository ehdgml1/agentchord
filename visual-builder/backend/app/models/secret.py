"""Secret model with multi-tenant isolation (M13).

Each secret is scoped to an owner_id, allowing per-user secret management.
The composite primary key (name, owner_id) allows different users to have
secrets with the same name without conflict.
"""
from datetime import UTC, datetime
from sqlalchemy import String, LargeBinary, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


def _utcnow():
    """Return current UTC time without timezone info (for SQLite compat)."""
    return datetime.now(UTC).replace(tzinfo=None)


class Secret(Base):
    """Secret entity with owner-scoped isolation."""

    __tablename__ = "secrets"

    name: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )
    owner_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        default="system",
    )
    value: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
    )
    key_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )
