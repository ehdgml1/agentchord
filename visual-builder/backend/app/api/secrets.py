"""Secrets API endpoints with multi-tenant isolation.

Phase 0 MVP:
- List secrets (names only, no values)
- Create/update/delete secrets
- Values are never returned in responses

M13 Multi-tenancy:
- Each user manages their own secrets via owner_id scoping
- Admin can list all secrets (no owner_id filter)
- Regular users only see/manage their own secrets
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from ..auth import get_current_user
from ..auth.jwt import User
from ..core.rbac import require_permission, Role
from ..core.secret_store import (
    SecretNameInvalidError,
    SecretNotFoundError,
    SecretStoreError,
)
from ..dtos.secret import (
    SecretCreate,
    SecretUpdate,
    SecretResponse,
)

router = APIRouter(prefix="/api/secrets", tags=["secrets"])


@router.get("", response_model=list[SecretResponse])
@require_permission("workflow:write")
async def list_secrets(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
):
    """List secret names (values excluded for security).

    Admin users see all secrets. Regular users see only their own.

    Args:
        request: FastAPI request object.
        user: Current authenticated user.

    Returns:
        List of secret metadata without values.
    """
    try:
        secret_store = request.app.state.secret_store
        # Admin sees all secrets; regular users see only their own
        if user.role == Role.ADMIN:
            secrets_meta = await secret_store.list_with_metadata()
        else:
            secrets_meta = await secret_store.list_with_metadata(owner_id=user.id)
        return [
            SecretResponse(
                name=m["name"],
                description="",
                created_at=m["created_at"],
                updated_at=m["updated_at"],
            )
            for m in secrets_meta
        ]
    except SecretStoreError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "SECRET_STORE_ERROR",
                    "message": str(e),
                }
            },
        )


@router.post("", response_model=SecretResponse, status_code=201)
@require_permission("workflow:write")
async def create_secret(
    secret: SecretCreate,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
):
    """Create new secret scoped to current user.

    Args:
        secret: Secret creation data.
        request: FastAPI request object.
        user: Current authenticated user.

    Returns:
        Created secret metadata (without value).

    Raises:
        400: Invalid secret name.
        409: Secret already exists for this user.
        500: Internal server error.
    """
    try:
        secret_store = request.app.state.secret_store

        # Validate name format
        secret_store.validate_name(secret.name)

        # Check if secret already exists for this user
        existing = await secret_store.get(secret.name, owner_id=user.id)
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": {
                        "code": "SECRET_ALREADY_EXISTS",
                        "message": f"Secret '{secret.name}' already exists",
                    }
                },
            )

        # Create the secret scoped to user
        await secret_store.set(secret.name, secret.value, owner_id=user.id)

        # Get metadata
        meta = await secret_store.get_metadata(secret.name, owner_id=user.id)
        return SecretResponse(
            name=secret.name,
            description=secret.description,
            created_at=meta["created_at"] if meta else None,
            updated_at=meta["updated_at"] if meta else None,
        )

    except SecretNameInvalidError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "SECRET_NAME_INVALID",
                    "message": str(e),
                }
            },
        )
    except SecretStoreError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "SECRET_STORE_ERROR",
                    "message": str(e),
                }
            },
        )


@router.put("/{name}", response_model=SecretResponse)
@require_permission("workflow:write")
async def update_secret(
    name: str,
    secret: SecretUpdate,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
):
    """Update existing secret owned by current user.

    Args:
        name: Secret name.
        secret: Secret update data.
        request: FastAPI request object.
        user: Current authenticated user.

    Returns:
        Updated secret metadata (without value).

    Raises:
        400: Invalid secret name.
        404: Secret not found for this user.
        500: Internal server error.
    """
    try:
        secret_store = request.app.state.secret_store

        # Validate name format
        secret_store.validate_name(name)

        # Check if secret exists for this user
        existing = await secret_store.get(name, owner_id=user.id)
        if existing is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "SECRET_NOT_FOUND",
                        "message": f"Secret '{name}' not found",
                    }
                },
            )

        # Update the secret (scoped to user)
        await secret_store.set(name, secret.value, owner_id=user.id)

        # Get metadata
        meta = await secret_store.get_metadata(name, owner_id=user.id)
        return SecretResponse(
            name=name,
            description=secret.description or "",
            created_at=meta["created_at"] if meta else None,
            updated_at=meta["updated_at"] if meta else None,
        )

    except SecretNameInvalidError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "SECRET_NAME_INVALID",
                    "message": str(e),
                }
            },
        )
    except SecretStoreError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "SECRET_STORE_ERROR",
                    "message": str(e),
                }
            },
        )


@router.delete("/{name}", status_code=204)
@require_permission("workflow:write")
async def delete_secret(
    name: str,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
):
    """Delete secret owned by current user.

    Args:
        name: Secret name.
        request: FastAPI request object.
        user: Current authenticated user.

    Raises:
        404: Secret not found for this user.
        500: Internal server error.
    """
    try:
        secret_store = request.app.state.secret_store

        # Check if secret exists for this user
        existing = await secret_store.get(name, owner_id=user.id)
        if existing is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "SECRET_NOT_FOUND",
                        "message": f"Secret '{name}' not found",
                    }
                },
            )

        # Delete the secret (scoped to user)
        await secret_store.delete(name, owner_id=user.id)

    except SecretStoreError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "SECRET_STORE_ERROR",
                    "message": str(e),
                }
            },
        )
