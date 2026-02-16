"""Execution model."""
from datetime import UTC, datetime
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


def _utcnow():
    """Return current UTC time without timezone info (for SQLite compat)."""
    return datetime.now(UTC).replace(tzinfo=None)


class Execution(Base):
    """Execution entity."""

    __tablename__ = "executions"
    __table_args__ = (
        Index("ix_executions_workflow_status", "workflow_id", "status"),
        Index("ix_executions_workflow_started", "workflow_id", "started_at"),
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
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
    )
    mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="full",
    )
    trigger_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="manual",
    )
    trigger_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )
    input: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )
    output: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    node_logs: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=_utcnow,
        index=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    total_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    prompt_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    completion_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    estimated_cost: Mapped[float | None] = mapped_column(
        nullable=True,
    )
    model_used: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
