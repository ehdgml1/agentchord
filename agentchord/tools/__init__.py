"""Tool system for AgentChord.

Provides a way to register Python functions as tools that agents can use.
"""

from agentchord.tools.base import Tool, ToolParameter, ToolResult
from agentchord.tools.decorator import tool
from agentchord.tools.executor import ToolExecutor
from agentchord.tools.web_search import create_web_search_tool

__all__ = [
    "Tool",
    "ToolParameter",
    "ToolResult",
    "tool",
    "ToolExecutor",
    "create_web_search_tool",
]
