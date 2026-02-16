"""Version DTOs."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class VersionMetadata(BaseModel):
    """Version metadata response."""

    id: str = Field(description="Version ID")
    workflow_id: str = Field(description="Workflow ID", alias="workflowId")
    version_number: int = Field(description="Version number", alias="versionNumber")
    message: str = Field(description="Version message")
    created_at: str = Field(description="Creation timestamp", alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)


class VersionDetail(BaseModel):
    """Detailed version with data."""

    id: str = Field(description="Version ID")
    workflow_id: str = Field(description="Workflow ID", alias="workflowId")
    version_number: int = Field(description="Version number", alias="versionNumber")
    message: str = Field(description="Version message")
    data: dict = Field(description="Workflow data")
    created_at: str = Field(description="Creation timestamp", alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)


class VersionListResponse(BaseModel):
    """Version list response."""

    versions: list[VersionMetadata] = Field(
        description="List of versions"
    )
    total: int = Field(description="Total count")


class VersionCreateRequest(BaseModel):
    """Create version request."""

    message: str = Field(
        default="",
        max_length=500,
        description="Version message",
    )


class VersionRestoreResponse(BaseModel):
    """Version restore response."""

    workflow_id: str = Field(description="Workflow ID", alias="workflowId")
    version_id: str = Field(description="Restored version ID", alias="versionId")
    version_number: int = Field(description="Version number", alias="versionNumber")
    message: str = Field(description="Success message")

    model_config = ConfigDict(populate_by_name=True)
