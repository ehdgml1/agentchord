# Multi-Agent Orchestration Guide

AgentWeave's orchestration system enables multiple agents to collaborate on complex tasks through structured coordination strategies. Unlike single-agent workflows, multi-agent orchestration introduces agent-to-agent communication, role specialization, and emergent problem-solving patterns.

## Quick Start

Basic multi-agent team with coordinator strategy:

```python
from agentweave import Agent, AgentTeam

# Define specialized agents
researcher = Agent(
    name="researcher",
    role="Research expert who gathers and analyzes information",
    model="gpt-4o-mini",
)
writer = Agent(
    name="writer",
    role="Content writer who creates engaging text",
    model="gpt-4o-mini",
)

# Create coordinated team
team = AgentTeam(
    name="content-team",
    members=[researcher, writer],
    strategy="coordinator",
    max_rounds=5,
)

# Execute task
result = await team.run("Write a blog post about AI safety")
print(result.output)  # Final synthesized output
print(f"Cost: ${result.total_cost:.4f}")
print(f"Rounds: {result.rounds}")
```

## Core Concepts

### AgentTeam

`AgentTeam` is the orchestration container that manages multiple agents working together. It provides:

- **Strategy selection**: Choose how agents coordinate (coordinator, round robin, debate, map-reduce)
- **Message routing**: Structured agent-to-agent communication via `MessageBus`
- **Shared state**: Thread-safe `SharedContext` for cross-agent data sharing
- **Cost aggregation**: Automatic token and cost tracking across all agents
- **Lifecycle management**: Async context manager for resource cleanup

```python
team = AgentTeam(
    name="research-team",
    members=[agent1, agent2, agent3],
    strategy="coordinator",
    max_rounds=10,
)

async with team:
    result = await team.run("Analyze market trends")
```

### TeamMember

Each agent in a team has a role that defines its specialization:

```python
from agentweave.orchestration import TeamMember, TeamRole

member = TeamMember(
    name="analyst",
    role=TeamRole.SPECIALIST,
    capabilities=["data_analysis", "visualization"],
    agent_config={"temperature": 0.2},
)
```

**Roles:**
- `COORDINATOR`: Orchestrates task delegation
- `WORKER`: Executes assigned tasks
- `REVIEWER`: Validates outputs
- `SPECIALIST`: Domain-specific expertise

### MessageBus

The `MessageBus` provides async pub/sub messaging between agents:

```python
from agentweave.orchestration import MessageBus, AgentMessage, MessageType

bus = MessageBus()
bus.register("agent-1")
bus.register("agent-2")

# Send directed message
msg = AgentMessage(
    sender="agent-1",
    recipient="agent-2",
    message_type=MessageType.TASK,
    content="Analyze this dataset",
)
await bus.send(msg)

# Receive message
received = await bus.receive("agent-2")

# Broadcast to all
await bus.broadcast(sender="coordinator", content="Task complete")

# View history
history = bus.get_history()
```

**Message Types:**
- `TASK`: Task assignment
- `RESULT`: Task completion
- `QUERY`: Information request
- `RESPONSE`: Answer to query
- `BROADCAST`: Announcement to all
- `SYSTEM`: Orchestration control

### SharedContext

Thread-safe shared state for concurrent agent access:

```python
from agentweave.orchestration import SharedContext

ctx = SharedContext(initial={"project": "AI Research"})

# Thread-safe writes
await ctx.set("findings", research_data, agent="researcher")
await ctx.update({"status": "in_progress", "version": 2}, agent="coordinator")

# Thread-safe reads (returns deep copy)
findings = await ctx.get("findings")

# Check existence
if await ctx.has("findings"):
    keys = await ctx.keys()

# View modification history
history = ctx.get_history()
for update in history:
    print(f"{update.agent} {update.operation} {update.key} at {update.timestamp}")
```

## Orchestration Strategies

AgentWeave provides four built-in strategies, each optimized for different collaboration patterns.

### Coordinator Strategy

**Pattern**: Central coordinator delegates subtasks to specialized workers.

**Best for**: Complex tasks requiring specialized expertise, hierarchical workflows.

**How it works**:
1. Coordinator agent analyzes the task
2. Delegates subtasks to appropriate specialists via tool calls
3. Aggregates results into final output

```python
from agentweave import Agent, AgentTeam

# Define coordinator with delegation tools
coordinator = Agent(
    name="coordinator",
    role="Task orchestrator who delegates to specialists",
    model="gpt-4o",
)

# Define specialists
data_analyst = Agent(
    name="analyst",
    role="Data analysis specialist",
    model="gpt-4o-mini",
)
report_writer = Agent(
    name="writer",
    role="Report writing specialist",
    model="gpt-4o-mini",
)

team = AgentTeam(
    name="analysis-team",
    members=[data_analyst, report_writer],
    coordinator=coordinator,
    strategy="coordinator",
    max_rounds=8,
)

result = await team.run("Analyze Q4 sales data and generate executive summary")
```

**Key innovation**: Delegation-as-tools pattern. The coordinator receives tool functions to invoke each specialist, enabling natural language delegation decisions.

### Round Robin Strategy

**Pattern**: Agents take turns processing the task sequentially.

**Best for**: Iterative refinement, assembly-line workflows, progressive enhancement.

**How it works**:
1. Task starts with first agent
2. Each agent receives previous agent's output as input
3. Final agent produces synthesis

```python
team = AgentTeam(
    name="refinement-team",
    members=[drafter, editor, reviewer],
    strategy="round_robin",
    max_rounds=3,
)

result = await team.run("Write a product announcement")
# drafter → editor → reviewer → final output
```

**Rounds**: Each complete cycle through all agents counts as one round. With `max_rounds=3` and 3 agents, each agent runs exactly once.

### Debate Strategy

**Pattern**: Agents present opposing viewpoints and synthesize consensus.

**Best for**: Decision analysis, risk assessment, creative brainstorming with diverse perspectives.

**How it works**:
1. Each agent independently analyzes the task
2. Agents present their viewpoints simultaneously
3. Viewpoints are synthesized into balanced conclusion

```python
optimist = Agent(
    name="optimist",
    role="Identifies opportunities and benefits",
    model="gpt-4o-mini",
)
skeptic = Agent(
    name="skeptic",
    role="Identifies risks and challenges",
    model="gpt-4o-mini",
)

team = AgentTeam(
    name="decision-analysis",
    members=[optimist, skeptic],
    strategy="debate",
    max_rounds=2,
)

result = await team.run("Should we adopt blockchain for supply chain tracking?")
```

**Rounds**: Each round consists of one contribution from each debater. With `max_rounds=2`, you get 2 exchanges before synthesis.

### Map-Reduce Strategy

**Pattern**: Parallel task decomposition (map) followed by result aggregation (reduce).

**Best for**: Data processing, parallel analysis, divide-and-conquer problems.

**How it works**:
1. Task is divided into independent subtasks
2. Workers process subtasks in parallel (map phase)
3. Results are aggregated into final output (reduce phase)

```python
workers = [
    Agent(name=f"worker-{i}", role=f"Processor {i}", model="gpt-4o-mini")
    for i in range(4)
]

team = AgentTeam(
    name="data-processors",
    members=workers,
    strategy="map_reduce",
    max_rounds=1,
)

result = await team.run("Summarize these 1000 customer reviews")
# Each worker gets ~250 reviews, processes in parallel, results merged
```

**Performance**: Map phase runs in parallel, dramatically reducing wall-clock time for independent subtasks.

## Strategy Comparison

| Strategy | Communication Pattern | Parallelization | Best Use Case |
|----------|----------------------|-----------------|---------------|
| **Coordinator** | Hub-and-spoke (tools) | Workers run sequentially via coordinator | Complex hierarchical tasks requiring expertise routing |
| **Round Robin** | Sequential pipeline | None (linear chain) | Iterative refinement, editorial workflows |
| **Debate** | Peer-to-peer | Agents run in parallel | Decision analysis, multi-perspective synthesis |
| **Map-Reduce** | Scatter-gather | Map phase fully parallel | Data processing, divide-and-conquer problems |

## Delegation-as-Tools Pattern

The coordinator strategy implements delegation via **tool calling**, a key innovation that enables natural language-driven task routing.

**How it works:**

1. Coordinator agent receives a tool for each specialist:
   ```python
   def delegate_to_analyst(subtask: str) -> str:
       """Delegate data analysis subtask to analyst specialist."""
       return analyst.run_sync(subtask)
   ```

2. Coordinator decides when and how to delegate via LLM reasoning:
   ```
   User: "Analyze sales and write a report"
   Coordinator: I'll use delegate_to_analyst() to analyze the data,
                then delegate_to_writer() to create the report.
   ```

3. Tool execution routes subtasks to specialists automatically.

**Benefits:**
- No hardcoded routing logic
- Coordinator adapts delegation to task complexity
- Natural handling of dependencies (analyst before writer)
- Emergent multi-step workflows

**Example:**

```python
from agentweave.orchestration.tools import create_delegation_tools

# Create tools for coordinator
delegation_tools = create_delegation_tools(
    agents={"analyst": data_analyst, "writer": report_writer}
)

coordinator = Agent(
    name="coordinator",
    role="Orchestrator",
    model="gpt-4o",
    tools=delegation_tools,  # Coordinator can now delegate
)

team = AgentTeam(
    name="team",
    members=[data_analyst, report_writer],
    coordinator=coordinator,
    strategy="coordinator",
)
```

The coordinator automatically receives `delegate_to_analyst()` and `delegate_to_writer()` tools.

## Streaming Team Execution

Stream real-time updates as the team executes:

```python
async for event in team.stream("Analyze competitor landscape"):
    if event.type == "team_start":
        print(f"Starting: {event.content}")
    elif event.type == "agent_message":
        print(f"[{event.sender} → {event.recipient}] {event.content}")
    elif event.type == "agent_result":
        print(f"[{event.sender}] completed: {event.content[:100]}...")
    elif event.type == "team_complete":
        print(f"Final output: {event.content}")
        print(f"Cost: ${event.metadata['total_cost']:.4f}")
```

**Event Types:**
- `team_start`: Team execution begins
- `agent_message`: Agent-to-agent communication
- `agent_result`: Individual agent completes
- `team_complete`: Final result available

## Cost Tracking and Budgets

AgentTeam aggregates costs across all agent invocations:

```python
result = await team.run("Research AI safety")

print(f"Total cost: ${result.total_cost:.4f}")
print(f"Total tokens: {result.total_tokens:,}")
print(f"Agent breakdown:")
for name, output in result.agent_outputs.items():
    print(f"  {name}: ${output.cost:.4f} ({output.tokens:,} tokens)")
```

Set per-agent budgets:

```python
expensive_agent = Agent(
    name="gpt4-agent",
    role="Complex reasoning",
    model="gpt-4o",
    cost_config={"budget_limit": 1.00},  # Max $1 per invocation
)
```

## Message Bus Deep Dive

The `MessageBus` enables structured agent-to-agent communication.

### Registration

```python
bus = MessageBus()
bus.register("researcher")
bus.register("writer")
bus.register("reviewer")

# Check registration
print(bus.registered_agents)  # ["researcher", "writer", "reviewer"]
```

### Sending Messages

```python
# Directed message
msg = AgentMessage(
    sender="researcher",
    recipient="writer",
    message_type=MessageType.RESULT,
    content="Research findings: ...",
    metadata={"citations": ["source1", "source2"]},
)
await bus.send(msg)

# Broadcast (all agents except sender)
broadcast_msg = AgentMessage(
    sender="coordinator",
    recipient=None,
    message_type=MessageType.BROADCAST,
    content="Task priority changed to HIGH",
)
await bus.send(broadcast_msg)
```

### Receiving Messages

```python
# Block until message arrives (30s timeout default)
msg = await bus.receive("writer")

# Custom timeout
msg = await bus.receive("writer", timeout=10.0)

# Non-blocking check
if bus.pending_count("writer") > 0:
    msg = await bus.receive("writer", timeout=0.1)
```

### Message History

```python
# All messages
all_messages = bus.get_history()

# Messages for specific agent
writer_messages = bus.get_agent_messages("writer")
for msg in writer_messages:
    print(f"{msg.timestamp}: {msg.sender} → {msg.recipient}: {msg.content}")

# Total message count
print(f"Messages exchanged: {bus.message_count}")
```

## SharedContext Deep Dive

Thread-safe shared state for concurrent agent operations.

### Basic Operations

```python
ctx = SharedContext(initial={"project": "AgentWeave"})

# Set values
await ctx.set("status", "in_progress", agent="coordinator")
await ctx.set("findings", research_data, agent="researcher")

# Get values (returns deep copy to prevent mutation)
status = await ctx.get("status")
findings = await ctx.get("findings", default={})

# Check existence
if await ctx.has("findings"):
    keys = await ctx.keys()  # ["project", "status", "findings"]
```

### Bulk Updates

```python
# Atomic multi-key update
await ctx.update({
    "status": "review",
    "version": 2,
    "last_updated": datetime.now(UTC),
}, agent="coordinator")
```

### Deletion

```python
existed = await ctx.delete("temporary_data", agent="cleanup")
# Returns True if key existed, False otherwise
```

### Snapshots and History

```python
# Immutable snapshot of current state
snapshot = ctx.snapshot()  # dict copy, safe to modify

# Modification history
history = ctx.get_history()
for update in history:
    print(f"{update.agent}: {update.operation} {update.key} = {update.value}")

# Agent-specific history
researcher_updates = ctx.get_agent_updates("researcher")

# Metrics
print(f"Keys: {ctx.size}")
print(f"Updates: {ctx.update_count}")
```

### Concurrency Safety

`SharedContext` uses `asyncio.Lock` to prevent race conditions:

```python
# Safe concurrent writes
await asyncio.gather(
    ctx.set("metric_a", 100, agent="agent1"),
    ctx.set("metric_b", 200, agent="agent2"),
    ctx.set("metric_c", 300, agent="agent3"),
)

# Returns deep copies to prevent mutation
data = await ctx.get("large_dict")
data["new_key"] = "value"  # Does NOT mutate shared context
```

## Advanced Patterns

### Custom Coordinator Logic

Define a coordinator with specific delegation criteria:

```python
coordinator = Agent(
    name="coordinator",
    role="""You are a task coordinator. Analyze the user's request and delegate subtasks:
    - Use delegate_to_analyst() for data analysis tasks
    - Use delegate_to_writer() for content creation
    - Use delegate_to_reviewer() for quality checks

    Always delegate analysis BEFORE writing. Always review final outputs.""",
    model="gpt-4o",
    tools=delegation_tools,
)
```

### Hybrid Strategy Workflows

Combine strategies by nesting teams:

```python
# Inner team: Debate for analysis
analysis_team = AgentTeam(
    name="analysis",
    members=[optimist, skeptic],
    strategy="debate",
)

# Outer coordinator delegates to analysis team
coordinator_with_team = Agent(
    name="coordinator",
    role="Orchestrator",
    tools=[create_team_tool(analysis_team)],
)
```

### Dynamic Team Composition

Add/remove agents based on task requirements:

```python
from agentweave.orchestration import TeamMember, TeamRole

base_members = [researcher, writer]

# Add specialist if needed
if task_requires_legal_review:
    base_members.append(
        Agent(name="legal", role="Legal reviewer", model="gpt-4o")
    )

team = AgentTeam(name="team", members=base_members, strategy="coordinator")
```

### Message-Driven Workflows

Use MessageBus for custom coordination:

```python
# Agent 1 sends task
await bus.send(AgentMessage(
    sender="agent1",
    recipient="agent2",
    message_type=MessageType.TASK,
    content="Process this data",
    metadata={"data": data_batch},
))

# Agent 2 receives and responds
task_msg = await bus.receive("agent2")
result = agent2.run_sync(task_msg.content)

await bus.send(AgentMessage(
    sender="agent2",
    recipient="agent1",
    message_type=MessageType.RESULT,
    content=result.output,
    parent_id=task_msg.id,
))
```

## Best Practices

### 1. Choose the Right Strategy

```python
# Complex hierarchical tasks → Coordinator
team = AgentTeam(members=[...], strategy="coordinator")

# Iterative refinement → Round Robin
team = AgentTeam(members=[drafter, editor, proofreader], strategy="round_robin")

# Perspective diversity → Debate
team = AgentTeam(members=[optimist, skeptic], strategy="debate")

# Parallel data processing → Map-Reduce
team = AgentTeam(members=workers, strategy="map_reduce")
```

### 2. Limit Rounds for Cost Control

```python
# Prevent runaway costs
team = AgentTeam(
    name="team",
    members=[...],
    strategy="coordinator",
    max_rounds=5,  # Limit coordinator iterations
)
```

### 3. Use Lifecycle Management

```python
# Always use async context manager
async with AgentTeam(...) as team:
    result = await team.run(task)
# Automatic cleanup: clears message bus, releases resources
```

### 4. Monitor Message Patterns

```python
result = await team.run(task)

# Debug communication patterns
print(f"Messages exchanged: {len(result.messages)}")
for msg in result.messages:
    print(f"{msg.sender} → {msg.recipient}: {msg.message_type.value}")
```

### 5. Balance Model Costs

```python
# Expensive coordinator, cheap workers
coordinator = Agent(name="coord", model="gpt-4o")  # Smart routing
workers = [
    Agent(name=f"w{i}", model="gpt-4o-mini")  # Fast execution
    for i in range(3)
]

team = AgentTeam(
    members=workers,
    coordinator=coordinator,
    strategy="coordinator",
)
```

### 6. Validate Agent Outputs

```python
# Add reviewer agent to verify outputs
reviewer = Agent(
    name="reviewer",
    role="Validate outputs meet quality standards",
    model="gpt-4o-mini",
)

team = AgentTeam(
    members=[researcher, writer, reviewer],
    strategy="round_robin",  # Reviewer runs last
)
```

## Troubleshooting

### High Costs

**Symptom**: `total_cost` exceeds expectations

**Solutions**:
- Reduce `max_rounds`
- Use cheaper models (gpt-4o-mini instead of gpt-4o)
- Limit worker agent count in map-reduce
- Set per-agent `budget_limit`

### Poor Coordination

**Symptom**: Coordinator doesn't delegate properly

**Solutions**:
- Use stronger model for coordinator (gpt-4o)
- Improve coordinator role description with explicit delegation rules
- Verify delegation tools are passed to coordinator
- Check tool descriptions clearly explain each specialist's capability

### Message Timeouts

**Symptom**: `bus.receive()` returns `None`

**Solutions**:
- Increase timeout: `await bus.receive("agent", timeout=60.0)`
- Check agent is registered: `bus.registered_agents`
- Verify message was sent to correct recipient
- Debug with `bus.get_history()`

## See Also

- [Agent Documentation](../api/core.md) - Core Agent API
- [Tools Guide](tools.md) - Tool calling and delegation tools
- [Workflow Guide](workflows.md) - Single-agent sequential workflows
- [Examples](../examples.md) - Complete orchestration examples
