# Getting Started

Get up and running with AgentWeave in minutes.

## Installation

```bash
# Base installation
pip install agentweave

# With specific providers
pip install agentweave[openai]       # OpenAI (GPT models)
pip install agentweave[anthropic]    # Anthropic (Claude models)
pip install agentweave[all]          # All providers + protocols
```

Gemini and Ollama use `httpx` (included in base) and need no extras.

## Environment Setup

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Google Gemini
export GOOGLE_API_KEY="..."

# Ollama (no key needed - runs locally)
# Install: https://ollama.ai
# Start: ollama serve
```

## Your First Agent

```python
from agentweave import Agent

agent = Agent(
    name="assistant",
    role="Helpful AI assistant",
    model="gpt-4o-mini",
)

result = agent.run_sync("What is quantum computing?")
print(result.output)
print(f"Tokens: {result.usage.total_tokens}, Cost: ${result.cost:.4f}")
```

For async contexts:

```python
import asyncio
from agentweave import Agent

async def main():
    agent = Agent(name="assistant", role="AI Helper", model="gpt-4o-mini")
    result = await agent.run("Explain machine learning")
    print(result.output)

asyncio.run(main())
```

## Adding Tools

Tools let agents call Python functions:

```python
from agentweave import Agent, tool

@tool(description="Get current weather for a city")
def get_weather(city: str) -> str:
    return f"Weather in {city}: 22C, Sunny"

@tool(description="Calculate a math expression")
def calculate(expression: str) -> str:
    return str(eval(expression))  # simplified example

agent = Agent(
    name="helper",
    role="Assistant with tools",
    model="gpt-4o-mini",
    tools=[get_weather, calculate],
)

# Agent automatically calls tools when needed
result = agent.run_sync("What's the weather in Seoul and what is 15 * 7?")
print(result.output)
```

## Multi-Agent Workflows

Chain agents together with the Flow DSL:

```python
from agentweave import Agent, Workflow

researcher = Agent(name="researcher", role="Research specialist", model="gpt-4o-mini")
writer = Agent(name="writer", role="Content writer", model="gpt-4o-mini")
reviewer = Agent(name="reviewer", role="Quality reviewer", model="gpt-4o-mini")

# Sequential: each agent receives the previous agent's output
workflow = Workflow(
    agents=[researcher, writer, reviewer],
    flow="researcher -> writer -> reviewer",
)

result = workflow.run_sync("Write about AI trends in 2025")
print(result.output)
print(f"Total cost: ${result.total_cost:.4f}")
```

### Parallel Execution

Run agents concurrently with brackets:

```python
from agentweave import Agent, Workflow, MergeStrategy

analyst1 = Agent(name="technical", role="Technical analyst", model="gpt-4o-mini")
analyst2 = Agent(name="business", role="Business analyst", model="gpt-4o-mini")
synthesizer = Agent(name="synthesizer", role="Report synthesizer", model="gpt-4o-mini")

# Parallel then sequential
workflow = Workflow(
    agents=[analyst1, analyst2, synthesizer],
    flow="[technical, business] -> synthesizer",
    merge_strategy=MergeStrategy.CONCAT_NEWLINE,
)

result = workflow.run_sync("Analyze the impact of LLMs")
```

### Mixed Patterns

```python
# A -> [B, C] -> D
workflow = Workflow(
    agents=[researcher, analyst1, analyst2, writer],
    flow="researcher -> [technical, business] -> writer",
)
```

## Memory

Make agents remember previous conversations:

```python
from agentweave import Agent, ConversationMemory

memory = ConversationMemory()
agent = Agent(
    name="chatbot",
    role="Conversational assistant",
    model="gpt-4o-mini",
    memory=memory,
)

await agent.run("My name is Alice")
result = await agent.run("What's my name?")
print(result.output)  # Remembers Alice
```

## Cost Tracking

Monitor spending across agents:

```python
from agentweave import Agent, CostTracker

tracker = CostTracker()
agent = Agent(
    name="tracked",
    role="Assistant",
    model="gpt-4o-mini",
    cost_tracker=tracker,
)

await agent.run("Hello!")
await agent.run("How are you?")

summary = tracker.get_summary()
print(f"Total cost: ${summary.total_cost:.4f}")
print(f"Total tokens: {summary.total_tokens:,}")
print(f"Requests: {summary.request_count}")
```

## Streaming

Stream responses in real-time:

```python
async for chunk in agent.stream("Tell me a story"):
    print(chunk.delta, end="", flush=True)
print()
```

## Resilience

Add retry, circuit breaker, and timeout:

```python
from agentweave import Agent, ResilienceConfig, RetryPolicy

agent = Agent(
    name="robust",
    role="Reliable assistant",
    model="gpt-4o-mini",
    resilience=ResilienceConfig(
        retry_policy=RetryPolicy(max_retries=3),
    ),
)
```

## Multiple Providers

Switch providers by changing the model name:

```python
# OpenAI
agent = Agent(name="a", role="Helper", model="gpt-4o-mini")

# Anthropic
agent = Agent(name="a", role="Helper", model="claude-3-5-sonnet")

# Google Gemini (no extra package needed)
agent = Agent(name="a", role="Helper", model="gemini-2.0-flash")

# Ollama local (no API key needed)
agent = Agent(name="a", role="Helper", model="ollama/llama3.2")
```

## Error Handling

```python
from agentweave import Agent
from agentweave.errors.exceptions import (
    AgentExecutionError,
    MissingAPIKeyError,
    RateLimitError,
)

try:
    result = agent.run_sync("Hello")
except MissingAPIKeyError:
    print("Set your API key first")
except RateLimitError as e:
    print(f"Rate limited, retry after {e.retry_after}s")
except AgentExecutionError as e:
    print(f"Execution failed: {e}")
```

## Next Steps

- [Core Concepts](guides/core-concepts.md) - Deep dive into Agent, Workflow, State
- [Tools Guide](guides/tools.md) - Advanced tool creation and MCP integration
- [Providers Guide](guides/providers.md) - Configure and customize LLM providers
- [Resilience Guide](guides/resilience.md) - Production-ready error handling
- [API Reference](api/core.md) - Complete API documentation
- [Examples](examples.md) - 11 runnable examples
