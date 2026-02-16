"""Webhook Pydantic schemas for API request/response."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WebhookCreate(BaseModel):
    """Webhook creation request."""

    workflow_id: str = Field(..., description="Workflow ID to trigger", alias="workflowId")
    allowed_ips: str | None = Field(None, description="Comma-separated allowed IPs", alias="allowedIps")
    input_mapping: str | None = Field(None, description="JSON input mapping template", alias="inputMapping")

    model_config = ConfigDict(populate_by_name=True)


class WebhookResponse(BaseModel):
    """Webhook response (secret excluded)."""

    id: str = Field(..., description="Webhook ID")
    workflow_id: str = Field(..., description="Workflow ID", alias="workflowId")
    allowed_ips: str | None = Field(None, description="Allowed IPs", alias="allowedIps")
    input_mapping: str | None = Field(None, description="Input mapping", alias="inputMapping")
    enabled: bool = Field(..., description="Whether webhook is enabled")
    last_called_at: str | None = Field(None, description="Last triggered timestamp", alias="lastCalledAt")
    created_at: str = Field(..., description="Creation timestamp", alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)


class WebhookListResponse(BaseModel):
    """Webhook list response."""

    webhooks: list[WebhookResponse] = Field(..., description="List of webhooks")
    total: int = Field(..., description="Total count")


class WebhookSecretResponse(BaseModel):
    """Response after secret rotation (includes new secret)."""

    id: str = Field(..., description="Webhook ID")
    secret: str = Field(..., description="New webhook secret")
