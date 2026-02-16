"""Debug mode DTOs.

Phase 2 Task:
- WebSocket message DTOs
- Debug event responses
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Any


class DebugStartRequest(BaseModel):
    """Request to start debug execution.

    Sent by client to initiate debug session.
    """
    input: str = Field(default="", description="Workflow input")
    breakpoints: list[str] = Field(default_factory=list, description="List of node IDs to break at")


class DebugCommand(BaseModel):
    """Debug control command.

    Sent by client during debug session.
    """
    action: str = Field(..., description="Command action: 'continue', 'step', 'stop'")


class DebugEventResponse(BaseModel):
    """Debug event streamed to client.

    Server sends this via WebSocket during debug execution.
    """
    type: str = Field(..., description="Event type: 'node_start', 'breakpoint', 'node_complete', 'complete', 'error', 'timeout'")
    node_id: str | None = Field(None, description="Node ID if applicable", alias="nodeId")
    data: dict[str, Any] | None = Field(None, description="Event payload")
    timestamp: str | None = Field(None, description="Event timestamp (ISO format)")

    model_config = ConfigDict(populate_by_name=True)
