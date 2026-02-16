"""Role-Based Access Control system."""
from enum import Enum
from functools import wraps
from typing import Callable
from fastapi import HTTPException


class Role(Enum):
    """User roles with hierarchical permissions."""

    VIEWER = "viewer"
    EDITOR = "editor"
    OPERATOR = "operator"
    ADMIN = "admin"


# Hierarchical permissions
ROLE_PERMISSIONS = {
    Role.VIEWER: ["workflow:read", "execution:read"],
    Role.EDITOR: [
        "workflow:read",
        "workflow:write",
        "execution:read",
    ],
    Role.OPERATOR: [
        "workflow:read",
        "workflow:write",
        "execution:read",
        "execution:write",
        "schedule:write",
    ],
    Role.ADMIN: ["*"],  # All permissions (includes audit:read, user:read, user:write)
}


def has_permission(role: Role, permission: str) -> bool:
    """Check if role has permission.

    Args:
        role: User role to check.
        permission: Permission string (e.g., "workflow:write").

    Returns:
        True if role has permission, False otherwise.
    """
    perms = ROLE_PERMISSIONS.get(role, [])
    return "*" in perms or permission in perms


def require_permission(permission: str):
    """Decorator to require permission on endpoint.

    Args:
        permission: Required permission string.

    Returns:
        Decorator function.

    Raises:
        HTTPException: 403 if user lacks permission.
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get("user")
            if not user:
                raise HTTPException(
                    401,
                    {
                        "error": {
                            "code": "UNAUTHORIZED",
                            "message": "Authentication required",
                        }
                    },
                )
            # Convert string role to Role enum if needed
            role = user.role if isinstance(user.role, Role) else Role(user.role)
            if not has_permission(role, permission):
                raise HTTPException(
                    403,
                    {
                        "error": {
                            "code": "FORBIDDEN",
                            "message": "Permission denied",
                        }
                    },
                )
            return await func(*args, **kwargs)

        return wrapper

    return decorator
