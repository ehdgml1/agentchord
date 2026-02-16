"""WorkflowVersion model."""
from datetime import UTC, datetime
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


def _utcnow():
    """Return current UTC time without timezone info (for SQLite compat)."""
    return datetime.now(UTC).replace(tzinfo=None)


class WorkflowVersion(Base):
    """Workflow version entity."""

    __tablename__ = "workflow_versions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )
    workflow_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    data: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    message: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=_utcnow,
    )
