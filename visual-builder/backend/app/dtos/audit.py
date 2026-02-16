"""Audit log DTOs."""
import json
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models.audit_log import AuditLog


class AuditLogResponse(BaseModel):
    """Audit log response schema."""

    id: str = Field(..., description="Audit log ID")
    timestamp: datetime = Field(..., description="Event timestamp")
    event_type: str = Field(..., description="Event type", alias="eventType")
    user_id: str | None = Field(None, description="User who performed action", alias="userId")
    resource_type: str = Field(..., description="Resource type", alias="resourceType")
    resource_id: str = Field(..., description="Resource ID", alias="resourceId")
    action: str = Field(..., description="Action performed")
    details: dict | None = Field(None, description="Additional details")
    ip_address: str | None = Field(None, description="Client IP address", alias="ipAddress")
    success: bool = Field(..., description="Whether action succeeded")

    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def from_model(cls, log: AuditLog) -> "AuditLogResponse":
        """Create DTO from model.

        Args:
            log: AuditLog model instance.

        Returns:
            AuditLogResponse DTO.
        """
        details = None
        if log.details:
            try:
                details = json.loads(log.details)
            except json.JSONDecodeError:
                pass

        return cls(
            id=log.id,
            timestamp=log.timestamp,
            event_type=log.event_type,
            user_id=log.user_id,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            action=log.action,
            details=details,
            ip_address=log.ip_address,
            success=log.success,
        )


class AuditLogListResponse(BaseModel):
    """Audit log list response schema."""

    logs: list[AuditLogResponse] = Field(..., description="Audit logs")
    total: int = Field(..., description="Total count")
