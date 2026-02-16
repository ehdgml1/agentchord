"""Schedule Pydantic schemas for API request/response.

Phase -1 Implementation:
- ScheduleCreate, ScheduleUpdate, ScheduleResponse
- ScheduleListResponse
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScheduleCreate(BaseModel):
    """Schedule creation request."""

    workflow_id: str = Field(
        ...,
        min_length=1,
        max_length=36,
        description="Workflow ID to schedule",
        alias="workflowId",
    )
    expression: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Cron expression (e.g., '0 9 * * *' for 9am daily)",
    )
    input: dict[str, Any] = Field(
        default_factory=dict,
        description="Input to pass to workflow execution",
    )
    timezone: str = Field(
        default="UTC",
        max_length=50,
        description="Timezone for schedule (e.g., 'America/New_York')",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "workflow_id": "wf-123",
                "expression": "0 9 * * *",
                "input": {"param": "value"},
                "timezone": "UTC",
            }
        }
    )


class ScheduleUpdate(BaseModel):
    """Schedule update request."""

    expression: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description="Cron expression",
    )
    input: dict[str, Any] | None = Field(
        None,
        description="Input to pass to workflow execution",
    )
    timezone: str | None = Field(
        None,
        max_length=50,
        description="Timezone for schedule",
    )
    enabled: bool | None = Field(
        None,
        description="Whether schedule is enabled",
    )


class ScheduleResponse(BaseModel):
    """Schedule response."""

    id: str = Field(..., description="Schedule ID")
    workflow_id: str = Field(..., description="Workflow ID", alias="workflowId")
    type: str = Field(..., description="Schedule type (cron)")
    expression: str = Field(..., description="Cron expression")
    input: dict[str, Any] = Field(..., description="Workflow input")
    timezone: str = Field(..., description="Schedule timezone")
    enabled: bool = Field(..., description="Whether schedule is enabled")
    last_run_at: datetime | None = Field(None, description="Last execution time", alias="lastRunAt")
    next_run_at: datetime | None = Field(None, description="Next scheduled run", alias="nextRunAt")
    created_at: datetime = Field(..., description="Creation timestamp", alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ScheduleListResponse(BaseModel):
    """Schedule list response."""

    schedules: list[ScheduleResponse] = Field(
        ...,
        description="List of schedules",
    )
    total: int = Field(..., description="Total count")
