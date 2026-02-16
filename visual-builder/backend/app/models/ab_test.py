"""A/B Test SQLAlchemy models."""
from datetime import UTC, datetime
from sqlalchemy import String, Float, Text, Integer, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


def _utcnow():
    """Return current UTC time without timezone info (for SQLite compat)."""
    return datetime.now(UTC).replace(tzinfo=None)


class ABTest(Base):
    """A/B Test entity."""

    __tablename__ = "ab_tests"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    workflow_a_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workflows.id"),
        nullable=False,
    )
    workflow_b_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workflows.id"),
        nullable=False,
    )
    traffic_split: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5,
    )
    metrics: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default='["duration", "success_rate"]',
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=_utcnow,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )


class ABTestResult(Base):
    """A/B Test result entity."""

    __tablename__ = "ab_test_results"
    __table_args__ = (
        Index("ix_ab_test_results_test_variant_created", "test_id", "variant", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )
    test_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ab_tests.id"),
        nullable=False,
    )
    variant: Mapped[str] = mapped_column(
        String(1),
        nullable=False,
    )
    execution_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )
    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    success: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=_utcnow,
    )
