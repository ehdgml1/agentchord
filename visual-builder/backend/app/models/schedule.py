"""Schedule model."""
from datetime import UTC, datetime
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


def _utcnow():
    """Return current UTC time without timezone info (for SQLite compat)."""
    return datetime.now(UTC).replace(tzinfo=None)


class Schedule(Base):
    """Schedule entity."""

    __tablename__ = "schedules"
    __table_args__ = (
        Index("ix_schedules_workflow_enabled", "workflow_id", "enabled"),
        Index("ix_schedules_enabled_created", "enabled", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )
    workflow_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workflows.id"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    expression: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    input: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )
    timezone: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="UTC",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=_utcnow,
    )
