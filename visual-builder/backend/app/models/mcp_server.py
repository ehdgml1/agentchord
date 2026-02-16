"""MCP Server model."""
from datetime import UTC, datetime
from sqlalchemy import String, Text, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


def _utcnow():
    """Return current UTC time without timezone info (for SQLite compat)."""
    return datetime.now(UTC).replace(tzinfo=None)


class MCPServer(Base):
    """MCP Server entity."""

    __tablename__ = "mcp_servers"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )
    command: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    args: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
    )
    env: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="disconnected",
    )
    last_connected_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    tool_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=_utcnow,
    )
