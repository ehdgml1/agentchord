"""Tool base classes."""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Awaitable
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict


class ToolParameter(BaseModel):
    """Tool parameter definition."""

    name: str
    type: str  # "string", "integer", "number", "boolean", "array", "object"
    description: str = ""
    required: bool = True
    default: Any = None
    enum: list[Any] | None = None


class ToolResult(BaseModel):
    """Result of a tool execution."""

    tool_call_id: str = Field(default_factory=lambda: str(uuid4()))
    tool_name: str
    success: bool
    result: Any = None
    error: str | None = None

    @classmethod
    def success_result(cls, tool_name: str, result: Any, tool_call_id: str | None = None) -> "ToolResult":
        """Create a successful result."""
        return cls(
            tool_call_id=tool_call_id or str(uuid4()),
            tool_name=tool_name,
            success=True,
            result=result,
        )

    @classmethod
    def error_result(cls, tool_name: str, error: str, tool_call_id: str | None = None) -> "ToolResult":
        """Create an error result."""
        return cls(
            tool_call_id=tool_call_id or str(uuid4()),
            tool_name=tool_name,
            success=False,
            error=error,
        )


class Tool(BaseModel):
    """A tool that can be used by an agent."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    parameters: list[ToolParameter] = Field(default_factory=list)
    func: Callable[..., Any] | Callable[..., Awaitable[Any]]

    @property
    def is_async(self) -> bool:
        """Check if the tool function is async."""
        return asyncio.iscoroutinefunction(self.func)

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with given arguments."""
        try:
            if self.is_async:
                result = await self.func(**kwargs)
            else:
                result = self.func(**kwargs)
            return ToolResult.success_result(self.name, result)
        except Exception as e:
            return ToolResult.error_result(self.name, str(e))

    def to_openai_schema(self) -> dict[str, Any]:
        """Convert to OpenAI function calling schema."""
        properties = {}
        required = []

        for param in self.parameters:
            prop: dict[str, Any] = {"type": param.type}
            if param.description:
                prop["description"] = param.description
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default
            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def to_anthropic_schema(self) -> dict[str, Any]:
        """Convert to Anthropic tool schema."""
        properties = {}
        required = []

        for param in self.parameters:
            prop: dict[str, Any] = {"type": param.type}
            if param.description:
                prop["description"] = param.description
            if param.enum:
                prop["enum"] = param.enum
            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }
