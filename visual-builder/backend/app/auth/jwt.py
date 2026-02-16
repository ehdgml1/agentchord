"""JWT authentication implementation.

Phase 0 MVP:
- JWT token generation and verification
- Current user dependency injection
- Optional authentication for public APIs
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError

from app.config import get_settings
from app.core.rbac import Role

# JWT configuration from settings
_settings = get_settings()
JWT_SECRET = _settings.jwt_secret
if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET environment variable must be set. "
        "The application cannot start without a valid JWT secret for token signing. "
        "Please set JWT_SECRET in your environment or .env file."
    )
JWT_ALGORITHM = _settings.jwt_algorithm
JWT_EXPIRE_MINUTES = _settings.jwt_expiry_minutes

# Security scheme
security = HTTPBearer()


class User:
    """User model for authentication."""

    def __init__(self, id: str, email: str, role: Role = Role.VIEWER):
        """Initialize user.

        Args:
            id: User ID.
            email: User email.
            role: User role (default: VIEWER).
        """
        self.id = id
        self.email = email
        self.role = Role(role) if isinstance(role, str) else role


def create_access_token(user_id: str, email: str, role: Role = Role.VIEWER) -> str:
    """Create JWT access token.

    Args:
        user_id: User ID to encode in token.
        email: User email.
        role: User role (default: VIEWER).

    Returns:
        JWT token string.

    Example:
        >>> token = create_access_token("user-123", "user@example.com")
    """
    expire = datetime.now(UTC) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role.value,
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify JWT token.

    Args:
        token: JWT token string.

    Returns:
        Decoded token payload.

    Raises:
        HTTPException: If token is invalid or expired.
    """
    try:
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "INVALID_TOKEN",
                    "message": f"Could not validate credentials: {str(e)}",
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> User:
    """Get current authenticated user.

    Dependency for protected endpoints.

    Args:
        credentials: HTTP Bearer credentials.

    Returns:
        Current user instance.

    Raises:
        HTTPException: If authentication fails.

    Example:
        >>> @app.get("/api/workflows")
        >>> async def list_workflows(user: User = Depends(get_current_user)):
        >>>     ...
    """
    payload = decode_token(credentials.credentials)

    user_id = payload.get("sub")
    email = payload.get("email")
    role_str = payload.get("role", "viewer")

    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "INVALID_TOKEN",
                    "message": "Token missing required claims",
                }
            },
        )

    try:
        role = Role(role_str)
    except ValueError:
        role = Role.VIEWER

    return User(id=user_id, email=email, role=role)


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(HTTPBearer(auto_error=False))]
) -> User | None:
    """Get current user or None if not authenticated.

    Dependency for public endpoints that support optional authentication.

    Args:
        credentials: Optional HTTP Bearer credentials.

    Returns:
        Current user instance or None.

    Example:
        >>> @app.get("/api/public/workflows")
        >>> async def list_public_workflows(user: User | None = Depends(get_current_user_optional)):
        >>>     if user:
        >>>         # Show user's private workflows too
        >>>     ...
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
