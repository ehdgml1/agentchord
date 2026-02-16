# Orchestration API Reference

Complete API reference for AgentWeave multi-agent orchestration: team coordination, agent-to-agent messaging, shared state, and orchestration strategies.

## Types

### AgentMessage

A structured message exchanged between agents.

```python
from agentweave.orchestration import AgentMessage, MessageType

msg = AgentMessage(
    sender="researcher",
    recipient="writer",
    message_type=MessageType.TASK,
    content="Analyze this dataset",
    metadata={"priority": "high"},
    parent_id=None,
)
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique message ID (auto-generated UUID) |
| `sender` | `str` | Agent name sending the message |
| `recipient` | `str \| None` | Agent name to receive (None = broadcast) |
| `message_type` | `MessageType` | Type of message (TASK, RESULT, QUERY, etc.) |
| `content` | `str` | Message content |
| `metadata` | `dict[str, Any]` | Arbitrary metadata |
| `parent_id` | `str \| None` | ID of parent message (for threading) |
| `timestamp` | `datetime` | UTC timestamp (auto-generated) |

### MessageType

Enum of message types.

| Value | Description |
|-------|-------------|
| `TASK` | Task assignment to another agent |
| `RESULT` | Task completion result |
| `QUERY` | Information request |
| `RESPONSE` | Answer to a query |
| `BROADCAST` | Announcement to all agents |
| `SYSTEM` | Orchestration control message |

### TeamMember

Descriptor of an agent's role in a team.

```python
from agentweave.orchestration import TeamMember, TeamRole

member = TeamMember(
    name="data-analyst",
    role=TeamRole.SPECIALIST,
    capabilities=["data_analysis", "visualization"],
    agent_config={"temperature": 0.2},
)
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Agent name (must match Agent.name) |
| `role` | `TeamRole` | Agent's role in the team |
| `capabilities` | `list[str]` | List of agent capabilities |
| `agent_config` | `dict[str, Any]` | Configuration for agent initialization |

### TeamRole

Enum of agent roles.

| Value | Description |
|-------|-------------|
| `COORDINATOR` | Orchestrates task delegation |
| `WORKER` | Executes assigned tasks |
| `REVIEWER` | Validates outputs |
| `SPECIALIST` | Domain-specific expertise |

### OrchestrationStrategy

Enum of orchestration strategies.

| Value | Description |
|-------|-------------|
| `COORDINATOR` | Central coordinator delegates via tools |
| `ROUND_ROBIN` | Sequential turn-taking |
| `DEBATE` | Parallel viewpoints + synthesis |
| `MAP_REDUCE` | Parallel decomposition + aggregation |
| `SEQUENTIAL` | Alias for ROUND_ROBIN |

### TeamEvent

Event emitted during team streaming execution.

```python
from agentweave.orchestration import TeamEvent

event = TeamEvent(
    type="agent_result",
    sender="researcher",
    content="Research complete",
    round=1,
    metadata={"tokens": 500, "cost": 0.01},
)
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `type` | `str` | Event type (team_start, agent_message, agent_result, team_complete) |
| `sender` | `str \| None` | Agent emitting the event |
| `recipient` | `str \| None` | Target agent (for messages) |
| `content` | `str` | Event content |
| `round` | `int` | Current orchestration round |
| `timestamp` | `datetime` | UTC timestamp (auto-generated) |
| `metadata` | `dict[str, Any]` | Additional event data |

### AgentOutput

Output from a single agent within team execution.

```python
from agentweave.orchestration import AgentOutput, TeamRole

output = AgentOutput(
    agent_name="researcher",
    role=TeamRole.SPECIALIST,
    output="Research findings...",
    tokens=1500,
    cost=0.03,
    duration_ms=2500,
)
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `agent_name` | `str` | Name of the agent |
| `role` | `TeamRole` | Agent's role in team |
| `output` | `str` | Agent's output text |
| `tokens` | `int` | Total tokens used |
| `cost` | `float` | Total cost in USD |
| `duration_ms` | `int` | Execution duration in milliseconds |

### TeamResult

Aggregated result from team execution.

```python
from agentweave.orchestration import TeamResult

result = TeamResult(
    output="Final synthesized output",
    agent_outputs={
        "researcher": AgentOutput(...),
        "writer": AgentOutput(...),
    },
    messages=[msg1, msg2, msg3],
    total_cost=0.15,
    total_tokens=5000,
    rounds=3,
    duration_ms=8000,
    strategy="coordinator",
    team_name="content-team",
)
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `output` | `str` | Final synthesized output |
| `agent_outputs` | `dict[str, AgentOutput]` | Per-agent outputs (keyed by agent name) |
| `messages` | `list[AgentMessage]` | All messages exchanged |
| `total_cost` | `float` | Total cost across all agents (USD) |
| `total_tokens` | `int` | Total tokens across all agents |
| `rounds` | `int` | Number of orchestration rounds executed |
| `duration_ms` | `int` | Total execution time (milliseconds) |
| `strategy` | `str` | Strategy used |
| `team_name` | `str` | Name of the team |

## AgentTeam

Orchestrates multiple agents using configurable strategies.

```python
from agentweave import Agent, AgentTeam

researcher = Agent(name="researcher", role="Research expert", model="gpt-4o-mini")
writer = Agent(name="writer", role="Content writer", model="gpt-4o-mini")

team = AgentTeam(
    name="content-team",
    members=[researcher, writer],
    strategy="coordinator",
    max_rounds=10,
)

result = await team.run("Write a blog post about AI")
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | Required | Unique team name |
| `members` | `list[Agent \| TeamMember]` | Required | Team members (Agent instances or TeamMember descriptors) |
| `coordinator` | `Agent \| None` | None | Optional dedicated coordinator agent |
| `strategy` | `str \| OrchestrationStrategy` | "coordinator" | Orchestration strategy |
| `shared_context` | `SharedContext \| None` | None | Shared state (auto-created if None) |
| `message_bus` | `MessageBus \| None` | None | Message bus (auto-created if None) |
| `max_rounds` | `int` | 10 | Maximum orchestration rounds |
| `callbacks` | `CallbackManager \| None` | None | Callback manager for events |

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `run` | `async run(task: str) -> TeamResult` | `TeamResult` | Execute team on task |
| `stream` | `async stream(task: str) -> AsyncIterator[TeamEvent]` | `AsyncIterator[TeamEvent]` | Stream execution events |
| `run_sync` | `run_sync(task: str) -> TeamResult` | `TeamResult` | Synchronous wrapper for run() |
| `close` | `async close() -> None` | `None` | Release resources (idempotent) |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `members` | `list[TeamMember]` | List of team members |
| `agents` | `dict[str, Agent]` | Dictionary of agent name to Agent instance |
| `strategy` | `str` | Current strategy name |
| `shared_context` | `SharedContext` | Team's shared context |
| `message_bus` | `MessageBus` | Team's message bus |

**Example:**

```python
# Basic usage
async with AgentTeam(name="team", members=[agent1, agent2], strategy="round_robin") as team:
    result = await team.run("Analyze competitor landscape")
    print(result.output)
    print(f"Cost: ${result.total_cost:.4f}")
    print(f"Rounds: {result.rounds}")

# Streaming
async for event in team.stream("Research AI trends"):
    if event.type == "agent_result":
        print(f"[{event.sender}] {event.content[:100]}...")

# Agent breakdown
for name, output in result.agent_outputs.items():
    print(f"{name}: ${output.cost:.4f} ({output.tokens:,} tokens)")
```

## MessageBus

Async pub/sub message routing between agents.

```python
from agentweave.orchestration import MessageBus, AgentMessage, MessageType

bus = MessageBus()
bus.register("agent-1")
bus.register("agent-2")

# Send message
msg = AgentMessage(
    sender="agent-1",
    recipient="agent-2",
    message_type=MessageType.TASK,
    content="Process this data",
)
await bus.send(msg)

# Receive message
received = await bus.receive("agent-2", timeout=10.0)
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `callbacks` | `CallbackManager \| None` | None | Optional callback manager for message events |

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `register` | `register(agent_name: str) -> None` | `None` | Register agent to receive messages |
| `unregister` | `unregister(agent_name: str) -> None` | `None` | Unregister agent |
| `send` | `async send(message: AgentMessage) -> None` | `None` | Send message to recipient or broadcast |
| `receive` | `async receive(agent_name: str, timeout: float \| None = None) -> AgentMessage \| None` | `AgentMessage \| None` | Receive next message (default timeout 30s) |
| `broadcast` | `async broadcast(sender: str, content: str, metadata: dict \| None = None) -> AgentMessage` | `AgentMessage` | Broadcast message to all agents (except sender) |
| `get_history` | `get_history() -> list[AgentMessage]` | `list[AgentMessage]` | Return all messages in chronological order |
| `get_agent_messages` | `get_agent_messages(agent_name: str) -> list[AgentMessage]` | `list[AgentMessage]` | Return messages sent by or to a specific agent |
| `pending_count` | `pending_count(agent_name: str) -> int` | `int` | Number of unread messages for agent |
| `clear` | `clear() -> None` | `None` | Clear all history and queues |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `registered_agents` | `list[str]` | List of registered agent names |
| `message_count` | `int` | Total number of messages sent |

**Example:**

```python
bus = MessageBus()
bus.register("coordinator")
bus.register("worker-1")
bus.register("worker-2")

# Directed message
await bus.send(AgentMessage(
    sender="coordinator",
    recipient="worker-1",
    message_type=MessageType.TASK,
    content="Analyze dataset A",
))

# Broadcast
await bus.broadcast(sender="coordinator", content="Priority changed to HIGH")

# Receive with timeout
msg = await bus.receive("worker-1", timeout=5.0)
if msg:
    print(f"Received: {msg.content}")

# Check pending
if bus.pending_count("worker-2") > 0:
    pending_msg = await bus.receive("worker-2")

# View history
history = bus.get_history()
worker1_msgs = bus.get_agent_messages("worker-1")
```

## SharedContext

Thread-safe shared state for concurrent agent collaboration.

```python
from agentweave.orchestration import SharedContext

ctx = SharedContext(initial={"project": "AgentWeave"})

# Thread-safe operations
await ctx.set("status", "in_progress", agent="coordinator")
status = await ctx.get("status")
await ctx.update({"version": 2, "last_updated": "2025-01-15"}, agent="system")
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `initial` | `dict[str, Any] \| None` | None | Initial context data |

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `get` | `async get(key: str, default: Any = None) -> Any` | `Any` | Get value (returns deep copy for dicts/lists) |
| `set` | `async set(key: str, value: Any, agent: str = "") -> None` | `None` | Set value and record update |
| `update` | `async update(data: dict[str, Any], agent: str = "") -> None` | `None` | Update multiple keys atomically |
| `delete` | `async delete(key: str, agent: str = "") -> bool` | `bool` | Delete key (returns True if existed) |
| `has` | `async has(key: str) -> bool` | `bool` | Check if key exists |
| `keys` | `async keys() -> list[str]` | `list[str]` | Get all keys |
| `snapshot` | `snapshot() -> dict[str, Any]` | `dict[str, Any]` | Return deep copy of current state (sync) |
| `get_history` | `get_history() -> list[ContextUpdate]` | `list[ContextUpdate]` | Return all updates in chronological order |
| `get_agent_updates` | `get_agent_updates(agent: str) -> list[ContextUpdate]` | `list[ContextUpdate]` | Return updates made by specific agent |
| `clear` | `clear() -> None` | `None` | Clear all data and history |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `size` | `int` | Number of keys in context |
| `update_count` | `int` | Total number of updates made |

**Example:**

```python
ctx = SharedContext(initial={"task": "research"})

# Set values
await ctx.set("findings", research_data, agent="researcher")
await ctx.set("summary", summary_text, agent="writer")

# Bulk update
await ctx.update({
    "status": "review",
    "version": 2,
}, agent="coordinator")

# Get values (deep copy returned)
findings = await ctx.get("findings", default={})

# Check existence
if await ctx.has("summary"):
    keys = await ctx.keys()

# Delete
existed = await ctx.delete("temporary_data", agent="cleanup")

# Snapshot
snapshot = ctx.snapshot()  # Safe to modify

# History
history = ctx.get_history()
for update in history:
    print(f"{update.agent}: {update.operation} {update.key} at {update.timestamp}")

researcher_updates = ctx.get_agent_updates("researcher")

# Metrics
print(f"Keys: {ctx.size}")
print(f"Updates: {ctx.update_count}")
```

## ContextUpdate

Record of a SharedContext modification.

```python
from agentweave.orchestration import ContextUpdate

update = ContextUpdate(
    key="status",
    value="complete",
    agent="coordinator",
    operation="set",
)
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `key` | `str` | Context key modified |
| `value` | `Any` | New value (None for delete operations) |
| `agent` | `str` | Agent name that made the update |
| `timestamp` | `datetime` | UTC timestamp (auto-generated) |
| `operation` | `str` | Operation type ("set" or "delete") |

## Orchestration Strategies

### BaseStrategy

Abstract base class for orchestration strategies.

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `execute` | `async execute(task, agents, coordinator, members, message_bus, shared_context, max_rounds, callbacks) -> TeamResult` | `TeamResult` | Execute orchestration strategy |

### CoordinatorStrategy

Central coordinator delegates subtasks to specialists via tool calling.

**Behavior:**
1. Coordinator receives delegation tools for each worker
2. Coordinator analyzes task and delegates via tool calls
3. Workers execute delegated subtasks
4. Coordinator synthesizes results

### RoundRobinStrategy

Agents process task sequentially in turn.

**Behavior:**
1. First agent receives original task
2. Each subsequent agent receives previous agent's output as input
3. Final agent's output becomes team result

### DebateStrategy

Agents present independent viewpoints, then synthesize consensus.

**Behavior:**
1. All agents analyze task independently (parallel execution)
2. Each agent presents their perspective
3. Perspectives are synthesized into balanced conclusion

### MapReduceStrategy

Parallel task decomposition followed by result aggregation.

**Behavior:**
1. Task is divided into independent subtasks
2. Workers process subtasks in parallel (map phase)
3. Results are aggregated into final output (reduce phase)

## Helper Functions

### create_delegation_tools

Create tool functions for coordinator to delegate to specialists.

```python
from agentweave.orchestration.tools import create_delegation_tools

tools = create_delegation_tools(
    agents={"analyst": data_analyst, "writer": report_writer}
)

coordinator = Agent(
    name="coordinator",
    role="Task orchestrator",
    model="gpt-4o",
    tools=tools,  # Can now delegate via tool calls
)
```

**Function Signature:**

```python
def create_delegation_tools(agents: dict[str, Agent]) -> list[Tool]:
    ...
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `agents` | `dict[str, Agent]` | Dictionary of agent name to Agent instance |

**Returns:**

List of `Tool` instances, one per agent. Each tool:
- **Name**: `delegate_to_{agent_name}`
- **Description**: `Delegate a subtask to {agent_name} ({agent.role})`
- **Parameters**: `subtask: str` - The subtask to delegate

### create_context_tools

Create tool functions for agents to access shared context.

```python
from agentweave.orchestration.tools import create_context_tools

ctx = SharedContext()
tools = create_context_tools(ctx)

agent = Agent(
    name="worker",
    role="Worker with context access",
    model="gpt-4o-mini",
    tools=tools,  # Can read/write shared context
)
```

**Function Signature:**

```python
def create_context_tools(shared_context: SharedContext) -> list[Tool]:
    ...
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `shared_context` | `SharedContext` | Shared context instance |

**Returns:**

List of `Tool` instances:
- `get_context(key: str) -> Any`: Read from shared context
- `set_context(key: str, value: str) -> None`: Write to shared context
- `list_context_keys() -> list[str]`: List all context keys
