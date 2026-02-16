"""MCP Pydantic schemas for API request/response.

Phase 0 MVP:
- MCPServerCreate, MCPServerResponse
- MCPToolResponse
- Health check response
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MCPServerCreate(BaseModel):
    """MCP server connection request."""

    name: str = Field(..., min_length=1, max_length=100, description="Server name")
    command: str = Field(..., description="Server command to execute")
    args: list[str] = Field(default_factory=list, description="Command arguments")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables")
    description: str = Field("", max_length=500, description="Server description")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "filesystem",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                "description": "Filesystem MCP server"
            }
        }
    )


class MCPToolResponse(BaseModel):
    """MCP tool response."""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    input_schema: dict[str, Any] = Field(..., description="Tool input JSON schema", alias="inputSchema")
    server_id: str = Field(..., description="MCP server ID", alias="serverId")

    model_config = ConfigDict(populate_by_name=True)


class MCPServerResponse(BaseModel):
    """MCP server response."""

    id: str = Field(..., description="Server ID")
    name: str = Field(..., description="Server name")
    command: str = Field(..., description="Server command")
    args: list[str] = Field(..., description="Command arguments")
    description: str = Field(..., description="Server description")
    status: str = Field(..., description="Server status (connected, disconnected, error)")
    tool_count: int = Field(0, description="Number of tools", alias="toolCount")
    last_connected_at: str | None = Field(None, description="Last connection timestamp", alias="lastConnectedAt")
    tools: list[MCPToolResponse] = Field(default_factory=list, description="Available tools")

    model_config = ConfigDict(populate_by_name=True)


class MCPHealthResponse(BaseModel):
    """MCP server health check response."""

    server_id: str = Field(..., description="Server ID", alias="serverId")
    status: str = Field(..., description="Health status (healthy, unhealthy, unknown)")
    message: str | None = Field(None, description="Status message")
    latency_ms: int | None = Field(None, description="Health check latency in milliseconds", alias="latencyMs")

    model_config = ConfigDict(populate_by_name=True)
