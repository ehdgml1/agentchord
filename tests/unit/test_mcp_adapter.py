"""Unit tests for MCP adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from agentchord.protocols.mcp.adapter import (
    _convert_parameters,
    mcp_tool_to_tool,
    mcp_tools_to_tools,
    register_mcp_tools,
)
from agentchord.protocols.mcp.types import MCPTool, MCPToolResult
from agentchord.tools.base import Tool, ToolParameter
from agentchord.tools.executor import ToolExecutor


class TestConvertParameters:
    """Tests for _convert_parameters function."""

    def test_basic_properties(self) -> None:
        """Schema with string and integer properties should convert correctly."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "User name"},
                "age": {"type": "integer", "description": "User age"},
            },
        }

        params = _convert_parameters(schema)

        assert len(params) == 2

        name_param = next(p for p in params if p.name == "name")
        assert name_param.type == "string"
        assert name_param.description == "User name"
        assert name_param.required is False  # Not in required list

        age_param = next(p for p in params if p.name == "age")
        assert age_param.type == "integer"
        assert age_param.description == "User age"
        assert age_param.required is False

    def test_required_fields(self) -> None:
        """Schema with 'required' list should mark parameters correctly."""
        schema = {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "encoding": {"type": "string"},
            },
            "required": ["path"],
        }

        params = _convert_parameters(schema)

        path_param = next(p for p in params if p.name == "path")
        assert path_param.required is True

        encoding_param = next(p for p in params if p.name == "encoding")
        assert encoding_param.required is False

    def test_empty_schema(self) -> None:
        """Empty schema should return empty list."""
        schema = {}
        params = _convert_parameters(schema)
        assert params == []

    def test_enum_parameter(self) -> None:
        """Schema with enum constraint should propagate to ToolParameter."""
        schema = {
            "type": "object",
            "properties": {
                "color": {
                    "type": "string",
                    "enum": ["red", "green", "blue"],
                },
            },
        }

        params = _convert_parameters(schema)

        assert len(params) == 1
        assert params[0].name == "color"
        assert params[0].enum == ["red", "green", "blue"]

    def test_description_extraction(self) -> None:
        """Schema with descriptions should propagate to ToolParameter."""
        schema = {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string",
                },
            },
        }

        params = _convert_parameters(schema)

        assert len(params) == 1
        assert params[0].name == "query"
        assert params[0].description == "Search query string"


class TestMCPToolToTool:
    """Tests for mcp_tool_to_tool function."""

    def test_basic_conversion(self) -> None:
        """MCPTool should convert to Tool with correct fields."""
        mcp_tool = MCPTool(
            name="read_file",
            description="Read contents of a file",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                },
                "required": ["path"],
            },
            server_id="test-server",
        )

        mock_client = AsyncMock()
        tool = mcp_tool_to_tool(mcp_tool, mock_client)

        assert isinstance(tool, Tool)
        assert tool.name == "read_file"
        assert tool.description == "Read contents of a file"
        assert len(tool.parameters) == 1
        assert tool.parameters[0].name == "path"
        assert tool.parameters[0].type == "string"
        assert tool.parameters[0].required is True
        assert tool.is_async is True

    @pytest.mark.asyncio
    async def test_wrapper_calls_client(self) -> None:
        """Converted tool should call mcp_client.call_tool with correct args."""
        mcp_tool = MCPTool(
            name="test_tool",
            description="Test tool",
            input_schema={
                "type": "object",
                "properties": {
                    "arg1": {"type": "string"},
                },
            },
            server_id="test-server",
        )

        mock_client = AsyncMock()
        mock_client.call_tool = AsyncMock(
            return_value=MCPToolResult(content="success", is_error=False)
        )

        tool = mcp_tool_to_tool(mcp_tool, mock_client)
        result = await tool.execute(arg1="value1")

        assert result.success is True
        assert result.result == "success"
        mock_client.call_tool.assert_awaited_once_with(
            "test_tool",
            {"arg1": "value1"},
        )

    @pytest.mark.asyncio
    async def test_wrapper_raises_on_error(self) -> None:
        """When MCPToolResult.is_error=True, tool.execute() should return error result."""
        mcp_tool = MCPTool(
            name="failing_tool",
            description="Tool that fails",
            input_schema={},
            server_id="test-server",
        )

        mock_client = AsyncMock()
        mock_client.call_tool = AsyncMock(
            return_value=MCPToolResult(
                content="File not found",
                is_error=True,
            )
        )

        tool = mcp_tool_to_tool(mcp_tool, mock_client)
        result = await tool.execute()

        # Tool.execute catches RuntimeError and returns error result
        assert result.success is False
        assert "File not found" in result.error

    @pytest.mark.asyncio
    async def test_wrapper_returns_content(self) -> None:
        """Successful call should return content string."""
        mcp_tool = MCPTool(
            name="echo",
            description="Echo tool",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                },
            },
            server_id="test-server",
        )

        mock_client = AsyncMock()
        mock_client.call_tool = AsyncMock(
            return_value=MCPToolResult(
                content="echoed message",
                is_error=False,
            )
        )

        tool = mcp_tool_to_tool(mcp_tool, mock_client)
        result = await tool.execute(message="test")

        assert result.success is True
        assert result.result == "echoed message"


class TestMCPToolsToTools:
    """Tests for mcp_tools_to_tools function."""

    def test_batch_conversion(self) -> None:
        """Should convert list of MCPTools to list of Tools."""
        mcp_tools = [
            MCPTool(
                name="tool1",
                description="First tool",
                input_schema={},
                server_id="server1",
            ),
            MCPTool(
                name="tool2",
                description="Second tool",
                input_schema={},
                server_id="server2",
            ),
            MCPTool(
                name="tool3",
                description="Third tool",
                input_schema={},
                server_id="server3",
            ),
        ]

        mock_client = AsyncMock()
        tools = mcp_tools_to_tools(mcp_tools, mock_client)

        assert len(tools) == 3
        assert all(isinstance(t, Tool) for t in tools)
        assert tools[0].name == "tool1"
        assert tools[1].name == "tool2"
        assert tools[2].name == "tool3"


class TestRegisterMCPTools:
    """Tests for register_mcp_tools function."""

    @pytest.mark.asyncio
    async def test_register_tools(self) -> None:
        """Should register all MCP tools with executor."""
        mcp_tools = [
            MCPTool(
                name="read_file",
                description="Read file",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                    },
                },
                server_id="filesystem",
            ),
            MCPTool(
                name="write_file",
                description="Write file",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                },
                server_id="filesystem",
            ),
        ]

        mock_client = AsyncMock()
        mock_client.list_tools = AsyncMock(return_value=mcp_tools)

        executor = ToolExecutor()
        tool_names = await register_mcp_tools(mock_client, executor)

        assert tool_names == ["read_file", "write_file"]
        assert len(executor) == 2
        assert "read_file" in executor
        assert "write_file" in executor

        mock_client.list_tools.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_register_empty(self) -> None:
        """Empty tool list should return empty list."""
        mock_client = AsyncMock()
        mock_client.list_tools = AsyncMock(return_value=[])

        executor = ToolExecutor()
        tool_names = await register_mcp_tools(mock_client, executor)

        assert tool_names == []
        assert len(executor) == 0
