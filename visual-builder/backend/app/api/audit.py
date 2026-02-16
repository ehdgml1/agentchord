"""Audit API endpoints."""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.auth.jwt import User
from app.core.rbac import Role, require_permission
from app.db.database import get_db
from app.services.audit_service import AuditService
from app.dtos.audit import AuditLogResponse, AuditLogListResponse


router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=AuditLogListResponse)
@require_permission("audit:read")
async def list_audit_logs(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    user_id: str = Query(None),
    resource_type: str = Query(None),
    action: str = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """List audit logs (Admin only).

    Args:
        user: Current authenticated user.
        session: Database session.
        user_id: Filter by user ID.
        resource_type: Filter by resource type.
        action: Filter by action.
        limit: Maximum results.
        offset: Results offset.

    Returns:
        List of audit logs.
    """
    if user.role != Role.ADMIN:
        raise HTTPException(
            403,
            {
                "error": {
                    "code": "FORBIDDEN",
                    "message": "Admin role required",
                }
            },
        )

    service = AuditService(session)
    logs = await service.get_logs(
        user_id=user_id,
        resource_type=resource_type,
        action=action,
        limit=limit,
        offset=offset,
    )

    total = await service.count(
        user_id=user_id,
        resource_type=resource_type,
        action=action,
    )

    return AuditLogListResponse(
        logs=[AuditLogResponse.from_model(log) for log in logs],
        total=total,
    )


@router.get("/{log_id}", response_model=AuditLogResponse)
@require_permission("audit:read")
async def get_audit_log(
    log_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """Get audit log detail (Admin only).

    Args:
        log_id: Audit log ID.
        user: Current authenticated user.
        session: Database session.

    Returns:
        Audit log detail.
    """
    if user.role != Role.ADMIN:
        raise HTTPException(
            403,
            {
                "error": {
                    "code": "FORBIDDEN",
                    "message": "Admin role required",
                }
            },
        )

    service = AuditService(session)
    log = await service.get_log(log_id)

    if not log:
        raise HTTPException(
            404,
            {"error": {"code": "NOT_FOUND", "message": "Audit log not found"}},
        )

    return AuditLogResponse.from_model(log)
