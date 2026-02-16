# Core API Reference

Complete API reference for AgentWeave core components: agents, workflows, and execution engines.

## Message

A single message in a conversation.

```python
from agentweave.core import Message, MessageRole

# Create messages
msg = Message(role=MessageRole.USER, content="Hello")
msg = Message.user("Hello")
msg = Message.assistant("Hi there!")
msg = Message.system("You are helpful.")
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `role` | `MessageRole` | Message sender role: SYSTEM, USER, ASSISTANT, TOOL |
| `content` | `str` | Message content |
| `name` | `str \| None` | Optional sender name |
| `tool_calls` | `list[ToolCall] \| None` | Tool calls made by assistant |
| `tool_call_id` | `str \| None` | ID of tool call this responds to |

**Class Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `system(content: str)` | `Message` | Create system message |
| `user(content: str)` | `Message` | Create user message |
| `assistant(content: str)` | `Message` | Create assistant message |

## Usage

Token usage statistics for a single LLM call.

```python
from agentweave.core import Usage

usage = Usage(prompt_tokens=100, completion_tokens=50)
print(usage.total_tokens)  # 150
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `prompt_tokens` | `int` | Tokens in the prompt |
| `completion_tokens` | `int` | Tokens in the completion |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `total_tokens` | `int` | Sum of prompt and completion tokens |

## ToolCall

A tool call made by the assistant during generation.

```python
from agentweave.core import ToolCall

tool_call = ToolCall(
    id="call_123",
    name="search",
    arguments={"query": "python"}
)
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique identifier for this tool call |
| `name` | `str` | Name of the tool to call |
| `arguments` | `dict[str, Any]` | Arguments passed to the tool |

## LLMResponse

Response from an LLM provider.

```python
from agentweave.core import LLMResponse, Usage

response = LLMResponse(
    content="Here's the answer...",
    model="gpt-4o-mini",
    usage=Usage(prompt_tokens=100, completion_tokens=50),
    finish_reason="stop"
)
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `content` | `str` | Generated content |
| `model` | `str` | Model used for generation |
| `usage` | `Usage` | Token usage statistics |
| `finish_reason` | `str` | Reason for completion (stop, length, tool_calls, etc.) |
| `tool_calls` | `list[ToolCall] \| None` | Tool calls requested by the model |
| `raw_response` | `dict[str, Any] \| None` | Raw response from the provider |

## AgentResult

Result of an agent execution.

```python
from agentweave.core import AgentResult

result = await agent.run("What is Python?")
print(result.output)        # Final answer
print(result.cost)          # Cost in USD
print(result.usage.total_tokens)  # Total tokens used
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `output` | `str` | Final output from the agent |
| `messages` | `list[Message]` | Full conversation history |
| `usage` | `Usage` | Token usage statistics |
| `cost` | `float` | Estimated cost in USD |
| `duration_ms` | `int` | Execution time in milliseconds |
| `metadata` | `dict[str, Any]` | Additional execution metadata |

## Agent

Main agent class that runs LLM-powered tasks.

```python
from agentweave.core import Agent
from agentweave.tools import tool

@tool(name="search", description="Search the web")
async def search(query: str) -> str:
    return f"Results for {query}"

agent = Agent(
    name="researcher",
    role="You are a research assistant",
    model="gpt-4o-mini",
    tools=[search],
    temperature=0.7,
    max_tokens=4096,
    timeout=60.0
)

result = await agent.run("Find information about Python")
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | Required | Agent name/identifier |
| `role` | `str` | Required | System prompt defining agent's purpose |
| `model` | `str` | "gpt-4o-mini" | LLM model to use |
| `temperature` | `float` | 0.7 | Sampling temperature (0.0-2.0) |
| `max_tokens` | `int` | 4096 | Maximum tokens to generate |
| `timeout` | `float` | 60.0 | Request timeout in seconds |
| `system_prompt` | `str \| None` | None | Override system prompt |
| `llm_provider` | `BaseLLMProvider \| None` | None | Custom LLM provider |
| `memory` | `BaseMemory \| None` | None | Memory system for context |
| `cost_tracker` | `CostTracker \| None` | None | Cost tracking instance |
| `resilience` | `ResilienceConfig \| None` | None | Resilience configuration |
| `tools` | `list[Tool] \| None` | None | Tools available to agent |
| `callbacks` | `CallbackManager \| None` | None | Callback manager |
| `mcp_client` | `MCPClient \| None` | None | Model Context Protocol client |

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `run` | `async run(input: str, *, max_tool_rounds: int = 10) -> AgentResult` | `AgentResult` | Execute agent on input |
| `run_sync` | `run_sync(input: str) -> AgentResult` | `AgentResult` | Sync wrapper for run() |
| `stream` | `async stream(input: str, *, max_tool_rounds: int = 10) -> AsyncIterator[StreamChunk]` | `AsyncIterator[StreamChunk]` | Stream response tokens |
| `setup_mcp` | `async setup_mcp() -> list[str]` | `list[str]` | Register MCP tools, returns tool names |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `name` | `str` | Agent name |
| `role` | `str` | System prompt/role |
| `model` | `str` | LLM model |
| `system_prompt` | `str` | Full system prompt |
| `memory` | `BaseMemory \| None` | Memory instance |
| `cost_tracker` | `CostTracker \| None` | Cost tracker |
| `tools` | `list[Tool]` | Available tools |
| `mcp_client` | `MCPClient \| None` | MCP client |

**Example:**

```python
# Basic usage
agent = Agent(name="assistant", role="You are helpful")
result = await agent.run("Hello!")
print(result.output)

# With tools
result = await agent.run("Search for Python tutorials", max_tool_rounds=5)

# Streaming
async for chunk in agent.stream("Write a poem"):
    print(chunk.content, end="")
```

## StreamChunk

A chunk of streamed response data.

```python
from agentweave.core import StreamChunk

async for chunk in agent.stream("Hello"):
    if chunk.content:
        print(chunk.content, end="")
    if chunk.finish_reason:
        print(f"\nFinished: {chunk.finish_reason}")
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `content` | `str \| None` | Streamed content delta |
| `delta` | `str \| None` | Raw delta from provider |
| `finish_reason` | `str \| None` | Completion reason (stop, length, etc.) |
| `usage` | `Usage \| None` | Final token usage (at end of stream) |

## Workflow

Orchestrates multiple agents with sequential and parallel execution.

```python
from agentweave.core import Workflow, SequentialExecutor

agent1 = Agent(name="researcher", role="Research topics")
agent2 = Agent(name="writer", role="Write summaries")

executor = SequentialExecutor(["researcher", "writer"])
workflow = Workflow(
    agents={"researcher": agent1, "writer": agent2},
    executor=executor,
    merge_strategy="concat_newline"
)

result = await workflow.run("Write about Python")
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agents` | `dict[str, Agent]` | Required | Named agents to orchestrate |
| `executor` | `BaseExecutor` | `SequentialExecutor` | Execution strategy |
| `merge_strategy` | `MergeStrategy` | CONCAT_NEWLINE | Result merging strategy |

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `run` | `async run(input: str) -> WorkflowResult` | `WorkflowResult` | Execute workflow |
| `run_sync` | `run_sync(input: str) -> WorkflowResult` | `WorkflowResult` | Sync wrapper |
| `add_agent` | `add_agent(name: str, agent: Agent) -> None` | `None` | Add agent to workflow |
| `set_executor` | `set_executor(executor: BaseExecutor) -> None` | `None` | Change executor strategy |

**Example:**

```python
# Sequential execution: researcher -> writer
workflow = Workflow(
    agents={"researcher": r_agent, "writer": w_agent},
    executor=SequentialExecutor(["researcher", "writer"])
)
result = await workflow.run("Topic: Machine Learning")

# Parallel execution: researcher and writer run together
from agentweave.core import ParallelExecutor
executor = ParallelExecutor(["researcher", "writer"])
workflow = Workflow(agents={...}, executor=executor)
result = await workflow.run("Topic: Machine Learning")
```

## WorkflowResult

Result of a workflow execution.

```python
from agentweave.core import WorkflowStatus

result = await workflow.run("Input")
print(result.output)           # Final output
print(result.status)           # COMPLETED, FAILED, etc.
print(result.total_cost)       # Sum of all agent costs
print(result.total_tokens)     # Sum of all tokens
print(result.agent_results)    # Results per agent
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `output` | `str` | Final merged output |
| `state` | `WorkflowState` | Internal execution state |
| `status` | `WorkflowStatus` | Execution status |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `total_cost` | `float` | Sum of all agent costs |
| `total_tokens` | `int` | Sum of all tokens used |
| `total_duration_ms` | `int` | Total execution time |
| `agent_results` | `dict[str, AgentResult]` | Results by agent name |
| `usage` | `Usage` | Aggregated token usage |
| `is_success` | `bool` | True if workflow completed successfully |
| `error` | `str \| None` | Error message if failed |

## WorkflowStatus

Enum for workflow execution status.

```python
from agentweave.core import WorkflowStatus

if result.status == WorkflowStatus.COMPLETED:
    print("Success!")
elif result.status == WorkflowStatus.FAILED:
    print(f"Failed: {result.error}")
```

**Values:**

| Value | Description |
|-------|-------------|
| `PENDING` | Workflow not started |
| `RUNNING` | Workflow in progress |
| `COMPLETED` | Workflow finished successfully |
| `FAILED` | Workflow failed with error |
| `CANCELLED` | Workflow was cancelled |

## Executors

Execution strategies for workflows.

### SequentialExecutor

Runs agents one after another. Output of one agent becomes input to next.

```python
from agentweave.core import SequentialExecutor

executor = SequentialExecutor(["agent1", "agent2", "agent3"])
```

**Constructor Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `agent_names` | `list[str]` | Agents in execution order |

### ParallelExecutor

Runs agents concurrently. All agents receive same input.

```python
from agentweave.core import ParallelExecutor, MergeStrategy

executor = ParallelExecutor(
    ["agent1", "agent2"],
    merge_strategy=MergeStrategy.CONCAT_NEWLINE
)
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agent_names` | `list[str]` | Required | Agents to run in parallel |
| `merge_strategy` | `MergeStrategy` | CONCAT_NEWLINE | How to merge results |

### CompositeExecutor

Chains multiple executors together.

```python
from agentweave.core import CompositeExecutor, SequentialExecutor, ParallelExecutor

steps = [
    SequentialExecutor(["researcher"]),
    ParallelExecutor(["analyzer", "summarizer"]),
    SequentialExecutor(["reviewer"])
]
executor = CompositeExecutor(steps)
```

**Constructor Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `steps` | `list[BaseExecutor]` | Executors to run in sequence |

## MergeStrategy

How to merge results from parallel execution.

```python
from agentweave.core import MergeStrategy

# Concatenate without separator
MergeStrategy.CONCAT

# Concatenate with newline
MergeStrategy.CONCAT_NEWLINE

# Use first result only
MergeStrategy.FIRST

# Use last result only
MergeStrategy.LAST
```

**Values:**

| Value | Description |
|-------|-------------|
| `CONCAT` | Join results with empty string |
| `CONCAT_NEWLINE` | Join results with newline |
| `FIRST` | Return first result |
| `LAST` | Return last result |

## MessageRole

Enum for message roles in conversations.

```python
from agentweave.core import MessageRole

role = MessageRole.USER      # User input
role = MessageRole.ASSISTANT # Agent response
role = MessageRole.SYSTEM    # System instruction
role = MessageRole.TOOL      # Tool response
```

**Values:**

| Value | Description |
|-------|-------------|
| `SYSTEM` | System instruction message |
| `USER` | User input message |
| `ASSISTANT` | Assistant response message |
| `TOOL` | Tool response message |
