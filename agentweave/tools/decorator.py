"""Tool decorator for converting functions to tools."""

from __future__ import annotations

import inspect
from typing import Any, Callable, TypeVar, get_type_hints

from agentweave.tools.base import Tool, ToolParameter


F = TypeVar("F", bound=Callable[..., Any])


def _python_type_to_json_type(python_type: type) -> str:
    """Convert Python type to JSON schema type."""
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }

    # Handle Optional types
    origin = getattr(python_type, "__origin__", None)
    if origin is not None:
        # For Union types (including Optional), use the first non-None type
        args = getattr(python_type, "__args__", ())
        for arg in args:
            if arg is not type(None):
                return _python_type_to_json_type(arg)

    return type_map.get(python_type, "string")


def _extract_parameters(func: Callable[..., Any]) -> list[ToolParameter]:
    """Extract parameters from function signature."""
    sig = inspect.signature(func)
    type_hints = get_type_hints(func) if hasattr(func, "__annotations__") else {}

    parameters = []
    for name, param in sig.parameters.items():
        if name in ("self", "cls"):
            continue

        python_type = type_hints.get(name, str)
        json_type = _python_type_to_json_type(python_type)

        # Get description from docstring if available
        description = ""

        # Check if parameter has default
        has_default = param.default is not inspect.Parameter.empty
        default = param.default if has_default else None

        # Check if type is Optional (has None in union)
        is_optional = False
        origin = getattr(python_type, "__origin__", None)
        if origin is not None:
            args = getattr(python_type, "__args__", ())
            is_optional = type(None) in args

        parameters.append(ToolParameter(
            name=name,
            type=json_type,
            description=description,
            required=not has_default and not is_optional,
            default=default,
        ))

    return parameters


def tool(
    name: str | None = None,
    description: str | None = None,
) -> Callable[[F], Tool]:
    """Decorator to convert a function into a Tool.

    Example:
        @tool(description="Add two numbers together")
        def add(a: int, b: int) -> int:
            return a + b

        # Use with agent
        agent = Agent(name="math", role="Calculator", tools=[add])
    """
    def decorator(func: F) -> Tool:
        tool_name = name or func.__name__
        tool_description = description or func.__doc__ or f"Tool: {tool_name}"

        # Clean up description (first line of docstring)
        if "\n" in tool_description:
            tool_description = tool_description.split("\n")[0].strip()

        parameters = _extract_parameters(func)

        return Tool(
            name=tool_name,
            description=tool_description,
            parameters=parameters,
            func=func,
        )

    return decorator
