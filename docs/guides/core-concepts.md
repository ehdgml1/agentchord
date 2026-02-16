# Core Concepts

Understanding the fundamental building blocks of AgentWeave.

## Agent

The Agent is the fundamental unit of AgentWeave. It wraps an LLM with configuration, tools, memory, and more.

### Creating an Agent

```python
from agentweave import Agent

agent = Agent(
    name="researcher",              # Unique identifier
    role="Research specialist",     # Describes purpose (used in system prompt)
    model="gpt-4o-mini",           # LLM model (auto-detects provider)
    temperature=0.7,               # Creativity (0.0-2.0)
    max_tokens=4096,               # Max response length
    timeout=60.0,                  # Request timeout in seconds
    system_prompt=None,            # Custom system prompt (auto-generated if None)
)
```

### Optional Integrations

```python
agent = Agent(
    name="full",
    role="Fully configured agent",
    model="gpt-4o-mini",
    llm_provider=custom_provider,   # Override auto-detected provider
    memory=ConversationMemory(),    # Remember conversations
    cost_tracker=CostTracker(),     # Track token usage and costs
    resilience=ResilienceConfig(),  # Retry, circuit breaker, timeout
    tools=[my_tool],               # Callable tools
    callbacks=CallbackManager(),    # Event notifications
    mcp_client=mcp,                # MCP protocol client
)
```

### Execution

```python
# Async (preferred)
result = await agent.run("Hello!")

# Sync wrapper
result = agent.run_sync("Hello!")

# Streaming
async for chunk in agent.stream("Tell me a story"):
    print(chunk.delta, end="")
```

### AgentResult

Every `run()` call returns an `AgentResult`:

| Field | Type | Description |
|-------|------|-------------|
| `output` | str | Final text response |
| `messages` | list[Message] | Full conversation history |
| `usage` | Usage | Token counts (prompt + completion) |
| `cost` | float | Estimated cost in USD |
| `duration_ms` | int | Execution time in milliseconds |
| `metadata` | dict | Agent name, model, provider, tool_rounds |

```python
result = await agent.run("Hello!")
print(result.output)                          # "Hi there!"
print(result.usage.total_tokens)              # 150
print(result.cost)                            # 0.000225
print(result.metadata["agent_name"])          # "researcher"
print(result.metadata["tool_rounds"])         # 1
```

## Workflow

A Workflow orchestrates multiple Agents using a Flow DSL.

### Flow DSL Syntax

| Pattern | Syntax | Description |
|---------|--------|-------------|
| Sequential | `"A -> B -> C"` | Each agent receives previous output |
| Parallel | `"[A, B]"` | Agents run concurrently |
| Mixed | `"A -> [B, C] -> D"` | Combine both patterns |

```python
from agentweave import Agent, Workflow

researcher = Agent(name="researcher", role="Research", model="gpt-4o-mini")
writer = Agent(name="writer", role="Writing", model="gpt-4o-mini")

workflow = Workflow(
    agents=[researcher, writer],
    flow="researcher -> writer",
)

result = workflow.run_sync("Write about AI")
```

### Merge Strategies

When parallel agents finish, their outputs are merged:

| Strategy | Behavior |
|----------|----------|
| `CONCAT_NEWLINE` | Join with `\n\n` (default) |
| `CONCAT` | Join directly (no separator) |
| `FIRST` | Use first agent's output only |
| `LAST` | Use last agent's output only |

```python
from agentweave import Workflow, MergeStrategy

workflow = Workflow(
    agents=[a, b, c],
    flow="[a, b] -> c",
    merge_strategy=MergeStrategy.FIRST,
)
```

### WorkflowResult

| Property | Type | Description |
|----------|------|-------------|
| `output` | str | Final output |
| `status` | WorkflowStatus | COMPLETED, FAILED, etc. |
| `is_success` | bool | True if COMPLETED |
| `error` | str or None | Error message if FAILED |
| `total_cost` | float | Sum of all agent costs |
| `total_tokens` | int | Sum of all agent tokens |
| `total_duration_ms` | int | Total execution time |
| `agent_results` | list[AgentResult] | Individual agent results |
| `usage` | Usage | Aggregated token usage |

## WorkflowState

Immutable state that flows between workflow steps.

```python
state = WorkflowState(input="Analyze this data")

# State fields
state.input           # Original input
state.output          # Current output (updated by agents)
state.history         # list[AgentResult] - all agent executions
state.context         # dict - shared data between agents
state.effective_input # output if available, else input
```

State is immutable - methods return new copies:

```python
state = state.with_output("Analysis complete")
state = state.with_context("key", "value")
state = state.with_status(WorkflowStatus.COMPLETED)
```

## Provider Registry

AgentWeave auto-detects LLM providers from model name prefixes:

| Prefix | Provider | API Key Env Var |
|--------|----------|-----------------|
| `gpt-`, `o1-` | OpenAI | `OPENAI_API_KEY` |
| `claude-` | Anthropic | `ANTHROPIC_API_KEY` |
| `gemini-` | Google Gemini | `GOOGLE_API_KEY` |
| `ollama/` | Ollama (local) | None |

```python
# Auto-detected from model name
agent1 = Agent(name="a", role="R", model="gpt-4o")           # → OpenAI
agent2 = Agent(name="b", role="R", model="claude-3-5-sonnet") # → Anthropic
agent3 = Agent(name="c", role="R", model="gemini-2.0-flash")  # → Gemini
agent4 = Agent(name="d", role="R", model="ollama/llama3.2")   # → Ollama
```

### Custom Providers

```python
from agentweave import get_registry

registry = get_registry()
registry.register("custom", my_factory, ["custom-"])

# Now "custom-v1" auto-routes to your provider
agent = Agent(name="a", role="R", model="custom-v1")
```

## Messages and Types

### Message

```python
from agentweave import Message, MessageRole

# Roles: SYSTEM, USER, ASSISTANT, TOOL
msg = Message(role=MessageRole.USER, content="Hello")
```

### Usage

```python
from agentweave import Usage

usage = Usage(prompt_tokens=100, completion_tokens=50)
print(usage.total_tokens)  # 150
```

### ToolCall

```python
from agentweave import ToolCall

tc = ToolCall(id="call_123", name="calculator", arguments={"expr": "2+2"})
```

### StreamChunk

```python
from agentweave import StreamChunk

# Yielded during agent.stream()
# chunk.content  - accumulated text so far
# chunk.delta    - new text in this chunk
# chunk.finish_reason - "stop" on last chunk
# chunk.usage    - token counts on last chunk
```

## Putting It All Together

```python
from agentweave import Agent, Workflow, ConversationMemory, CostTracker, tool

@tool(description="Search the web")
def search(query: str) -> str:
    return f"Results for: {query}"

tracker = CostTracker()

researcher = Agent(
    name="researcher",
    role="Research with web search",
    model="gpt-4o-mini",
    tools=[search],
    cost_tracker=tracker,
)

writer = Agent(
    name="writer",
    role="Write articles from research",
    model="gpt-4o-mini",
    cost_tracker=tracker,
)

workflow = Workflow(
    agents=[researcher, writer],
    flow="researcher -> writer",
)

result = workflow.run_sync("Write about quantum computing")
print(result.output)
print(f"Total cost: ${tracker.get_summary().total_cost:.4f}")
```
