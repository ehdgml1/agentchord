# Tools API Reference

Complete API reference for the tool system that enables agents to execute functions.

## @tool Decorator

Decorator to convert a Python function into a tool that agents can call.

```python
from agentweave.tools import tool

@tool(name="add", description="Add two numbers together")
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b

@tool(description="Fetch content from a URL")
async def fetch_url(url: str) -> str:
    """Fetch HTML content from a URL."""
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str \| None` | None | Tool name (auto-derived from function name if None) |
| `description` | `str \| None` | None | Tool description shown to LLM |

**Returns:**

| Type | Description |
|------|-------------|
| `Tool` | Converted tool object |

**Notes:**

- Decorator extracts parameter types from function signature
- Supports both sync and async functions
- Docstring is used as description if `description` not provided

## Tool

A function wrapped as a tool that agents can call.

```python
from agentweave.tools import Tool, ToolParameter

# Create directly (less common)
tool = Tool(
    name="search",
    description="Search the web",
    parameters=[
        ToolParameter(
            name="query",
            type="string",
            description="Search query",
            required=True
        )
    ],
    func=lambda query: f"Results for {query}"
)

# More common: use decorator
@tool(description="Search the web")
def search(query: str) -> str:
    return f"Results for {query}"
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Tool name |
| `description` | `str` | Tool description |
| `parameters` | `list[ToolParameter]` | Input parameters |
| `func` | `Callable` | Underlying function |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `is_async` | `bool` | True if function is async |

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `execute` | `async execute(**kwargs: Any) -> ToolResult` | `ToolResult` | Execute tool with arguments |
| `to_openai_schema` | `to_openai_schema() -> dict[str, Any]` | `dict` | Convert to OpenAI function schema |
| `to_anthropic_schema` | `to_anthropic_schema() -> dict[str, Any]` | `dict` | Convert to Anthropic tool schema |

**Example:**

```python
# Define tool
@tool(description="Calculate factorial")
def factorial(n: int) -> int:
    """Calculate n!"""
    if n <= 1:
        return 1
    return n * factorial(n - 1)

# Use in agent
agent = Agent(
    name="calculator",
    role="You are a math tutor",
    tools=[factorial]
)

result = await agent.run("What is 5 factorial?")
```

## ToolParameter

Definition of a tool's input parameter.

```python
from agentweave.tools import ToolParameter

param = ToolParameter(
    name="query",
    type="string",
    description="Search query string",
    required=True,
    enum=["python", "javascript", "rust"]
)
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | Required | Parameter name |
| `type` | `str` | Required | Type: string, integer, number, boolean, array, object |
| `description` | `str` | "" | Parameter description for LLM |
| `required` | `bool` | True | Whether parameter is required |
| `default` | `Any` | None | Default value if not provided |
| `enum` | `list[Any] \| None` | None | Allowed values |

**Supported Types:**

| Type | Python Type | Example |
|------|-------------|---------|
| "string" | `str` | "hello" |
| "integer" | `int` | 42 |
| "number" | `float` | 3.14 |
| "boolean" | `bool` | True |
| "array" | `list` | [1, 2, 3] |
| "object" | `dict` | {"key": "value"} |

## ToolResult

Result of executing a tool.

```python
from agentweave.tools import ToolResult

# Successful execution
result = ToolResult.success_result(
    tool_name="search",
    result="Found 42 results",
    tool_call_id="call_123"
)

# Failed execution
result = ToolResult.error_result(
    tool_name="search",
    error="Connection timeout",
    tool_call_id="call_123"
)
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `tool_call_id` | `str` | Unique identifier for tool call |
| `tool_name` | `str` | Name of the tool executed |
| `success` | `bool` | True if execution succeeded |
| `result` | `Any` | Execution result (if successful) |
| `error` | `str \| None` | Error message (if failed) |

**Class Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `success_result` | `success_result(tool_name: str, result: Any, tool_call_id: str \| None = None) -> ToolResult` | `ToolResult` | Create successful result |
| `error_result` | `error_result(tool_name: str, error: str, tool_call_id: str \| None = None) -> ToolResult` | `ToolResult` | Create error result |

## ToolExecutor

Manages tool registration and execution.

```python
from agentweave.tools import ToolExecutor, tool

# Create executor with tools
@tool(description="Add numbers")
def add(a: int, b: int) -> int:
    return a + b

@tool(description="Multiply numbers")
def multiply(a: int, b: int) -> int:
    return a * b

executor = ToolExecutor(tools=[add, multiply])

# Or register tools after creation
executor = ToolExecutor()
executor.register(add)
executor.register(multiply)

# Execute a tool
result = await executor.execute("add", a=5, b=3, tool_call_id="call_123")
print(result.result)  # 8

# List available tools
tools_list = executor.list_tools()
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tools` | `list[Tool] \| None` | None | Initial tools to register |

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `register` | `register(tool: Tool) -> None` | `None` | Register a tool |
| `execute` | `async execute(name: str, tool_call_id: str \| None = None, **kwargs) -> ToolResult` | `ToolResult` | Execute named tool |
| `list_tools` | `list_tools() -> list[Tool]` | `list[Tool]` | Get all registered tools |
| `to_openai_tools` | `to_openai_tools() -> list[dict]` | `list[dict]` | Get OpenAI function schemas |
| `to_anthropic_tools` | `to_anthropic_tools() -> list[dict]` | `list[dict]` | Get Anthropic tool schemas |

## Complete Example

```python
from agentweave.tools import tool
from agentweave.core import Agent

# Define tools
@tool(description="Search Wikipedia for a topic")
async def search_wikipedia(topic: str) -> str:
    """Search Wikipedia and return summary."""
    import httpx
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
        return data.get("extract", "No results")

@tool(description="Count words in text")
def count_words(text: str) -> int:
    """Count number of words in text."""
    return len(text.split())

# Create agent with tools
agent = Agent(
    name="researcher",
    role="You are a research assistant. Use tools to find information.",
    tools=[search_wikipedia, count_words]
)

# Use agent
result = await agent.run(
    "Tell me about Python programming and count the words in the result"
)
print(f"Output: {result.output}")
print(f"Cost: ${result.cost:.4f}")
```

## Tool Schemas

Tools are automatically converted to LLM-specific schemas:

### OpenAI Schema

```python
{
    "type": "function",
    "function": {
        "name": "search",
        "description": "Search the web",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                }
            },
            "required": ["query"]
        }
    }
}
```

### Anthropic Schema

```python
{
    "name": "search",
    "description": "Search the web",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            }
        },
        "required": ["query"]
    }
}
```

## Best Practices

1. **Clear Descriptions**: Write descriptive tool descriptions so the LLM understands when to use them

```python
# Good
@tool(description="Search the web for current information about a topic")
def search(query: str) -> str:
    pass

# Bad
@tool(description="Search")
def search(query: str) -> str:
    pass
```

2. **Type Hints**: Always include type hints for tool parameters

```python
# Good
@tool(description="Add two numbers")
def add(a: int, b: int) -> int:
    return a + b

# Less helpful to LLM
@tool(description="Add two numbers")
def add(a, b):
    return a + b
```

3. **Error Handling**: Tool functions should handle errors gracefully

```python
@tool(description="Fetch URL")
async def fetch(url: str) -> str:
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)
            response.raise_for_status()
            return response.text
    except Exception as e:
        return f"Error: {e}"
```

4. **Docstrings**: Include docstrings for tool functions

```python
@tool(description="Calculate square root")
def sqrt(n: float) -> float:
    """Calculate the square root of a number."""
    import math
    return math.sqrt(n)
```

See the [Tools Guide](../guides/tools.md) for more usage examples.
