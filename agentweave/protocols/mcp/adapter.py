"""MCP to AgentWeave tool adapter.

This module bridges MCP tools into AgentWeave's tool system,
allowing MCP tools to work seamlessly with Agent's ToolExecutor.
"""

from __future__ import annotations

from typing import Any

from agentweave.protocols.mcp.client import MCPClient
from agentweave.protocols.mcp.types import MCPTool
from agentweave.tools.base import Tool, ToolParameter
from agentweave.tools.executor import ToolExecutor


def _convert_parameters(input_schema: dict[str, Any]) -> list[ToolParameter]:
    """Convert MCP input schema to ToolParameter list.

    Args:
        input_schema: JSON Schema dict with "properties" and "required" fields.

    Returns:
        List of ToolParameter objects.
    """
    properties = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))

    parameters = []
    for name, schema in properties.items():
        param = ToolParameter(
            name=name,
            type=schema.get("type", "string"),
            description=schema.get("description", ""),
            required=name in required,
            enum=schema.get("enum"),
        )
        parameters.append(param)

    return parameters


def mcp_tool_to_tool(mcp_tool: MCPTool, mcp_client: MCPClient) -> Tool:
    """Convert an MCPTool to an AgentWeave Tool.

    Creates an async wrapper function that calls the MCP client's call_tool method.

    Args:
        mcp_tool: The MCP tool to convert.
        mcp_client: The MCP client instance to use for tool calls.

    Returns:
        Tool configured to call the MCP tool via the client.

    Example:
        >>> tool = mcp_tool_to_tool(mcp_tool, mcp_client)
        >>> result = await tool.execute(arg1="value1", arg2="value2")
    """
    tool_name = mcp_tool.name

    async def wrapper(**kwargs: Any) -> str:
        """Wrapper function that calls MCP client's call_tool."""
        result = await mcp_client.call_tool(tool_name, kwargs)

        if result.is_error:
            raise RuntimeError(result.content)

        return result.content

    parameters = _convert_parameters(mcp_tool.input_schema)

    return Tool(
        name=mcp_tool.name,
        description=mcp_tool.description,
        parameters=parameters,
        func=wrapper,
    )


def mcp_tools_to_tools(mcp_tools: list[MCPTool], mcp_client: MCPClient) -> list[Tool]:
    """Batch convert multiple MCPTools to AgentWeave Tools.

    Args:
        mcp_tools: List of MCP tools to convert.
        mcp_client: The MCP client instance to use for tool calls.

    Returns:
        List of AgentWeave Tool objects.
    """
    return [mcp_tool_to_tool(mcp_tool, mcp_client) for mcp_tool in mcp_tools]


async def register_mcp_tools(mcp_client: MCPClient, executor: ToolExecutor) -> list[str]:
    """Register all MCP tools with a ToolExecutor.

    Gets all tools from the MCP client (already cached after connect),
    converts them to AgentWeave Tools, and registers them with the executor.

    Args:
        mcp_client: The MCP client with connected servers.
        executor: The ToolExecutor to register tools with.

    Returns:
        List of registered tool names.

    Example:
        >>> async with MCPClient() as mcp:
        ...     await mcp.connect("npx", ["-y", "@anthropic/mcp-server-filesystem"])
        ...     executor = ToolExecutor()
        ...     tool_names = await register_mcp_tools(mcp, executor)
        ...     print(f"Registered {len(tool_names)} tools: {tool_names}")
    """
    mcp_tools = await mcp_client.list_tools()

    # Convert and register each tool
    tools = mcp_tools_to_tools(mcp_tools, mcp_client)
    tool_names = []

    for tool in tools:
        executor.register(tool)
        tool_names.append(tool.name)

    return tool_names
