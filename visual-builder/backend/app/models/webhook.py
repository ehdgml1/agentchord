"""Webhook model."""
from datetime import UTC, datetime
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


def _utcnow():
    """Return current UTC time without timezone info (for SQLite compat)."""
    return datetime.now(UTC).replace(tzinfo=None)


class Webhook(Base):
    """Webhook entity."""

    __tablename__ = "webhooks"
    __table_args__ = (
        Index("ix_webhooks_workflow_enabled", "workflow_id", "enabled"),
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
    secret: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    allowed_ips: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    input_mapping: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    last_called_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=_utcnow,
    )
