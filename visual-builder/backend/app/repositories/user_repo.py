"""User repository implementation."""
from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserAccount


class UserRepository:
    """User repository for CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: str) -> UserAccount | None:
        stmt = select(UserAccount).where(UserAccount.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[UserAccount]:
        stmt = (
            select(UserAccount)
            .order_by(UserAccount.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self) -> int:
        stmt = select(func.count(UserAccount.id))
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def update_role(self, user_id: str, role: str) -> UserAccount | None:
        user = await self.get_by_id(user_id)
        if not user:
            return None
        user.role = role
        await self.session.flush()
        return user
