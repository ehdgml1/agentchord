"""MCP type definitions.

This module defines data structures for MCP integration.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MCPServerConfig(BaseModel):
    """Configuration for connecting to an MCP server.

    Example:
        >>> config = MCPServerConfig(
        ...     command="npx",
        ...     args=["-y", "@anthropic/mcp-server-github"],
        ...     env={"GITHUB_TOKEN": "..."},
        ... )
    """

    command: str = Field(..., description="Command to execute (e.g., 'npx', 'uvx')")
    args: list[str] = Field(default_factory=list, description="Command arguments")
    env: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables for the server process",
    )
    server_id: str | None = Field(
        None,
        description="Optional identifier for this server. Auto-generated if not provided.",
    )

    def get_server_id(self) -> str:
        """Get or generate server ID."""
        if self.server_id:
            return self.server_id
        # Generate from command and first arg
        if self.args:
            return f"{self.command}:{self.args[0]}"
        return self.command


class MCPToolParameter(BaseModel):
    """Parameter definition for an MCP tool."""

    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type (e.g., 'string', 'number')")
    description: str = Field("", description="Parameter description")
    required: bool = Field(False, description="Whether parameter is required")


class MCPTool(BaseModel):
    """MCP Tool definition.

    Represents a tool provided by an MCP server that can be called.

    Example:
        >>> tool = MCPTool(
        ...     name="read_file",
        ...     description="Read contents of a file",
        ...     input_schema={
        ...         "type": "object",
        ...         "properties": {"path": {"type": "string"}},
        ...     },
        ...     server_id="filesystem",
        ... )
    """

    name: str = Field(..., description="Tool name")
    description: str = Field("", description="Tool description")
    input_schema: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema for tool input parameters",
    )
    server_id: str = Field(..., description="ID of the server providing this tool")

    @property
    def parameters(self) -> list[MCPToolParameter]:
        """Extract parameters from input schema."""
        props = self.input_schema.get("properties", {})
        required = set(self.input_schema.get("required", []))

        params = []
        for name, schema in props.items():
            params.append(
                MCPToolParameter(
                    name=name,
                    type=schema.get("type", "string"),
                    description=schema.get("description", ""),
                    required=name in required,
                )
            )
        return params


class MCPToolResult(BaseModel):
    """Result from calling an MCP tool."""

    content: str = Field(..., description="Text content of the result")
    is_error: bool = Field(False, description="Whether the result is an error")
    raw_content: list[Any] = Field(
        default_factory=list,
        description="Raw content blocks from the MCP response",
    )
