# AgentChord Code Generator

The AgentChord code generator converts visual workflow graphs into executable Python code using the AgentChord framework.

## Features

### Dual Format Generation

The generator intelligently selects between two output formats:

1. **Simple Format** - For workflows containing only Agent nodes
2. **Complex Format** - For workflows with control flow (conditions, loops, parallel execution)

### Supported Node Types

| Node Type | Description | Output Format |
|-----------|-------------|---------------|
| **Agent** | AI agent with configurable model, temperature, and prompts | Agent instance definition + execution |
| **Condition** | Conditional branching (if/else) | Python if/else blocks |
| **Parallel** | Concurrent execution of multiple branches | `asyncio.gather()` |
| **Feedback Loop** | Iterative execution with stop condition | for loop with break |
| **MCP Tool** | Model Context Protocol tool invocation | Commented MCP client call |
| **Trigger** | Workflow trigger (cron/webhook) | Comment documenting trigger |
| **Start/End** | Workflow boundaries | Comments |

## Usage

```typescript
import { generateCode } from './utils/codeGenerator';

const code = generateCode(nodes, edges);
console.log(code);
```

## Examples

### Simple Workflow (Agent Chain)

**Input:**
```
Agent1 → Agent2 → Agent3
```

**Output:**
```python
from agentchord import Agent, Workflow

agent1 = Agent(
    name="Agent1",
    role="Assistant",
    model="gpt-4o-mini",
    temperature=0.7,
)

agent2 = Agent(
    name="Agent2",
    role="Assistant",
    model="gpt-4o-mini",
    temperature=0.7,
)

agent3 = Agent(
    name="Agent3",
    role="Assistant",
    model="gpt-4o-mini",
    temperature=0.7,
)

workflow = Workflow(
    agents=[agent1, agent2, agent3],
    flow="agent1 -> agent2 -> agent3",
)

if __name__ == "__main__":
    result = workflow.run_sync("Your input here")
    print(result.output)
```

### Conditional Workflow

**Input:**
```
Agent1 → Condition → Agent2 (true)
                   → Agent3 (false)
```

**Output:**
```python
import asyncio
from agentchord import Agent

agent1 = Agent(
    name="Agent1",
    role="Assistant",
    model="gpt-4o-mini",
    temperature=0.7,
)

agent2 = Agent(
    name="Agent2",
    role="Assistant",
    model="gpt-4o-mini",
    temperature=0.7,
)

agent3 = Agent(
    name="Agent3",
    role="Assistant",
    model="gpt-4o-mini",
    temperature=0.7,
)

# --- Workflow Logic ---
async def workflow_main(input_text: str):
    result = input_text
    # Agent: Agent1
    result = await agent1.complete(result)
    # Condition: result.valid
    if result.valid:
        # Agent: Agent2
        result = await agent2.complete(result)
    else:
        # Agent: Agent3
        result = await agent3.complete(result)
    return result

if __name__ == "__main__":
    input_text = "Your input here"
    result = asyncio.run(workflow_main(input_text))
    print(result)
```

### Parallel Execution

**Input:**
```
Parallel → Agent1
        → Agent2
        → Agent3
```

**Output:**
```python
import asyncio
from agentchord import Agent

agent1 = Agent(
    name="Agent1",
    role="Assistant",
    model="gpt-4o-mini",
    temperature=0.7,
)

agent2 = Agent(
    name="Agent2",
    role="Assistant",
    model="gpt-4o-mini",
    temperature=0.7,
)

agent3 = Agent(
    name="Agent3",
    role="Assistant",
    model="gpt-4o-mini",
    temperature=0.7,
)

# --- Workflow Logic ---
async def workflow_main(input_text: str):
    result = input_text
    # Parallel execution (merge: concat)
    results = await asyncio.gather(
        agent1.complete(result),
        agent2.complete(result),
        agent3.complete(result)
    )
    result = ' '.join(str(r) for r in results)
    return result

if __name__ == "__main__":
    input_text = "Your input here"
    result = asyncio.run(workflow_main(input_text))
    print(result)
```

### Feedback Loop

**Input:**
```
FeedbackLoop → Agent1 (loop body)
  maxIterations: 5
  stopCondition: result.done
```

**Output:**
```python
import asyncio
from agentchord import Agent

agent1 = Agent(
    name="LoopAgent",
    role="Assistant",
    model="gpt-4o-mini",
    temperature=0.7,
)

# --- Workflow Logic ---
async def workflow_main(input_text: str):
    result = input_text
    # Feedback loop (max 5 iterations, stop: result.done)
    loop_result = result
    for _iteration in range(5):
        # Agent: LoopAgent
        result = await agent1.complete(loop_result)
        if result.done:
            break
    result = loop_result
    return result

if __name__ == "__main__":
    input_text = "Your input here"
    result = asyncio.run(workflow_main(input_text))
    print(result)
```

### MCP Tool Integration

**Input:**
```
MCPTool(server: "filesystem", tool: "read_file")
```

**Output:**
```python
import asyncio
from agentchord import Agent
# from agentchord.protocols.mcp import MCPClient

# --- Workflow Logic ---
async def workflow_main(input_text: str):
    result = input_text
    # MCP Tool: read_file (filesystem)
    # result = await mcp_client.call_tool(
    #     server_id="filesystem",
    #     tool_name="read_file",
    #     parameters={
    #         "path": "/path/to/file"
    #     }
    # )
    return result

if __name__ == "__main__":
    input_text = "Your input here"
    result = asyncio.run(workflow_main(input_text))
    print(result)
```

### Complex Workflow

**Input:**
```
Trigger(webhook: /api/start)
  ↓
Agent1
  ↓
Condition(result.valid)
  ├─ true → Parallel → Agent2
  │                  → Agent3
  └─ false → Agent4
```

**Output:**
```python
import asyncio
from agentchord import Agent

agent1 = Agent(
    name="InputAgent",
    role="Assistant",
    model="gpt-4o-mini",
    temperature=0.7,
)

agent2 = Agent(
    name="ProcessorA",
    role="Assistant",
    model="gpt-4o-mini",
    temperature=0.7,
)

agent3 = Agent(
    name="ProcessorB",
    role="Assistant",
    model="gpt-4o-mini",
    temperature=0.7,
)

agent4 = Agent(
    name="OutputAgent",
    role="Assistant",
    model="gpt-4o-mini",
    temperature=0.7,
)

# --- Workflow Logic ---
async def workflow_main(input_text: str):
    result = input_text
    # Trigger: Webhook (/api/start)
    # Agent: InputAgent
    result = await agent1.complete(result)
    # Condition: result.valid
    if result.valid:
        # Parallel execution (merge: concat)
        results = await asyncio.gather(
            agent2.complete(result),
            agent3.complete(result)
        )
        result = ' '.join(str(r) for r in results)
    else:
        # Agent: OutputAgent
        result = await agent4.complete(result)
    return result

if __name__ == "__main__":
    input_text = "Your input here"
    result = asyncio.run(workflow_main(input_text))
    print(result)
```

## Implementation Details

### Format Selection

The generator uses simple format when:
- Workflow contains only Agent nodes
- No control flow nodes (Condition, Parallel, FeedbackLoop, MCPTool, Trigger)

The generator uses complex format when:
- Workflow contains any control flow node
- Requires branching, looping, or parallel execution

### Node Processing

1. **Topological Sort**: Determines execution order based on edge dependencies
2. **Node Execution**: Each node type has a dedicated generator method
3. **Edge Handling**: Conditional edges (true/false) route to appropriate branches
4. **Variable Naming**: Agent names converted to snake_case for Python variables

### Merge Strategies (Parallel Nodes)

- `concat`: Join all results with space separator
- `first`: Use first completed result
- `last`: Use last completed result
- `custom`: Return array of results for custom handling

## Testing

The generator includes comprehensive test coverage:

- **21 tests** for simple workflows (backward compatibility)
- **16 tests** for complex node types
- **37 total tests** covering all node types and edge cases

Run tests:
```bash
npm test -- src/utils/codeGenerator
```

## Type Safety

All generated code is type-checked using TypeScript. The generator uses:

- Strict type definitions from `types/blocks.ts`
- WorkflowNode and WorkflowEdge interfaces
- Proper type casting for node data

## Future Enhancements

Potential improvements:
- [ ] Support for custom merge functions in parallel nodes
- [ ] More sophisticated loop detection for feedback
- [ ] Agent-to-agent direct message passing
- [ ] Error handling edge support
- [ ] Retry policies for failed nodes
- [ ] Timeout configurations
