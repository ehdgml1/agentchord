"""Tool system for AgentWeave.

Provides a way to register Python functions as tools that agents can use.
"""

from agentweave.tools.base import Tool, ToolParameter, ToolResult
from agentweave.tools.decorator import tool
from agentweave.tools.executor import ToolExecutor

__all__ = [
    "Tool",
    "ToolParameter",
    "ToolResult",
    "tool",
    "ToolExecutor",
]
