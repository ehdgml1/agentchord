"""Tool executor for managing and running tools."""

from __future__ import annotations

from typing import Any

from agentweave.tools.base import Tool, ToolResult


class ToolExecutor:
    """Manages and executes tools.

    Example:
        >>> executor = ToolExecutor([add_tool, multiply_tool])
        >>> result = await executor.execute("add", a=1, b=2)
        >>> print(result.result)  # 3
    """

    def __init__(self, tools: list[Tool] | None = None) -> None:
        """Initialize with a list of tools."""
        self._tools: dict[str, Tool] = {}
        if tools:
            for t in tools:
                self.register(t)

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> bool:
        """Unregister a tool by name. Returns True if found."""
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        """Get all registered tools."""
        return list(self._tools.values())

    @property
    def tool_names(self) -> list[str]:
        """Get names of all registered tools."""
        return list(self._tools.keys())

    async def execute(
        self,
        name: str,
        tool_call_id: str | None = None,
        **arguments: Any,
    ) -> ToolResult:
        """Execute a tool by name.

        Args:
            name: Name of the tool to execute.
            tool_call_id: Optional ID for this tool call.
            **arguments: Arguments to pass to the tool.

        Returns:
            ToolResult with success/failure and result/error.
        """
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult.error_result(
                name,
                f"Tool '{name}' not found",
                tool_call_id,
            )

        result = await tool.execute(**arguments)
        if tool_call_id:
            result.tool_call_id = tool_call_id
        return result

    def to_openai_tools(self) -> list[dict[str, Any]]:
        """Convert all tools to OpenAI format."""
        return [tool.to_openai_schema() for tool in self._tools.values()]

    def to_anthropic_tools(self) -> list[dict[str, Any]]:
        """Convert all tools to Anthropic format."""
        return [tool.to_anthropic_schema() for tool in self._tools.values()]

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
