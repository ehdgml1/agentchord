"""Workflow Pydantic schemas for API request/response.

Phase 0 MVP:
- WorkflowCreate, WorkflowUpdate, WorkflowResponse
- WorkflowRunRequest, WorkflowRunResponse
- Node and Edge schemas
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorkflowNodeData(BaseModel):
    """Workflow node data schema."""

    model: str | None = None
    prompt: str | None = None
    serverId: str | None = None
    toolName: str | None = None
    condition: str | None = None
    # Allow additional fields
    model_config = ConfigDict(extra="allow")


class WorkflowNode(BaseModel):
    """Workflow node schema."""

    id: str = Field(..., description="Node ID")
    type: str = Field(..., description="Node type (agent, mcp_tool, condition, parallel)")
    data: WorkflowNodeData = Field(..., description="Node configuration")
    position: dict[str, float] | None = Field(None, description="Node position on canvas")


class WorkflowEdge(BaseModel):
    """Workflow edge schema."""

    id: str = Field(..., description="Edge ID")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    source_handle: str | None = Field(None, description="Source handle ID", alias="sourceHandle")
    target_handle: str | None = Field(None, description="Target handle ID", alias="targetHandle")

    model_config = ConfigDict(populate_by_name=True)


class WorkflowCreate(BaseModel):
    """Workflow creation request."""

    name: str = Field(..., min_length=1, max_length=200, description="Workflow name")
    description: str = Field("", max_length=1000, description="Workflow description")
    nodes: list[WorkflowNode] = Field(default_factory=list, description="Workflow nodes")
    edges: list[WorkflowEdge] = Field(default_factory=list, description="Workflow edges")


class WorkflowUpdate(BaseModel):
    """Workflow update request."""

    name: str | None = Field(None, min_length=1, max_length=200, description="Workflow name")
    description: str | None = Field(None, max_length=1000, description="Workflow description")
    nodes: list[WorkflowNode] | None = Field(None, description="Workflow nodes")
    edges: list[WorkflowEdge] | None = Field(None, description="Workflow edges")


class WorkflowResponse(BaseModel):
    """Workflow response."""

    id: str = Field(..., description="Workflow ID")
    name: str = Field(..., description="Workflow name")
    description: str = Field(..., description="Workflow description")
    nodes: list[WorkflowNode] = Field(..., description="Workflow nodes")
    edges: list[WorkflowEdge] = Field(..., description="Workflow edges")
    created_at: datetime = Field(..., description="Creation timestamp", alias="createdAt")
    updated_at: datetime = Field(..., description="Last update timestamp", alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class WorkflowListResponse(BaseModel):
    """Workflow list response."""

    workflows: list[WorkflowResponse] = Field(..., description="List of workflows")
    total: int = Field(..., description="Total count")
    limit: int = Field(..., description="Page limit")
    offset: int = Field(..., description="Page offset")


class WorkflowRunRequest(BaseModel):
    """Workflow execution request."""

    input: str = Field("", description="Workflow input string")
    mode: str = Field("full", description="Execution mode (full, mock, debug)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "input": "Process this text",
                "mode": "full"
            }
        }
    )


class WorkflowRunResponse(BaseModel):
    """Workflow execution response."""

    id: str = Field(..., description="Execution ID")
    workflow_id: str = Field(..., description="Workflow ID", alias="workflowId")
    status: str = Field(..., description="Execution status")
    mode: str = Field(..., description="Execution mode")
    trigger_type: str = Field(..., description="Trigger type", alias="triggerType")
    trigger_id: str | None = Field(None, description="Trigger ID", alias="triggerId")
    input: str | None = Field(None, description="Workflow input")
    output: Any | None = Field(None, description="Workflow output")
    error: str | None = Field(None, description="Error message")
    node_executions: list[dict[str, Any]] = Field(default_factory=list, description="Node execution logs", alias="nodeExecutions")
    started_at: str | None = Field(None, description="Start timestamp", alias="startedAt")
    completed_at: str | None = Field(None, description="Completion timestamp", alias="completedAt")
    duration_ms: int | None = Field(None, description="Duration in milliseconds", alias="durationMs")

    model_config = ConfigDict(populate_by_name=True)


class WorkflowValidationError(BaseModel):
    """Workflow validation error."""

    message: str = Field(..., description="Error message")


class WorkflowValidateResponse(BaseModel):
    """Workflow validation response."""

    valid: bool = Field(..., description="Whether workflow is valid")
    errors: list[WorkflowValidationError] = Field(
        default_factory=list,
        description="List of validation errors"
    )
