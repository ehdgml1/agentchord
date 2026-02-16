"""Authentication API endpoints (login/register)."""
from __future__ import annotations

import uuid
from typing import Annotated

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import User, create_access_token, get_current_user
from app.core.rbac import Role
from app.core.rate_limiter import limiter
from app.db.database import get_db
from app.models.user import UserAccount

router = APIRouter(prefix="/api/auth", tags=["auth"])


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against bcrypt hash."""
    return bcrypt.checkpw(password.encode(), hashed.encode())


class RegisterRequest(BaseModel):
    """Registration request payload."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """Login request payload."""

    email: EmailStr
    password: str = Field(min_length=1)


class AuthResponse(BaseModel):
    """Authentication response with JWT token."""

    token: str
    user_id: str
    email: str
    role: str


@router.post("/register", response_model=AuthResponse, status_code=201)
@limiter.limit("5/minute")
async def register(
    request: Request,
    data: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """Register a new user account."""
    existing = await session.execute(
        select(UserAccount).where(UserAccount.email == data.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "EMAIL_EXISTS",
                    "message": "Email already registered",
                }
            },
        )

    user = UserAccount(
        id=str(uuid.uuid4()),
        email=data.email,
        password_hash=hash_password(data.password),
        role=Role.EDITOR.value,
    )
    session.add(user)
    await session.flush()

    token = create_access_token(user.id, user.email, Role(user.role))
    return AuthResponse(
        token=token, user_id=user.id, email=user.email, role=user.role
    )


@router.post("/login", response_model=AuthResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    data: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """Login with email and password."""
    result = await session.execute(
        select(UserAccount).where(UserAccount.email == data.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "INVALID_CREDENTIALS",
                    "message": "Invalid email or password",
                }
            },
        )

    token = create_access_token(user.id, user.email, Role(user.role))
    return AuthResponse(
        token=token, user_id=user.id, email=user.email, role=user.role
    )


@router.post("/refresh", response_model=AuthResponse)
@limiter.limit("5/minute")
async def refresh_token(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
):
    """Refresh JWT token. Requires valid (non-expired) current token."""
    token = create_access_token(user.id, user.email, user.role)
    return AuthResponse(
        token=token, user_id=user.id, email=user.email, role=user.role.value
    )
