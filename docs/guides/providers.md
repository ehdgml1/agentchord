# LLM Providers Guide

AgentWeave supports multiple LLM providers through a unified interface. The framework automatically detects and creates the appropriate provider based on the model name.

## Quick Start

Change providers by simply changing the model string:

```python
from agentweave import Agent

# OpenAI
agent = Agent(name="ai", role="Helper", model="gpt-4o")

# Anthropic
agent = Agent(name="ai", role="Helper", model="claude-3-5-sonnet")

# Google Gemini
agent = Agent(name="ai", role="Helper", model="gemini-2.0-flash")

# Ollama (local)
agent = Agent(name="ai", role="Helper", model="ollama/llama3.2")
```

No code changes needed - just swap the model name.

## Provider Registry

AgentWeave uses a registry system for managing providers:

```python
from agentweave.llm.registry import get_registry

registry = get_registry()

# List all registered providers
providers = registry.list_providers()
print(providers)  # ["openai", "anthropic", "gemini", "ollama"]

# Detect provider from model name
provider_name = registry.detect_provider("gpt-4o")
print(provider_name)  # "openai"

# Create a provider
provider = registry.create_provider("claude-3-5-sonnet")
```

### Automatic Provider Detection

Model prefixes are mapped to providers:

| Provider | Model Prefixes | Examples |
|----------|----------------|----------|
| OpenAI | `gpt-`, `o1`, `text-` | `gpt-4o`, `gpt-4o-mini`, `o1` |
| Anthropic | `claude-` | `claude-3-5-sonnet`, `claude-3-haiku` |
| Gemini | `gemini-` | `gemini-2.0-flash`, `gemini-1.5-pro` |
| Ollama | `ollama/` | `ollama/llama3.2`, `ollama/mistral` |

## OpenAI

OpenAI models via the official API.

### Available Models

- `gpt-4o` - Latest flagship model (recommended)
- `gpt-4o-mini` - Faster, cheaper version
- `gpt-4-turbo` - Previous generation
- `gpt-3.5-turbo` - Older, very cheap
- `o1` - Reasoning models

### Setup

```python
import os
from agentweave import Agent

# Set API key via environment variable
os.environ["OPENAI_API_KEY"] = "sk-..."

# Create agent - API key is auto-detected
agent = Agent(
    name="assistant",
    role="Helpful AI",
    model="gpt-4o",
    temperature=0.7,
    max_tokens=4096
)

result = agent.run_sync("Explain quantum computing")
print(result.output)
```

### Custom Provider

```python
from agentweave.llm.openai import OpenAIProvider
from agentweave import Agent

provider = OpenAIProvider(
    model="gpt-4o",
    api_key="sk-..."
)

agent = Agent(
    name="assistant",
    role="Helpful AI",
    llm_provider=provider
)
```

### Provider Cost Tracking

OpenAI costs are automatically calculated:

```python
result = agent.run_sync("Hello")
print(f"Cost: ${result.cost:.4f}")
print(f"Tokens: {result.usage.total_tokens}")
```

Pricing is built-in for current models. Custom pricing can be set via provider configuration.

## Anthropic

Anthropic models (Claude) via their API.

### Available Models

- `claude-3-5-sonnet-20241022` - Latest, best all-around
- `claude-3-5-haiku-20241022` - Fast, efficient
- `claude-3-opus-20250219` - Most capable
- `claude-3-haiku` - Older version

### Setup

```python
import os
from agentweave import Agent

# Set API key
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."

agent = Agent(
    name="assistant",
    role="Expert analyst",
    model="claude-3-5-sonnet-20241022",
    temperature=0.7
)

result = agent.run_sync("Analyze this trend")
print(result.output)
```

### Custom Provider

```python
from agentweave.llm.anthropic import AnthropicProvider
from agentweave import Agent

provider = AnthropicProvider(
    model="claude-3-5-sonnet-20241022",
    api_key="sk-ant-..."
)

agent = Agent(
    name="assistant",
    role="Expert analyst",
    llm_provider=provider
)
```

### Provider Features

- Supports extended thinking (if configured)
- Vision capabilities with Claude 3.5 Sonnet
- Streaming support

## Google Gemini

Google's Gemini models via their API.

### Available Models

- `gemini-2.0-flash` - Latest, very fast
- `gemini-1.5-pro` - Most capable
- `gemini-1.5-flash` - Faster variant
- `gemini-pro` - Previous generation

### Setup

```python
import os
from agentweave import Agent

# Set API key
os.environ["GOOGLE_API_KEY"] = "AIza..."

agent = Agent(
    name="assistant",
    role="Research helper",
    model="gemini-2.0-flash",
    temperature=0.5
)

result = agent.run_sync("Summarize recent AI developments")
print(result.output)
```

### Custom Provider

```python
from agentweave.llm.gemini import GeminiProvider
from agentweave import Agent

provider = GeminiProvider(
    model="gemini-2.0-flash",
    api_key="AIza..."
)

agent = Agent(
    name="assistant",
    role="Research helper",
    llm_provider=provider
)
```

### Base URL

Customize the API endpoint:

```python
provider = GeminiProvider(
    model="gemini-2.0-flash",
    api_key="AIza...",
    base_url="https://generativelanguage.googleapis.com/v1beta"
)
```

## Ollama (Local)

Run open-source models locally with Ollama.

### Installation

```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama3.2
ollama pull mistral
```

### Available Models

- `ollama/llama3.2` - Meta's Llama 3.2
- `ollama/mistral` - Mistral 7B
- `ollama/neural-chat` - Intel Neural Chat
- `ollama/openchat` - OpenChat
- Any model available on ollama.com

### Setup

```python
from agentweave import Agent

# Ollama runs locally by default on port 11434
agent = Agent(
    name="local_assistant",
    role="Local helper",
    model="ollama/llama3.2",
    temperature=0.7
)

result = agent.run_sync("What are you?")
print(result.output)
```

### Custom Ollama Server

```python
from agentweave.llm.ollama import OllamaProvider
from agentweave import Agent

provider = OllamaProvider(
    model="llama3.2",
    base_url="http://192.168.1.100:11434"  # Different host
)

agent = Agent(
    name="remote_assistant",
    role="Helper",
    llm_provider=provider
)
```

### Free, Private, Fast

- No API costs
- Runs entirely locally
- Data stays on your machine
- Models vary in quality/speed

### Selecting Models

Choose based on your hardware:

| Hardware | Recommended | Notes |
|----------|------------|-------|
| 8GB RAM | `llama3.2:1b` | Smallest, fastest |
| 16GB RAM | `llama3.2:3b` or `mistral` | Good balance |
| 32GB+ RAM | `llama3.2:8b` | Better quality |
| GPU | Any model | Runs much faster |

## Custom Provider

Implement your own provider for private or custom models:

```python
from agentweave.llm.base import BaseLLMProvider
from agentweave.core.types import LLMResponse, Message, StreamChunk, Usage
from typing import Any, AsyncIterator

class MyCustomProvider(BaseLLMProvider):
    def __init__(self, model: str, api_key: str):
        self._model = model
        self._api_key = api_key

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return "mycustom"

    async def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        """Call your custom API."""
        # Implementation
        return LLMResponse(
            content="Your response",
            model=self._model,
            usage=Usage(prompt_tokens=10, completion_tokens=5),
            finish_reason="stop"
        )

    async def stream(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """Stream responses from your API."""
        yield StreamChunk(
            content="First ",
            delta="First "
        )
        yield StreamChunk(
            content="First chunk",
            delta="chunk",
            finish_reason="stop",
            usage=Usage(prompt_tokens=10, completion_tokens=5)
        )

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return 0.01

    @property
    def cost_per_1k_output_tokens(self) -> float:
        return 0.02
```

### Register Custom Provider

```python
from agentweave.llm.registry import get_registry
from agentweave import Agent

# Create factory
def create_custom(model: str, **kwargs) -> BaseLLMProvider:
    return MyCustomProvider(model=model, **kwargs)

# Register
registry = get_registry()
registry.register("mycustom", create_custom, ["custom-"])

# Use in Agent
agent = Agent(
    name="assistant",
    role="Helper",
    model="custom-mymodel",
    api_key="..."
)
```

## Streaming Support

All providers support streaming responses:

```python
agent = Agent(
    name="assistant",
    role="Helpful AI",
    model="gpt-4o",  # Works with any provider
)

# Stream response token by token
async for chunk in agent.stream("Write a short story"):
    print(chunk.delta, end="", flush=True)
```

Provider-specific stream implementation:

```python
# When using custom provider
async for chunk in provider.stream(messages):
    print(f"Chunk: {chunk.delta}")
    if chunk.finish_reason:
        print(f"Usage: {chunk.usage}")
```

## Cost Tracking

Costs are automatically calculated for supported providers:

```python
result = agent.run_sync("Hello")

print(f"Input tokens: {result.usage.prompt_tokens}")
print(f"Output tokens: {result.usage.completion_tokens}")
print(f"Total tokens: {result.usage.total_tokens}")
print(f"Estimated cost: ${result.cost:.4f}")
```

Costs per model:

| Provider | Model | Input/1k | Output/1k |
|----------|-------|----------|-----------|
| OpenAI | gpt-4o | $0.005 | $0.015 |
| OpenAI | gpt-4o-mini | $0.00015 | $0.0006 |
| Anthropic | claude-3-5-sonnet | $0.003 | $0.015 |
| Anthropic | claude-3-5-haiku | $0.00080 | $0.004 |
| Gemini | gemini-2.0-flash | $0.0001 | $0.0004 |
| Ollama | Any | $0.00 | $0.00 |

For custom providers:

```python
class MyProvider(BaseLLMProvider):
    @property
    def cost_per_1k_input_tokens(self) -> float:
        return 0.001  # $0.001 per 1k tokens

    @property
    def cost_per_1k_output_tokens(self) -> float:
        return 0.002  # $0.002 per 1k tokens

# Cost automatically calculated when agent runs
result = agent.run_sync("Hello")
estimated_cost = result.cost  # Calculated from token usage
```

## Best Practices

### 1. Choose Based on Requirements

```python
# Use gpt-4o for best results
agent = Agent(model="gpt-4o")

# Use gpt-4o-mini for speed and cost
agent = Agent(model="gpt-4o-mini")

# Use claude-3-5-sonnet for reasoning
agent = Agent(model="claude-3-5-sonnet")

# Use ollama/llama3.2 for privacy
agent = Agent(model="ollama/llama3.2")
```

### 2. Use Environment Variables

```python
import os

# Define in .env file
os.environ["OPENAI_API_KEY"] = "sk-..."
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."
os.environ["GOOGLE_API_KEY"] = "AIza..."

# Providers auto-detect from environment
agent = Agent(name="ai", role="Helper", model="gpt-4o")
```

### 3. Error Handling

```python
from agentweave.errors.exceptions import ModelNotFoundError, APIError

try:
    result = agent.run_sync("Hello")
except ModelNotFoundError:
    print("Unknown model name")
except APIError as e:
    print(f"API error: {e}")
```

### 4. Monitor Costs

```python
total_cost = 0.0

for query in queries:
    result = agent.run_sync(query)
    total_cost += result.cost
    print(f"Query cost: ${result.cost:.4f}, Total: ${total_cost:.4f}")
```

### 5. Switch Providers in Production

```python
# Easy to A/B test different providers
import os

provider = os.environ.get("LLM_PROVIDER", "openai")
model = "gpt-4o" if provider == "openai" else "claude-3-5-sonnet"

agent = Agent(
    name="assistant",
    role="Helper",
    model=model
)
```

## Complete Example

```python
from agentweave import Agent
import os

async def main():
    # Configure providers
    os.environ["OPENAI_API_KEY"] = "sk-..."
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."

    # Create agents with different providers
    openai_agent = Agent(
        name="openai_bot",
        role="OpenAI Assistant",
        model="gpt-4o"
    )

    anthropic_agent = Agent(
        name="anthropic_bot",
        role="Anthropic Assistant",
        model="claude-3-5-sonnet-20241022"
    )

    local_agent = Agent(
        name="local_bot",
        role="Local Assistant",
        model="ollama/llama3.2"
    )

    # Compare responses
    prompt = "Explain quantum entanglement in simple terms"

    result1 = openai_agent.run_sync(prompt)
    print(f"OpenAI (${result1.cost:.4f}): {result1.output[:100]}...")

    result2 = anthropic_agent.run_sync(prompt)
    print(f"Anthropic (${result2.cost:.4f}): {result2.output[:100]}...")

    result3 = local_agent.run_sync(prompt)
    print(f"Local (free): {result3.output[:100]}...")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## See Also

- [Tools Guide](tools.md) - Use tools with any provider
- [Memory Guide](memory.md) - Preserve context across providers
- [Resilience Guide](resilience.md) - Handle provider failures
- [Agent Documentation](../api/core.md) - Agent API details
