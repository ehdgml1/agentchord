# Tools Guide

Tools allow agents to perform actions and retrieve information. AgentWeave provides a simple but powerful tool system that works with any LLM provider.

## Quick Start

Convert any Python function to a tool using the `@tool` decorator:

```python
from agentweave import tool, Agent

@tool(description="Add two numbers")
def add(a: int, b: int) -> int:
    return a + b

agent = Agent(
    name="calculator",
    role="Math helper",
    model="gpt-4o-mini",
    tools=[add]
)

result = agent.run_sync("What is 5 + 3?")
print(result.output)  # "The answer is 8"
```

## Creating Tools with @tool

The `@tool` decorator extracts function signatures and converts them to LLM-compatible tool definitions.

### Basic Tool

```python
@tool(description="Convert text to uppercase")
def uppercase(text: str) -> str:
    return text.upper()
```

The decorator extracts:
- **name**: Function name (or custom via `name=` parameter)
- **description**: Required; tells the LLM what the tool does
- **parameters**: Extracted from function signature with type hints
- **return type**: Function's return type annotation

### Custom Tool Name

```python
@tool(name="uppercase_converter", description="Convert text to uppercase")
def uppercase(text: str) -> str:
    return text.upper()
```

### Async Tools

Tools can be async functions:

```python
import httpx

@tool(description="Fetch content from a URL")
async def fetch_url(url: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text
```

AgentWeave automatically detects async functions and handles them correctly.

### Parameter Types

AgentWeave supports all common Python types:

```python
@tool(description="Process multiple data points")
def process(
    name: str,
    count: int,
    ratio: float,
    enabled: bool,
    tags: list = None,
    metadata: dict = None
) -> dict:
    return {
        "name": name,
        "count": count,
        "ratio": ratio,
        "enabled": enabled,
        "tags": tags or [],
        "metadata": metadata or {}
    }
```

Supported types:
- `str` - text
- `int` - integers
- `float` - decimal numbers
- `bool` - true/false
- `list` - arrays
- `dict` - objects
- Optional types (via `Optional[T]` or `T | None`)

### Optional Parameters

Parameters with defaults are optional:

```python
@tool(description="Search with filters")
def search(
    query: str,
    max_results: int = 10,
    sort_by: str = "relevance"
) -> list:
    # Implementation
    return []
```

LLM sees `max_results` and `sort_by` as optional parameters that can be omitted.

## The Tool Class

Under the hood, `@tool` returns a `Tool` instance:

```python
from agentweave.tools import Tool, ToolParameter

# Equivalent to using @tool decorator
tool_instance = Tool(
    name="add",
    description="Add two numbers",
    parameters=[
        ToolParameter(name="a", type="integer", required=True),
        ToolParameter(name="b", type="integer", required=True),
    ],
    func=lambda a, b: a + b
)
```

### Tool Properties

```python
@tool(description="Divide numbers")
def divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

# Access tool properties
print(divide.name)           # "divide"
print(divide.description)    # "Divide numbers"
print(divide.parameters)     # List of ToolParameter objects
print(divide.is_async)       # False (or True for async functions)
```

### Executing Tools Directly

Execute a tool without an agent:

```python
# Sync execution
result = await divide.execute(a=10, b=2)
print(result.success)  # True
print(result.result)   # 5.0
print(result.tool_name)  # "divide"

# Error handling
result = await divide.execute(a=10, b=0)
print(result.success)  # False
print(result.error)    # "Cannot divide by zero"
```

## Tool Schemas

Tools are automatically converted to LLM provider schemas.

### OpenAI Schema

```python
openai_schema = divide.to_openai_schema()
# {
#   "type": "function",
#   "function": {
#     "name": "divide",
#     "description": "Divide numbers",
#     "parameters": {
#       "type": "object",
#       "properties": {
#         "a": {"type": "number"},
#         "b": {"type": "number"}
#       },
#       "required": ["a", "b"]
#     }
#   }
# }
```

### Anthropic Schema

```python
anthropic_schema = divide.to_anthropic_schema()
# {
#   "name": "divide",
#   "description": "Divide numbers",
#   "input_schema": {
#     "type": "object",
#     "properties": {
#       "a": {"type": "number"},
#       "b": {"type": "number"}
#     },
#     "required": ["a", "b"]
#   }
# }
```

## Using Tools with Agents

### Single Tool

```python
@tool(description="Get current temperature in Celsius")
def get_temp() -> float:
    return 22.5

agent = Agent(
    name="weather",
    role="Weather assistant",
    model="gpt-4o-mini",
    tools=[get_temp]
)

result = agent.run_sync("What is the current temperature?")
```

### Multiple Tools

```python
@tool(description="Add two numbers")
def add(a: int, b: int) -> int:
    return a + b

@tool(description="Subtract two numbers")
def subtract(a: int, b: int) -> int:
    return a - b

@tool(description="Multiply two numbers")
def multiply(a: int, b: int) -> int:
    return a * b

agent = Agent(
    name="calculator",
    role="Math helper",
    model="gpt-4o-mini",
    tools=[add, subtract, multiply]
)

result = agent.run_sync("Calculate (10 + 5) * 2")
# LLM will call add(10, 5) -> 15, then multiply(15, 2) -> 30
```

## Tool Executor

For advanced use cases, manage tools directly with `ToolExecutor`:

```python
from agentweave.tools import ToolExecutor

@tool(description="Add two numbers")
def add(a: int, b: int) -> int:
    return a + b

@tool(description="Subtract two numbers")
def subtract(a: int, b: int) -> int:
    return a - b

executor = ToolExecutor([add, subtract])

# List available tools
print(executor.tool_names)  # ["add", "subtract"]

# Execute a tool by name
result = await executor.execute("add", a=5, b=3)
print(result.success)  # True
print(result.result)   # 8

# Unknown tool
result = await executor.execute("divide", a=10, b=2)
print(result.success)  # False
print(result.error)    # "Tool 'divide' not found"

# List tools as LLM schemas
tools_for_openai = executor.to_openai_schemas()
tools_for_anthropic = executor.to_anthropic_schemas()
```

## Multi-Round Tool Calling

Agents can use multiple tools in sequence:

```python
@tool(description="Search the web")
def web_search(query: str) -> str:
    return "Results for: " + query

@tool(description="Analyze text sentiment")
def analyze_sentiment(text: str) -> str:
    return "positive" if len(text) > 5 else "neutral"

agent = Agent(
    name="analyst",
    role="Research analyst",
    model="gpt-4o-mini",
    tools=[web_search, analyze_sentiment],
    max_tool_rounds=10  # Allow up to 10 tool calls
)

result = agent.run_sync(
    "Search for 'AI trends 2025' and analyze the sentiment of the results"
)
# LLM will:
# 1. Call web_search("AI trends 2025")
# 2. Receive search results
# 3. Call analyze_sentiment(results)
# 4. Receive sentiment
# 5. Provide final analysis
```

The `max_tool_rounds` parameter (default: 10) prevents infinite loops and limits tool calling rounds.

## MCP Tool Integration

AgentWeave can bridge Model Context Protocol (MCP) tools to the agent system:

```python
from agentweave.protocols.mcp.adapter import mcp_tool_to_tool
from agentweave import Agent

# Assume mcp_client is a connected MCPClient instance
mcp_tools = await agent.setup_mcp()  # Auto-register MCP tools
# Tools from MCP are automatically added to the agent
```

The `setup_mcp()` method:
1. Connects to the MCP server
2. Discovers available tools
3. Converts MCPTool → AgentWeave Tool
4. Registers them with the agent

## Error Handling

Tools should raise exceptions for errors; AgentWeave handles them:

```python
@tool(description="Calculate square root")
def sqrt(x: float) -> float:
    if x < 0:
        raise ValueError("Cannot take square root of negative number")
    return x ** 0.5

# When tool raises an exception, ToolResult captures it
result = await sqrt.execute(x=-1)
print(result.success)  # False
print(result.error)    # "Cannot take square root of negative number"

# The agent continues and can retry or provide alternative approach
```

## Best Practices

### 1. Clear Descriptions

Write descriptions that help the LLM understand what the tool does:

```python
# Good
@tool(description="Calculate the factorial of a positive integer")
def factorial(n: int) -> int:
    ...

# Less helpful
@tool(description="Math function")
def factorial(n: int) -> int:
    ...
```

### 2. Type Hints

Always include type hints for parameters:

```python
# Good
@tool(description="Convert temperature")
def celsius_to_fahrenheit(celsius: float) -> float:
    return (celsius * 9/5) + 32

# Harder for type checking
@tool(description="Convert temperature")
def celsius_to_fahrenheit(celsius):
    ...
```

### 3. Simple Return Values

Return simple, serializable values:

```python
# Good
@tool(description="Get user data")
def get_user(user_id: int) -> dict:
    return {"id": user_id, "name": "Alice", "age": 30}

# Problematic - complex objects don't serialize well
@tool(description="Get user data")
def get_user(user_id: int) -> User:
    return User(user_id)
```

### 4. Handle Errors Gracefully

Let exceptions propagate; AgentWeave captures them:

```python
# Good
@tool(description="Divide numbers")
def divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("Division by zero")
    return a / b

# Avoid catching and returning error strings
@tool(description="Divide numbers")
def divide(a: float, b: float) -> dict:
    try:
        return {"result": a / b, "error": None}
    except:
        return {"result": None, "error": "failed"}
```

### 5. Keep Tools Focused

One tool = one responsibility:

```python
# Good - separate concerns
@tool(description="Search the web")
def web_search(query: str) -> str:
    ...

@tool(description="Extract key information from text")
def extract_key_info(text: str) -> dict:
    ...

# Less good - multiple concerns in one tool
@tool(description="Search the web and extract information")
def search_and_extract(query: str) -> dict:
    ...
```

## Complete Example

```python
import asyncio
from agentweave import Agent, tool

@tool(description="Get the current temperature in Celsius")
def get_temperature() -> float:
    return 22.5

@tool(description="Convert Celsius to Fahrenheit")
def celsius_to_fahrenheit(celsius: float) -> float:
    return (celsius * 9/5) + 32

@tool(description="Check if temperature is comfortable (15-25 C)")
def is_comfortable(celsius: float) -> bool:
    return 15 <= celsius <= 25

async def main():
    agent = Agent(
        name="weather_bot",
        role="Weather assistant",
        model="gpt-4o-mini",
        tools=[get_temperature, celsius_to_fahrenheit, is_comfortable]
    )

    result = agent.run_sync(
        "Tell me the current temperature in Fahrenheit and whether it's comfortable"
    )
    print(result.output)

if __name__ == "__main__":
    asyncio.run(main())
```

## See Also

- [Memory Guide](memory.md) - Retain context across tool calls
- [Agent Documentation](../api/core.md) - Agent API details
- [Examples](../examples.md) - Complete tool examples
