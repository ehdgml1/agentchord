"""Audit logging service with PII filtering."""
import json
from uuid import uuid4
from datetime import UTC, datetime
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pii_filter import sanitize_pii
from app.models.audit_log import AuditLog


class AuditService:
    """Service for audit logging."""

    def __init__(self, session: AsyncSession):
        """Initialize service.

        Args:
            session: Database session.
        """
        self.session = session

    async def log(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        user_id: str,
        details: dict = None,
        ip_address: str = None,
        success: bool = True,
    ) -> AuditLog:
        """Log audit event with PII sanitization.

        Args:
            action: Action performed.
            resource_type: Type of resource.
            resource_id: Resource ID.
            user_id: User who performed action.
            details: Additional details.
            ip_address: Client IP address.
            success: Whether action succeeded.

        Returns:
            Created audit log entry.
        """
        sanitized = sanitize_pii(details) if details else None
        details_json = json.dumps(sanitized) if sanitized else None

        audit_log = AuditLog(
            id=str(uuid4()),
            timestamp=datetime.now(UTC).replace(tzinfo=None),
            event_type=f"{resource_type}.{action}",
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details_json,
            ip_address=ip_address,
            success=success,
        )

        self.session.add(audit_log)
        await self.session.flush()
        return audit_log

    async def get_logs(
        self,
        user_id: str = None,
        resource_type: str = None,
        action: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Get audit logs with filters.

        Args:
            user_id: Filter by user ID.
            resource_type: Filter by resource type.
            action: Filter by action.
            limit: Maximum results.
            offset: Results offset.

        Returns:
            List of audit logs.
        """
        query = select(AuditLog).order_by(desc(AuditLog.timestamp))

        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        if action:
            query = query.where(AuditLog.action == action)

        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(
        self,
        user_id: str = None,
        resource_type: str = None,
        action: str = None,
    ) -> int:
        """Count audit logs with filters.

        Args:
            user_id: Filter by user ID.
            resource_type: Filter by resource type.
            action: Filter by action.

        Returns:
            Total count of matching audit logs.
        """
        from sqlalchemy import func as sql_func
        query = select(sql_func.count(AuditLog.id))
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        if action:
            query = query.where(AuditLog.action == action)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_log(self, log_id: str) -> AuditLog | None:
        """Get audit log by ID.

        Args:
            log_id: Audit log ID.

        Returns:
            Audit log or None if not found.
        """
        result = await self.session.execute(
            select(AuditLog).where(AuditLog.id == log_id)
        )
        return result.scalar_one_or_none()
