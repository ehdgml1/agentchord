"""Unit tests for MCP types."""

from __future__ import annotations

import pytest

from agentweave.protocols.mcp.types import (
    MCPServerConfig,
    MCPTool,
    MCPToolParameter,
    MCPToolResult,
)


class TestMCPServerConfig:
    """Tests for MCPServerConfig."""

    def test_config_creation(self) -> None:
        """Config should be created with required fields."""
        config = MCPServerConfig(
            command="npx",
            args=["-y", "@anthropic/mcp-server-github"],
        )

        assert config.command == "npx"
        assert config.args == ["-y", "@anthropic/mcp-server-github"]
        assert config.env == {}

    def test_get_server_id_with_explicit_id(self) -> None:
        """get_server_id should return explicit ID if provided."""
        config = MCPServerConfig(
            command="npx",
            args=["-y", "mcp-server"],
            server_id="my-server",
        )

        assert config.get_server_id() == "my-server"

    def test_get_server_id_auto_generated(self) -> None:
        """get_server_id should auto-generate from command and args."""
        config = MCPServerConfig(
            command="npx",
            args=["-y", "@anthropic/mcp-server-github"],
        )

        assert config.get_server_id() == "npx:-y"

    def test_get_server_id_command_only(self) -> None:
        """get_server_id should use command when no args."""
        config = MCPServerConfig(command="my-server")

        assert config.get_server_id() == "my-server"


class TestMCPTool:
    """Tests for MCPTool."""

    def test_tool_creation(self) -> None:
        """Tool should be created with required fields."""
        tool = MCPTool(
            name="read_file",
            description="Read file contents",
            server_id="filesystem",
        )

        assert tool.name == "read_file"
        assert tool.description == "Read file contents"
        assert tool.server_id == "filesystem"

    def test_tool_with_input_schema(self) -> None:
        """Tool should accept input schema."""
        tool = MCPTool(
            name="read_file",
            description="Read file contents",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                },
                "required": ["path"],
            },
            server_id="filesystem",
        )

        assert tool.input_schema["type"] == "object"
        assert "path" in tool.input_schema["properties"]

    def test_tool_parameters_extraction(self) -> None:
        """parameters property should extract from input schema."""
        tool = MCPTool(
            name="create_issue",
            description="Create GitHub issue",
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Issue title"},
                    "body": {"type": "string", "description": "Issue body"},
                },
                "required": ["title"],
            },
            server_id="github",
        )

        params = tool.parameters
        assert len(params) == 2

        title_param = next(p for p in params if p.name == "title")
        assert title_param.type == "string"
        assert title_param.required is True

        body_param = next(p for p in params if p.name == "body")
        assert body_param.required is False


class TestMCPToolResult:
    """Tests for MCPToolResult."""

    def test_result_creation(self) -> None:
        """Result should be created with content."""
        result = MCPToolResult(content="File contents here")

        assert result.content == "File contents here"
        assert result.is_error is False

    def test_result_with_error(self) -> None:
        """Result should support error flag."""
        result = MCPToolResult(
            content="File not found",
            is_error=True,
        )

        assert result.is_error is True
