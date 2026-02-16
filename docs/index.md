# AgentWeave

**Protocol-First Multi-Agent Framework for Python**

AgentWeave is an async-first Python framework for building multi-agent AI systems with native support for [MCP](https://modelcontextprotocol.io/) (Model Context Protocol) and [A2A](https://google.github.io/A2A/) (Agent-to-Agent) protocols.

## Why AgentWeave?

- **Simple API** - Create an agent in 3 lines of code
- **Protocol Native** - Built-in MCP and A2A support, not bolted on
- **Provider Agnostic** - OpenAI, Anthropic, Gemini, Ollama - switch with one line
- **Production Ready** - Retry, circuit breaker, timeout, cost tracking built in
- **Composable** - Flow DSL for intuitive workflow orchestration

## Quick Example

```python
from agentweave import Agent, Workflow

# Create agents
researcher = Agent(name="researcher", role="Research specialist", model="gpt-4o-mini")
writer = Agent(name="writer", role="Content writer", model="gpt-4o-mini")

# Compose into workflow
workflow = Workflow(
    agents=[researcher, writer],
    flow="researcher -> writer",
)

# Run
result = workflow.run_sync("Write about quantum computing")
print(result.output)
```

## Next Steps

- [Getting Started](getting-started.md) - Installation and first steps
- [Core Concepts](guides/core-concepts.md) - Understand Agent, Workflow, and Flow DSL
- [Examples](examples.md) - 11 complete runnable examples
- [API Reference](api/core.md) - Full API documentation
