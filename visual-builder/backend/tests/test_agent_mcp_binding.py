"""Tests for Agent MCP tool binding.

This module tests the integration between Agent nodes and MCP tools,
ensuring that tools can be properly bound to agents at runtime.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from typing import Any

from app.core.executor import WorkflowNode
from app.core.mcp_manager import MCPTool


@pytest.mark.asyncio
class TestAgentMCPBinding:
    """Test suite for Agent MCP tool binding."""

    async def test_agent_without_mcp_tools(self, executor, simple_workflow):
        """Test that Agent node works without mcpTools (backward compatibility)."""
        # Run workflow in mock mode
        execution = await executor.run(simple_workflow, "test input", mode="mock")

        # Should complete successfully
        assert execution.status == "completed"
        assert len(execution.node_executions) == 2

    async def test_build_agent_tools_valid(self, executor):
        """Test _build_agent_tools creates Tool objects from valid IDs."""
        # Setup mock MCP tools
        executor.mcp_manager._tools = {
            "test-server": [
                MCPTool(
                    server_id="test-server",
                    name="get_weather",
                    description="Get weather information",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "City name",
                            },
                            "units": {
                                "type": "string",
                                "description": "Temperature units",
                                "enum": ["celsius", "fahrenheit"],
                            },
                        },
                        "required": ["location"],
                    },
                ),
            ],
        }

        # Build tools
        tools = await executor._build_agent_tools(["test-server:get_weather"])

        # Verify
        assert len(tools) == 1
        tool = tools[0]
        assert tool.name == "test-server__get_weather"
        assert tool.description == "Get weather information"
        assert len(tool.parameters) == 2

        # Check parameters
        location_param = next(p for p in tool.parameters if p.name == "location")
        assert location_param.type == "string"
        assert location_param.required is True
        assert location_param.description == "City name"

        units_param = next(p for p in tool.parameters if p.name == "units")
        assert units_param.type == "string"
        assert units_param.required is False
        assert units_param.enum == ["celsius", "fahrenheit"]

    async def test_build_agent_tools_invalid_format(self, executor, caplog):
        """Test that invalid format IDs are skipped with warning."""
        # Build tools with invalid IDs
        tools = await executor._build_agent_tools([
            "invalid-format",
            "also:invalid:format",
            "",
        ])

        # Should return empty list
        assert len(tools) == 0

        # Check warnings were logged
        assert "Invalid MCP tool ID format" in caplog.text

    async def test_build_agent_tools_missing_tool(self, executor, caplog):
        """Test that missing tools are skipped with warning."""
        # Setup empty tools
        executor.mcp_manager._tools = {"test-server": []}

        # Build tools with non-existent tool
        tools = await executor._build_agent_tools(["test-server:nonexistent"])

        # Should return empty list
        assert len(tools) == 0

        # Check warning was logged
        assert "MCP tool not found: test-server:nonexistent" in caplog.text

    async def test_schema_to_tool_params(self, executor):
        """Test JSON Schema conversion to ToolParameter list."""
        schema = {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "User name",
                },
                "age": {
                    "type": "integer",
                    "description": "User age",
                    "default": 0,
                },
                "role": {
                    "type": "string",
                    "description": "User role",
                    "enum": ["admin", "user", "guest"],
                },
                "active": {
                    "type": "boolean",
                    "description": "Is active",
                },
            },
            "required": ["name", "role"],
        }

        params = executor._schema_to_tool_params(schema)

        # Should have 4 parameters
        assert len(params) == 4

        # Check name parameter
        name_param = next(p for p in params if p.name == "name")
        assert name_param.type == "string"
        assert name_param.required is True
        assert name_param.description == "User name"

        # Check age parameter
        age_param = next(p for p in params if p.name == "age")
        assert age_param.type == "integer"
        assert age_param.required is False
        assert age_param.default == 0

        # Check role parameter
        role_param = next(p for p in params if p.name == "role")
        assert role_param.type == "string"
        assert role_param.required is True
        assert role_param.enum == ["admin", "user", "guest"]

        # Check active parameter
        active_param = next(p for p in params if p.name == "active")
        assert active_param.type == "boolean"
        assert active_param.required is False

    async def test_find_mcp_tool_found(self, executor):
        """Test _find_mcp_tool returns MCPTool when it exists."""
        # Setup mock tools
        tool = MCPTool(
            server_id="test-server",
            name="test_tool",
            description="Test tool",
            input_schema={"type": "object", "properties": {}},
        )
        executor.mcp_manager._tools = {"test-server": [tool]}

        # Find tool
        found = executor._find_mcp_tool("test-server", "test_tool")

        # Verify
        assert found is not None
        assert found.name == "test_tool"
        assert found.server_id == "test-server"

    async def test_find_mcp_tool_not_found(self, executor):
        """Test _find_mcp_tool returns None when tool doesn't exist."""
        # Setup empty tools
        executor.mcp_manager._tools = {"test-server": []}

        # Find non-existent tool
        found = executor._find_mcp_tool("test-server", "nonexistent")

        # Should return None
        assert found is None

    async def test_agent_with_mcp_tools_mock_mode(self, executor):
        """Test Agent node with mcpTools runs in mock mode."""
        from app.core.executor import Workflow, WorkflowNode, WorkflowEdge
        import uuid

        # Create workflow with agent that has mcpTools
        nodes = [
            WorkflowNode(
                id="agent-1",
                type="agent",
                data={
                    "name": "Test Agent",
                    "role": "Assistant",
                    "model": "gpt-4o-mini",
                    "mcpTools": ["test-server:get_weather"],
                },
            ),
        ]

        workflow = Workflow(
            id=str(uuid.uuid4()),
            name="Test Workflow",
            nodes=nodes,
            edges=[],
            description="Test workflow with MCP tools",
        )

        # Setup mock tools
        executor.mcp_manager._tools = {
            "test-server": [
                MCPTool(
                    server_id="test-server",
                    name="get_weather",
                    description="Get weather",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "location": {"type": "string"},
                        },
                        "required": ["location"],
                    },
                ),
            ],
        }

        # Run workflow in mock mode
        execution = await executor.run(workflow, "test input", mode="mock")

        # Should complete successfully
        assert execution.status == "completed"

    async def test_schema_to_tool_params_empty_schema(self, executor):
        """Test _schema_to_tool_params handles empty schema."""
        schema = {"type": "object", "properties": {}}

        params = executor._schema_to_tool_params(schema)

        # Should return empty list
        assert len(params) == 0

    async def test_schema_to_tool_params_no_required(self, executor):
        """Test _schema_to_tool_params handles schema without required field."""
        schema = {
            "type": "object",
            "properties": {
                "optional_param": {
                    "type": "string",
                    "description": "Optional parameter",
                },
            },
        }

        params = executor._schema_to_tool_params(schema)

        # Should have 1 parameter
        assert len(params) == 1
        assert params[0].name == "optional_param"
        assert params[0].required is False

    async def test_find_mcp_tool_server_not_found(self, executor):
        """Test _find_mcp_tool handles non-existent server."""
        # Setup empty tools
        executor.mcp_manager._tools = {}

        # Find tool from non-existent server
        found = executor._find_mcp_tool("nonexistent-server", "test_tool")

        # Should return None
        assert found is None

    async def test_build_agent_tools_multiple_tools(self, executor):
        """Test _build_agent_tools handles multiple tools."""
        # Setup mock tools
        executor.mcp_manager._tools = {
            "server1": [
                MCPTool(
                    server_id="server1",
                    name="tool1",
                    description="Tool 1",
                    input_schema={
                        "type": "object",
                        "properties": {"param1": {"type": "string"}},
                    },
                ),
            ],
            "server2": [
                MCPTool(
                    server_id="server2",
                    name="tool2",
                    description="Tool 2",
                    input_schema={
                        "type": "object",
                        "properties": {"param2": {"type": "integer"}},
                    },
                ),
            ],
        }

        # Build tools
        tools = await executor._build_agent_tools([
            "server1:tool1",
            "server2:tool2",
        ])

        # Verify
        assert len(tools) == 2
        assert tools[0].name == "server1__tool1"
        assert tools[1].name == "server2__tool2"

    async def test_build_agent_tools_partial_success(self, executor, caplog):
        """Test _build_agent_tools handles partial success (some valid, some invalid)."""
        # Setup mock tools
        executor.mcp_manager._tools = {
            "server1": [
                MCPTool(
                    server_id="server1",
                    name="tool1",
                    description="Tool 1",
                    input_schema={
                        "type": "object",
                        "properties": {},
                    },
                ),
            ],
        }

        # Build tools with mix of valid and invalid IDs
        tools = await executor._build_agent_tools([
            "server1:tool1",  # Valid
            "invalid-format",  # Invalid
            "server2:tool2",  # Missing server
        ])

        # Should return only valid tool
        assert len(tools) == 1
        assert tools[0].name == "server1__tool1"

        # Check warnings were logged
        assert "Invalid MCP tool ID format" in caplog.text
        assert "MCP tool not found" in caplog.text
