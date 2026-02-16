"""MCP (Model Context Protocol) integration.

MCP is an open protocol by Anthropic that standardizes how AI applications
connect to external tools and data sources.

Example:
    >>> from agentweave.protocols.mcp import MCPClient
    >>> async with MCPClient() as mcp:
    ...     await mcp.connect("npx", ["-y", "@anthropic/mcp-server-github"])
    ...     tools = await mcp.list_tools()
    ...     print([t.name for t in tools])
"""

from agentweave.protocols.mcp.types import MCPTool, MCPServerConfig
from agentweave.protocols.mcp.adapter import (
    mcp_tool_to_tool,
    mcp_tools_to_tools,
    register_mcp_tools,
)

__all__ = [
    "MCPTool",
    "MCPServerConfig",
    "mcp_tool_to_tool",
    "mcp_tools_to_tools",
    "register_mcp_tools",
]


def __getattr__(name: str):
    """Lazy import for MCPClient (requires mcp package)."""
    if name == "MCPClient":
        from agentweave.protocols.mcp.client import MCPClient
        return MCPClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
