"""Unit tests for Tool module."""

from __future__ import annotations

import pytest

from agentweave.tools.base import Tool, ToolParameter, ToolResult
from agentweave.tools.decorator import tool, _python_type_to_json_type
from agentweave.tools.executor import ToolExecutor


class TestToolParameter:
    """Tests for ToolParameter."""

    def test_parameter_creation(self) -> None:
        """Should create parameter with defaults."""
        param = ToolParameter(name="x", type="integer")

        assert param.name == "x"
        assert param.type == "integer"
        assert param.required is True
        assert param.default is None

    def test_parameter_with_options(self) -> None:
        """Should accept all options."""
        param = ToolParameter(
            name="color",
            type="string",
            description="Pick a color",
            required=False,
            enum=["red", "green", "blue"],
        )

        assert param.description == "Pick a color"
        assert param.required is False
        assert param.enum == ["red", "green", "blue"]


class TestToolResult:
    """Tests for ToolResult."""

    def test_success_result(self) -> None:
        """Should create success result."""
        result = ToolResult.success_result("add", 42)

        assert result.tool_name == "add"
        assert result.success is True
        assert result.result == 42
        assert result.error is None

    def test_error_result(self) -> None:
        """Should create error result."""
        result = ToolResult.error_result("divide", "Division by zero")

        assert result.tool_name == "divide"
        assert result.success is False
        assert result.error == "Division by zero"


class TestTool:
    """Tests for Tool."""

    def test_tool_creation(self) -> None:
        """Should create tool from function."""
        def add(a: int, b: int) -> int:
            return a + b

        t = Tool(
            name="add",
            description="Add two numbers",
            parameters=[
                ToolParameter(name="a", type="integer"),
                ToolParameter(name="b", type="integer"),
            ],
            func=add,
        )

        assert t.name == "add"
        assert len(t.parameters) == 2
        assert t.is_async is False

    @pytest.mark.asyncio
    async def test_tool_execute_sync(self) -> None:
        """Should execute sync function."""
        def multiply(a: int, b: int) -> int:
            return a * b

        t = Tool(name="multiply", description="Multiply", func=multiply, parameters=[])
        result = await t.execute(a=3, b=4)

        assert result.success is True
        assert result.result == 12

    @pytest.mark.asyncio
    async def test_tool_execute_async(self) -> None:
        """Should execute async function."""
        async def async_add(a: int, b: int) -> int:
            return a + b

        t = Tool(name="async_add", description="Async add", func=async_add, parameters=[])
        result = await t.execute(a=5, b=7)

        assert result.success is True
        assert result.result == 12

    @pytest.mark.asyncio
    async def test_tool_execute_error(self) -> None:
        """Should capture errors."""
        def failing() -> None:
            raise ValueError("Something went wrong")

        t = Tool(name="failing", description="Always fails", func=failing, parameters=[])
        result = await t.execute()

        assert result.success is False
        assert "Something went wrong" in result.error

    def test_to_openai_schema(self) -> None:
        """Should convert to OpenAI format."""
        t = Tool(
            name="search",
            description="Search the web",
            parameters=[
                ToolParameter(name="query", type="string", description="Search query"),
            ],
            func=lambda q: q,
        )

        schema = t.to_openai_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "search"
        assert "query" in schema["function"]["parameters"]["properties"]

    def test_to_anthropic_schema(self) -> None:
        """Should convert to Anthropic format."""
        t = Tool(
            name="search",
            description="Search the web",
            parameters=[
                ToolParameter(name="query", type="string"),
            ],
            func=lambda q: q,
        )

        schema = t.to_anthropic_schema()

        assert schema["name"] == "search"
        assert "input_schema" in schema


class TestToolDecorator:
    """Tests for @tool decorator."""

    def test_type_conversion(self) -> None:
        """Should convert Python types to JSON types."""
        assert _python_type_to_json_type(str) == "string"
        assert _python_type_to_json_type(int) == "integer"
        assert _python_type_to_json_type(float) == "number"
        assert _python_type_to_json_type(bool) == "boolean"
        assert _python_type_to_json_type(list) == "array"
        assert _python_type_to_json_type(dict) == "object"

    def test_decorator_basic(self) -> None:
        """Should create tool from decorated function."""
        @tool(description="Add two numbers")
        def add(a: int, b: int) -> int:
            return a + b

        assert isinstance(add, Tool)
        assert add.name == "add"
        assert add.description == "Add two numbers"
        assert len(add.parameters) == 2

    def test_decorator_custom_name(self) -> None:
        """Should use custom name."""
        @tool(name="custom_name", description="Test")
        def original_name() -> None:
            pass

        assert original_name.name == "custom_name"

    def test_decorator_extracts_params(self) -> None:
        """Should extract parameter info."""
        @tool(description="Greet")
        def greet(name: str, age: int = 18) -> str:
            return f"Hello {name}, {age}"

        params = {p.name: p for p in greet.parameters}

        assert params["name"].type == "string"
        assert params["name"].required is True
        assert params["age"].type == "integer"
        assert params["age"].required is False
        assert params["age"].default == 18


class TestToolExecutor:
    """Tests for ToolExecutor."""

    def test_register_and_get(self) -> None:
        """Should register and retrieve tools."""
        @tool(description="Add")
        def add(a: int, b: int) -> int:
            return a + b

        executor = ToolExecutor([add])

        assert "add" in executor
        assert executor.get("add") == add
        assert len(executor) == 1

    def test_unregister(self) -> None:
        """Should unregister tools."""
        @tool(description="Test")
        def test_func() -> None:
            pass

        executor = ToolExecutor([test_func])
        removed = executor.unregister("test_func")

        assert removed is True
        assert "test_func" not in executor

    @pytest.mark.asyncio
    async def test_execute(self) -> None:
        """Should execute tool by name."""
        @tool(description="Add")
        def add(a: int, b: int) -> int:
            return a + b

        executor = ToolExecutor([add])
        result = await executor.execute("add", a=3, b=4)

        assert result.success is True
        assert result.result == 7

    @pytest.mark.asyncio
    async def test_execute_not_found(self) -> None:
        """Should return error for unknown tool."""
        executor = ToolExecutor()
        result = await executor.execute("unknown")

        assert result.success is False
        assert "not found" in result.error

    def test_to_openai_tools(self) -> None:
        """Should convert all tools to OpenAI format."""
        @tool(description="Add")
        def add(a: int, b: int) -> int:
            return a + b

        executor = ToolExecutor([add])
        tools = executor.to_openai_tools()

        assert len(tools) == 1
        assert tools[0]["type"] == "function"
