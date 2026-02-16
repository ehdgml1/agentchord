"""User management DTOs."""
from pydantic import BaseModel, Field

from app.core.rbac import Role


class UserResponse(BaseModel):
    """User response schema."""

    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    role: Role = Field(..., description="User role")


class UserListResponse(BaseModel):
    """User list response schema."""

    users: list[UserResponse] = Field(..., description="Users")
    total: int = Field(..., description="Total count")


class UserRoleUpdate(BaseModel):
    """User role update schema."""

    role: Role = Field(..., description="New role")
