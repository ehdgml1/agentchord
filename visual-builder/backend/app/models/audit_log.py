"""Audit Log model."""
from datetime import UTC, datetime
from sqlalchemy import String, Text, Boolean, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


def _utcnow():
    """Return current UTC time without timezone info (for SQLite compat)."""
    return datetime.now(UTC).replace(tzinfo=None)


class AuditLog(Base):
    """Audit Log entity."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_user_timestamp", "user_id", "timestamp"),
        Index("ix_audit_logs_action_timestamp", "action", "timestamp"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=_utcnow,
    )
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    resource_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )
    success: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
