"""A/B Test DTOs for serializable data transfer."""

from __future__ import annotations

from dataclasses import dataclass
from pydantic import BaseModel, ConfigDict, Field


# === Dataclasses for internal use ===


@dataclass
class ABTestStats:
    """A/B Test statistics for a variant."""

    variant: str
    count: int
    success_rate: float
    avg_duration_ms: float


# === Pydantic Models for API ===


class ABTestCreate(BaseModel):
    """Request to create A/B test."""

    name: str = Field(..., description="Test name")
    workflow_a_id: str = Field(..., description="Workflow A ID", alias="workflowAId")
    workflow_b_id: str = Field(..., description="Workflow B ID", alias="workflowBId")
    traffic_split: float = Field(0.5, ge=0.0, le=1.0, description="Traffic split for variant A (0.0-1.0)", alias="trafficSplit")
    metrics: list[str] = Field(["duration", "success_rate"], description="Metrics to track")

    model_config = ConfigDict(populate_by_name=True)


class ABTestResponse(BaseModel):
    """A/B Test response."""

    id: str = Field(..., description="Test ID")
    name: str = Field(..., description="Test name")
    workflow_a_id: str = Field(..., description="Workflow A ID", alias="workflowAId")
    workflow_b_id: str = Field(..., description="Workflow B ID", alias="workflowBId")
    traffic_split: float = Field(..., description="Traffic split for variant A", alias="trafficSplit")
    metrics: list[str] = Field(..., description="Metrics to track")
    status: str = Field(..., description="Test status (draft, running, completed)")
    created_at: str = Field(..., description="Creation timestamp", alias="createdAt")
    completed_at: str | None = Field(None, description="Completion timestamp", alias="completedAt")

    model_config = ConfigDict(populate_by_name=True)


class ABTestStatsResponse(BaseModel):
    """A/B Test statistics response."""

    variant: str = Field(..., description="Variant (A or B)")
    count: int = Field(..., description="Number of executions")
    success_rate: float = Field(..., description="Success rate (0.0-1.0)", alias="successRate")
    avg_duration_ms: float = Field(..., description="Average duration in milliseconds", alias="avgDurationMs")

    model_config = ConfigDict(populate_by_name=True)


class ABTestDetailResponse(BaseModel):
    """A/B Test with statistics."""

    id: str = Field(..., description="Test ID")
    name: str = Field(..., description="Test name")
    workflow_a_id: str = Field(..., description="Workflow A ID", alias="workflowAId")
    workflow_b_id: str = Field(..., description="Workflow B ID", alias="workflowBId")
    traffic_split: float = Field(..., description="Traffic split for variant A", alias="trafficSplit")
    metrics: list[str] = Field(..., description="Metrics to track")
    status: str = Field(..., description="Test status")
    created_at: str = Field(..., description="Creation timestamp", alias="createdAt")
    completed_at: str | None = Field(None, description="Completion timestamp", alias="completedAt")
    stats: dict[str, ABTestStatsResponse] = Field(..., description="Statistics by variant")

    model_config = ConfigDict(populate_by_name=True)


class ABTestListResponse(BaseModel):
    """A/B Test list response."""

    tests: list[ABTestResponse] = Field(..., description="List of tests")
    total: int = Field(..., description="Total count")
