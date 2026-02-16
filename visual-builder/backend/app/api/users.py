"""User management API endpoints."""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.auth.jwt import User
from app.core.rbac import Role, require_permission
from app.db.database import get_db
from app.dtos.user import UserResponse, UserListResponse, UserRoleUpdate
from app.repositories.user_repo import UserRepository


router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=UserListResponse)
@require_permission("user:read")
async def list_users(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """List users (Admin only)."""
    if user.role != Role.ADMIN:
        raise HTTPException(
            403,
            {"error": {"code": "FORBIDDEN", "message": "Admin role required"}},
        )

    repo = UserRepository(session)
    users = await repo.list_all()
    total = await repo.count()

    return UserListResponse(
        users=[
            UserResponse(
                id=u.id,
                email=u.email,
                role=u.role,
            )
            for u in users
        ],
        total=total,
    )


@router.put("/{user_id}/role", response_model=UserResponse)
@require_permission("user:write")
async def update_user_role(
    user_id: str,
    role_update: UserRoleUpdate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """Update user role (Admin only)."""
    if user.role != Role.ADMIN:
        raise HTTPException(
            403,
            {"error": {"code": "FORBIDDEN", "message": "Admin role required"}},
        )

    # Prevent self-demotion
    if user_id == user.id and role_update.role != Role.ADMIN:
        raise HTTPException(
            400,
            {"error": {"code": "INVALID_OPERATION", "message": "Cannot change your own role"}},
        )

    repo = UserRepository(session)
    updated = await repo.update_role(user_id, role_update.role.value)
    if not updated:
        raise HTTPException(
            404,
            {"error": {"code": "NOT_FOUND", "message": f"User '{user_id}' not found"}},
        )

    await session.commit()

    return UserResponse(
        id=updated.id,
        email=updated.email,
        role=updated.role,
    )
