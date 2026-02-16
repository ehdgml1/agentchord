"""Workflow model."""
from datetime import UTC, datetime
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


def _utcnow():
    """Return current UTC time without timezone info (for SQLite compat)."""
    return datetime.now(UTC).replace(tzinfo=None)


class Workflow(Base):
    """Workflow entity."""

    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    nodes: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
    )
    edges: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
    )
    owner_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
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
