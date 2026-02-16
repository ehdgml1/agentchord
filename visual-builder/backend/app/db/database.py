"""Database configuration and session management."""
from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base

from app.config import get_settings

settings = get_settings()

# Engine configuration
_engine_kwargs: dict = {
    "echo": settings.db_echo,
    "future": True,
}

# Add connection pool settings for non-SQLite databases
if not settings.is_sqlite:
    _engine_kwargs.update({
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
        "pool_pre_ping": True,
        "pool_recycle": 3600,  # Recycle connections after 1 hour
    })

engine = create_async_engine(settings.database_url, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


def get_session_factory():
    """Get session factory for scheduler.

    Returns:
        Callable that returns AsyncSession context manager.
    """
    return AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session.

    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables.

    In production, use Alembic migrations instead:
        alembic upgrade head
    """
    if settings.is_production:
        return  # Production uses Alembic migrations

    # Development: auto-create tables
    # Import models to register them
    from app.models import (
        Workflow,
        Execution,
        Secret,
        MCPServer,
        Schedule,
        Webhook,
        AuditLog,
        ABTest,
        ABTestResult,
        UserAccount,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Create execution_states table for checkpoints (not a SQLAlchemy model)
        from sqlalchemy import text
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS execution_states (
                execution_id TEXT PRIMARY KEY,
                current_node TEXT NOT NULL,
                context TEXT NOT NULL,
                status TEXT DEFAULT 'running',
                error TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
