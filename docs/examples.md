# Examples

AgentWeave includes 11 complete examples in the `examples/` directory.

## Running Examples

```bash
# Set your API key
export OPENAI_API_KEY="sk-your-key"

# Run any example
python examples/01_hello_world.py
```

## Example Index

| # | File | Description | API Key Required |
|---|------|-------------|-----------------|
| 01 | `hello_world.py` | Basic Agent creation and execution | Yes |
| 02 | `multi_model.py` | Using multiple LLM providers | Yes |
| 03 | `workflow_sequential.py` | Sequential multi-agent workflow | Yes |
| 04 | `workflow_parallel.py` | Parallel execution with merge strategies | Yes |
| 05 | `with_mcp.py` | MCP tool integration (mock mode) | No |
| 06 | `a2a_server.py` | Agent-to-Agent protocol server | No |
| 07 | `memory_system.py` | Conversation and working memory | Yes |
| 08 | `cost_tracking.py` | Token usage and cost monitoring | Yes |
| 09 | `tools.py` | Tool system and @tool decorator | No |
| 10 | `streaming.py` | Streaming responses with tools (mock) | No |
| 11 | `full_agent.py` | All features combined (mock) | No |

## Highlights

### Hello World (01)

```python
from agentweave import Agent

agent = Agent(name="assistant", role="AI Helper", model="gpt-4o-mini")
result = agent.run_sync("Hello!")
print(result.output)
```

### Workflow with Flow DSL (03-04)

```python
# Sequential: A -> B -> C
workflow = Workflow(agents=[a, b, c], flow="researcher -> writer -> reviewer")

# Parallel: [A, B] -> C
workflow = Workflow(agents=[a, b, c], flow="[analyst1, analyst2] -> summarizer")

# Mixed: A -> [B, C] -> D
workflow = Workflow(agents=[a, b, c, d], flow="researcher -> [analyst1, analyst2] -> writer")
```

### Tools (09)

```python
from agentweave import tool

@tool(description="Add two numbers")
def add(a: int, b: int) -> int:
    return a + b

agent = Agent(name="math", role="Calculator", tools=[add])
```
