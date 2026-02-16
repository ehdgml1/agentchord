# Tracking API Reference

Complete API reference for token usage and cost tracking systems.

## TokenUsage

Token usage statistics for a single LLM call.

```python
from agentweave.tracking import TokenUsage

usage = TokenUsage(prompt_tokens=100, completion_tokens=50)
print(usage.total_tokens)  # 150

# Add usage records
usage1 = TokenUsage(prompt_tokens=100, completion_tokens=50)
usage2 = TokenUsage(prompt_tokens=75, completion_tokens=25)
combined = usage1 + usage2
print(combined.total_tokens)  # 250
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

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `__add__` | `__add__(other: TokenUsage) -> TokenUsage` | `TokenUsage` | Add two usage records |

## CostEntry

A single cost tracking entry.

```python
from agentweave.tracking import CostEntry, TokenUsage
from datetime import datetime

entry = CostEntry(
    model="gpt-4o-mini",
    usage=TokenUsage(prompt_tokens=100, completion_tokens=50),
    cost_usd=0.0015,
    agent_name="researcher",
    metadata={"source": "api_call"}
)
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `timestamp` | `datetime` | now() | When the call was made |
| `model` | `str` | Required | Model used |
| `usage` | `TokenUsage` | Required | Token usage |
| `cost_usd` | `float` | Required | Cost in USD |
| `agent_name` | `str \| None` | None | Agent name if tracked |
| `request_id` | `str \| None` | None | Request identifier |
| `metadata` | `dict[str, Any]` | {} | Additional metadata |

## CostSummary

Aggregated cost summary.

```python
from agentweave.tracking import CostSummary, CostEntry

summary = CostSummary.from_entries(entries)
print(f"Total cost: ${summary.total_cost_usd:.4f}")
print(f"Total tokens: {summary.total_tokens}")
print(f"By model: {summary.by_model}")
print(f"By agent: {summary.by_agent}")
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `total_cost_usd` | `float` | Total cost in USD |
| `total_tokens` | `int` | Total tokens used |
| `prompt_tokens` | `int` | Total prompt tokens |
| `completion_tokens` | `int` | Total completion tokens |
| `request_count` | `int` | Number of requests |
| `by_model` | `dict[str, float]` | Cost breakdown by model |
| `by_agent` | `dict[str, float]` | Cost breakdown by agent |

**Class Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `from_entries` | `from_entries(entries: list[CostEntry]) -> CostSummary` | `CostSummary` | Create summary from entries |

## CostTracker

Thread-safe cost tracker for LLM API usage.

```python
from agentweave.tracking import CostTracker
from agentweave.core import Agent

# Create tracker with budget limit
tracker = CostTracker(
    budget_limit=10.0,
    warning_threshold=0.8,
    raise_on_exceed=True
)

# Use with agent
agent = Agent(
    name="assistant",
    role="You are helpful",
    cost_tracker=tracker
)

result = await agent.run("Hello")

# Check costs
print(f"Total cost: ${tracker.total_cost:.4f}")
print(f"Remaining: ${tracker.remaining_budget:.4f}")
print(f"Summary: {tracker.get_summary()}")
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `budget_limit` | `float \| None` | None | Maximum budget in USD (None = unlimited) |
| `on_budget_warning` | `Callable[[CostSummary, float], None] \| None` | None | Callback when warning threshold reached |
| `warning_threshold` | `float` | 0.8 | Fraction of budget to trigger warning (0-1) |
| `on_budget_exceeded` | `Callable[[CostSummary], None] \| None` | None | Callback when budget exceeded |
| `raise_on_exceed` | `bool` | False | Raise exception when budget exceeded |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `budget_limit` | `float \| None` | Configured budget limit |
| `is_over_budget` | `bool` | True if budget exceeded |
| `total_cost` | `float` | Total cost in USD |
| `remaining_budget` | `float \| None` | Remaining budget (None if unlimited) |

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `track_usage` | `track_usage(model: str, usage: Usage, agent_name: str \| None = None) -> None` | `None` | Track token usage |
| `get_summary` | `get_summary() -> CostSummary` | `CostSummary` | Get cost summary |
| `get_entries` | `get_entries() -> list[CostEntry]` | `list[CostEntry]` | Get all entries |
| `get_entries_by_agent` | `get_entries_by_agent(name: str) -> list[CostEntry]` | `list[CostEntry]` | Get entries for agent |
| `reset` | `reset() -> None` | `None` | Clear all entries |

**Example: Budget Management**

```python
from agentweave.tracking import CostTracker, CostSummary

def on_warning(summary: CostSummary, remaining: float):
    print(f"Warning: 80% of budget used!")
    print(f"Remaining: ${remaining:.2f}")

def on_exceeded(summary: CostSummary):
    print(f"Error: Budget exceeded!")
    print(f"Total cost: ${summary.total_cost_usd:.2f}")

tracker = CostTracker(
    budget_limit=5.0,
    warning_threshold=0.8,
    on_budget_warning=on_warning,
    on_budget_exceeded=on_exceeded,
    raise_on_exceed=True
)

# Agent uses tracker
agent = Agent(
    name="assistant",
    role="You help users",
    cost_tracker=tracker
)

try:
    result = await agent.run("Generate a long response")
except Exception as e:
    print(f"Budget exceeded: {e}")
```

## CallbackEvent

Events that can trigger callbacks.

```python
from agentweave.tracking import CallbackEvent

# Agent lifecycle events
event = CallbackEvent.AGENT_START
event = CallbackEvent.AGENT_END
event = CallbackEvent.AGENT_ERROR

# LLM interaction events
event = CallbackEvent.LLM_START
event = CallbackEvent.LLM_END
event = CallbackEvent.LLM_ERROR

# Tool usage events
event = CallbackEvent.TOOL_START
event = CallbackEvent.TOOL_END
event = CallbackEvent.TOOL_ERROR

# Workflow events
event = CallbackEvent.WORKFLOW_START
event = CallbackEvent.WORKFLOW_END
event = CallbackEvent.WORKFLOW_STEP

# Memory events
event = CallbackEvent.MEMORY_ADD
event = CallbackEvent.MEMORY_SEARCH

# Cost events
event = CallbackEvent.COST_TRACKED
event = CallbackEvent.BUDGET_WARNING
event = CallbackEvent.BUDGET_EXCEEDED
```

**Values:**

| Value | Description |
|-------|-------------|
| `AGENT_START` | Agent execution started |
| `AGENT_END` | Agent execution completed |
| `AGENT_ERROR` | Agent execution failed |
| `LLM_START` | LLM request started |
| `LLM_END` | LLM request completed |
| `LLM_ERROR` | LLM request failed |
| `TOOL_START` | Tool execution started |
| `TOOL_END` | Tool execution completed |
| `TOOL_ERROR` | Tool execution failed |
| `WORKFLOW_START` | Workflow started |
| `WORKFLOW_END` | Workflow completed |
| `WORKFLOW_STEP` | Workflow step completed |
| `MEMORY_ADD` | Memory entry added |
| `MEMORY_SEARCH` | Memory search performed |
| `COST_TRACKED` | Cost entry tracked |
| `BUDGET_WARNING` | Budget warning threshold reached |
| `BUDGET_EXCEEDED` | Budget exceeded |

## CallbackContext

Context passed to callback handlers.

```python
from agentweave.tracking import CallbackContext, CallbackEvent
from datetime import datetime

context = CallbackContext(
    event=CallbackEvent.AGENT_END,
    timestamp=datetime.now(),
    agent_name="researcher",
    data={"output": "...", "cost": 0.015}
)
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `event` | `CallbackEvent` | Event type |
| `timestamp` | `datetime` | When event occurred |
| `agent_name` | `str \| None` | Agent name if applicable |
| `data` | `dict[str, Any]` | Event-specific data |

## CallbackManager

Manages callback registration and execution.

```python
from agentweave.tracking import CallbackManager, CallbackEvent

# Create manager
manager = CallbackManager()

# Register event callbacks
async def on_agent_end(context):
    print(f"Agent {context.agent_name} finished")

def on_cost_tracked(context):
    cost = context.data.get("cost_usd")
    print(f"Cost: ${cost:.4f}")

manager.register(CallbackEvent.AGENT_END, on_agent_end)
manager.register(CallbackEvent.COST_TRACKED, on_cost_tracked)

# Emit events
await manager.emit(CallbackEvent.AGENT_END, agent_name="assistant")
```

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `register_global` | `register_global(callback: Callable) -> None` | `None` | Register callback for all events |
| `register` | `register(event: CallbackEvent, callback: Callable) -> None` | `None` | Register callback for specific event |
| `emit` | `async emit(event: CallbackEvent, **data) -> None` | `None` | Emit event and trigger callbacks |

**Example: Cost Tracking Callbacks**

```python
from agentweave.tracking import CallbackManager, CallbackEvent, CostTracker
from agentweave.core import Agent

tracker = CostTracker(budget_limit=10.0)
callbacks = CallbackManager()

# Track cost events
def on_cost_tracked(context):
    cost = context.data.get("cost_usd", 0)
    total = tracker.total_cost
    print(f"Cost: ${cost:.4f}, Total: ${total:.4f}")

callbacks.register(CallbackEvent.COST_TRACKED, on_cost_tracked)

# Create agent with callbacks and tracker
agent = Agent(
    name="assistant",
    role="You help users",
    cost_tracker=tracker,
    callbacks=callbacks
)

# Callbacks fired during execution
result = await agent.run("Hello")
```

## Complete Example: Cost Monitoring

```python
from agentweave.tracking import CostTracker, CallbackEvent, CallbackManager
from agentweave.core import Agent, Workflow, SequentialExecutor

# Setup tracking
tracker = CostTracker(budget_limit=5.0)
callbacks = CallbackManager()

# Track each agent's cost
def log_agent_cost(context):
    agent = context.agent_name
    print(f"{agent}: ${context.data.get('cost', 0):.4f}")

callbacks.register(CallbackEvent.AGENT_END, log_agent_cost)

# Create agents
researcher = Agent(
    name="researcher",
    role="Research topics",
    cost_tracker=tracker,
    callbacks=callbacks
)

writer = Agent(
    name="writer",
    role="Write summaries",
    cost_tracker=tracker,
    callbacks=callbacks
)

# Create workflow
executor = SequentialExecutor(["researcher", "writer"])
workflow = Workflow(
    agents={"researcher": researcher, "writer": writer},
    executor=executor
)

# Run and track costs
result = await workflow.run("Topic: AI")

# Print summary
summary = tracker.get_summary()
print(f"\nTotal cost: ${summary.total_cost_usd:.4f}")
print(f"By model: {summary.by_model}")
print(f"By agent: {summary.by_agent}")
```

## Best Practices

1. **Set Budget Limits**: Prevent runaway costs

```python
tracker = CostTracker(budget_limit=100.0)
```

2. **Enable Warnings**: Get notified before budget is exceeded

```python
tracker = CostTracker(
    budget_limit=100.0,
    warning_threshold=0.8
)
```

3. **Monitor Per-Agent Costs**: Track spending by agent

```python
summary = tracker.get_summary()
for agent, cost in summary.by_agent.items():
    print(f"{agent}: ${cost:.4f}")
```

4. **Use Callbacks**: Observe events in real-time

```python
callbacks = CallbackManager()
callbacks.register(CallbackEvent.COST_TRACKED, on_cost)
```

5. **Regular Audits**: Review cost trends

```python
summary = tracker.get_summary()
entries = tracker.get_entries()
# Analyze usage patterns
```

See [Example 08](../examples.md) for a complete tracking example.
