"""Secret Pydantic schemas for API request/response.

Phase 0 MVP:
- SecretCreate, SecretUpdate
- SecretResponse (without value)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SecretCreate(BaseModel):
    """Secret creation request."""

    name: str = Field(..., min_length=1, max_length=100, description="Secret name")
    value: str = Field(..., min_length=1, description="Secret value")
    description: str = Field("", max_length=500, description="Secret description")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "OPENAI_API_KEY",
                "value": "sk-...",
                "description": "OpenAI API key for workflows"
            }
        }
    )


class SecretUpdate(BaseModel):
    """Secret update request."""

    value: str = Field(..., min_length=1, description="New secret value")
    description: str | None = Field(None, max_length=500, description="Secret description")


class SecretResponse(BaseModel):
    """Secret response (without value)."""

    name: str = Field(..., description="Secret name")
    description: str = Field(..., description="Secret description")
    created_at: str | None = Field(None, description="Creation timestamp", alias="createdAt")
    updated_at: str | None = Field(None, description="Last update timestamp", alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)
