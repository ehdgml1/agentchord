# LLM Providers API Reference

Complete API reference for LLM provider interfaces and implementations.

## BaseLLMProvider

Abstract base class that all LLM providers must implement.

```python
from agentweave.llm.base import BaseLLMProvider
from agentweave.core import Message

class MyProvider(BaseLLMProvider):
    @property
    def model(self) -> str:
        return "my-model"

    @property
    def provider_name(self) -> str:
        return "my-provider"

    async def complete(self, messages, **kwargs):
        # Implementation
        pass

    async def stream(self, messages, **kwargs):
        # Implementation
        pass
```

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `model` | `str` | Model identifier (abstract) |
| `provider_name` | `str` | Provider name like 'openai', 'anthropic' (abstract) |

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `complete` | `async complete(messages: list[Message], *, temperature: float = 0.7, max_tokens: int = 4096, **kwargs) -> LLMResponse` | `LLMResponse` | Generate completion (abstract) |
| `stream` | `async stream(messages: list[Message], *, temperature: float = 0.7, max_tokens: int = 4096, **kwargs) -> AsyncIterator[StreamChunk]` | `AsyncIterator[StreamChunk]` | Stream completion (abstract) |

**Raises:**

- `RateLimitError`: Rate limit exceeded
- `AuthenticationError`: Authentication failed
- `APIError`: API error occurred
- `TimeoutError`: Request timed out

## OpenAIProvider

OpenAI LLM provider supporting GPT models.

```python
from agentweave.llm import OpenAIProvider

# Using environment variable OPENAI_API_KEY
provider = OpenAIProvider(model="gpt-4o-mini")

# Using explicit API key
provider = OpenAIProvider(
    model="gpt-4o",
    api_key="sk-...",
    timeout=60.0
)

response = await provider.complete(messages)
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | `str` | Required | Model name (e.g., "gpt-4o", "gpt-4o-mini") |
| `api_key` | `str \| None` | None | OpenAI API key (uses OPENAI_API_KEY env var if None) |
| `timeout` | `float` | 60.0 | Request timeout in seconds |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `model` | `str` | OpenAI model identifier |
| `provider_name` | `str` | "openai" |

**Methods:**

Inherits from `BaseLLMProvider`:
- `async complete(messages, *, temperature=0.7, max_tokens=4096, **kwargs) -> LLMResponse`
- `async stream(messages, *, temperature=0.7, max_tokens=4096, **kwargs) -> AsyncIterator[StreamChunk]`

## AnthropicProvider

Anthropic LLM provider supporting Claude models.

```python
from agentweave.llm import AnthropicProvider

# Using environment variable ANTHROPIC_API_KEY
provider = AnthropicProvider(model="claude-3-5-sonnet-20241022")

# Using explicit API key
provider = AnthropicProvider(
    model="claude-3-opus-20250219",
    api_key="sk-ant-...",
    timeout=60.0
)

response = await provider.complete(messages)
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | `str` | Required | Model name (e.g., "claude-3-5-sonnet-20241022") |
| `api_key` | `str \| None` | None | Anthropic API key (uses ANTHROPIC_API_KEY env var if None) |
| `timeout` | `float` | 60.0 | Request timeout in seconds |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `model` | `str` | Anthropic model identifier |
| `provider_name` | `str` | "anthropic" |

**Methods:**

Inherits from `BaseLLMProvider`:
- `async complete(messages, *, temperature=0.7, max_tokens=4096, **kwargs) -> LLMResponse`
- `async stream(messages, *, temperature=0.7, max_tokens=4096, **kwargs) -> AsyncIterator[StreamChunk]`

## GeminiProvider

Google Gemini LLM provider.

```python
from agentweave.llm import GeminiProvider

# Using environment variable GOOGLE_API_KEY
provider = GeminiProvider(model="gemini-2.0-flash")

# Using explicit API key
provider = GeminiProvider(
    model="gemini-2.0-flash",
    api_key="AIza...",
    timeout=60.0
)

response = await provider.complete(messages)
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | `str` | "gemini-2.0-flash" | Model name |
| `api_key` | `str \| None` | None | Google API key (uses GOOGLE_API_KEY env var if None) |
| `timeout` | `float` | 60.0 | Request timeout in seconds |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `model` | `str` | Gemini model identifier |
| `provider_name` | `str` | "gemini" |

**Methods:**

Inherits from `BaseLLMProvider`:
- `async complete(messages, *, temperature=0.7, max_tokens=4096, **kwargs) -> LLMResponse`
- `async stream(messages, *, temperature=0.7, max_tokens=4096, **kwargs) -> AsyncIterator[StreamChunk]`

## OllamaProvider

Local Ollama provider for running models locally.

```python
from agentweave.llm import OllamaProvider

# Connect to local Ollama server
provider = OllamaProvider(
    model="llama2",
    base_url="http://localhost:11434",
    timeout=120.0
)

response = await provider.complete(messages)
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | `str` | Required | Model name available in Ollama |
| `base_url` | `str` | "http://localhost:11434" | Ollama server URL |
| `timeout` | `float` | 120.0 | Request timeout in seconds |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `model` | `str` | Ollama model identifier |
| `provider_name` | `str` | "ollama" |

**Methods:**

Inherits from `BaseLLMProvider`:
- `async complete(messages, *, temperature=0.7, max_tokens=4096, **kwargs) -> LLMResponse`
- `async stream(messages, *, temperature=0.7, max_tokens=4096, **kwargs) -> AsyncIterator[StreamChunk]`

## ProviderRegistry

Manages LLM provider registration and discovery.

```python
from agentweave.llm import ProviderRegistry, get_registry

# Get global registry
registry = get_registry()

# Register a provider
def openai_factory(model, **kwargs):
    from agentweave.llm import OpenAIProvider
    return OpenAIProvider(model=model, **kwargs)

registry.register("openai", openai_factory, prefixes=["gpt-"])

# Detect provider from model name
provider = registry.detect_provider("gpt-4o-mini")
print(provider)  # "openai"

# Create provider instance
instance = registry.create_provider("gpt-4o-mini")

# List registered providers
providers = registry.list_providers()
print(providers)  # ["openai", "anthropic", "gemini", "ollama"]
```

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `register` | `register(name: str, factory: Callable, prefixes: list[str]) -> None` | `None` | Register new provider |
| `unregister` | `unregister(name: str) -> None` | `None` | Unregister provider |
| `detect_provider` | `detect_provider(model: str) -> str \| None` | `str \| None` | Detect provider from model name |
| `create_provider` | `create_provider(model: str, **kwargs) -> BaseLLMProvider` | `BaseLLMProvider` | Create provider instance |
| `list_providers` | `list_providers() -> list[str]` | `list[str]` | List all registered provider names |

**Example: Custom Provider**

```python
from agentweave.llm import BaseLLMProvider, get_registry
from agentweave.core import LLMResponse, StreamChunk, Usage

class CustomProvider(BaseLLMProvider):
    def __init__(self, model: str, api_key: str = None, timeout: float = 60.0):
        self._model = model
        self._api_key = api_key
        self._timeout = timeout

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return "custom"

    async def complete(self, messages, *, temperature=0.7, max_tokens=4096, **kwargs):
        # Implementation here
        usage = Usage(prompt_tokens=100, completion_tokens=50)
        return LLMResponse(
            content="Response here",
            model=self._model,
            usage=usage,
            finish_reason="stop"
        )

    async def stream(self, messages, *, temperature=0.7, max_tokens=4096, **kwargs):
        # Streaming implementation
        yield StreamChunk(content="Hello")
        yield StreamChunk(content=" ", finish_reason="stop")

# Register it
registry = get_registry()
def custom_factory(model, **kwargs):
    return CustomProvider(model=model, **kwargs)

registry.register("custom", custom_factory, prefixes=["custom-"])

# Use it
provider = registry.create_provider("custom-model")
```

## get_registry()

Get the global provider registry singleton.

```python
from agentweave.llm import get_registry

registry = get_registry()
```

**Returns:**

| Type | Description |
|------|-------------|
| `ProviderRegistry` | Global singleton registry instance |

## Example: Multi-Provider Agent

```python
from agentweave.llm import OpenAIProvider, AnthropicProvider
from agentweave.core import Agent

# Create agents with different providers
openai_provider = OpenAIProvider(model="gpt-4o-mini")
anthropic_provider = AnthropicProvider(model="claude-3-5-sonnet-20241022")

agent1 = Agent(
    name="gpt_agent",
    role="You help with coding",
    llm_provider=openai_provider
)

agent2 = Agent(
    name="claude_agent",
    role="You help with analysis",
    llm_provider=anthropic_provider
)

# Each agent uses its own provider
result1 = await agent1.run("Write Python code")
result2 = await agent2.run("Analyze the data")
```

## Provider Selection

AgentWeave automatically selects the appropriate provider based on the model name:

| Model Pattern | Provider |
|---------------|----------|
| `gpt-*` | OpenAI |
| `claude-*` | Anthropic |
| `gemini-*` | Google Gemini |
| `llama*`, `mistral*`, etc. | Ollama |

You can override the provider by passing `llm_provider` to Agent constructor.

## Error Handling

All providers raise consistent exception types:

```python
from agentweave.errors import (
    RateLimitError,
    AuthenticationError,
    APIError,
    TimeoutError,
    ModelNotFoundError
)

try:
    response = await provider.complete(messages)
except RateLimitError as e:
    print(f"Rate limited, retry after {e.retry_after}s")
except AuthenticationError as e:
    print(f"Auth failed for {e.provider}")
except TimeoutError as e:
    print(f"Timed out after {e.timeout_seconds}s")
except ModelNotFoundError as e:
    print(f"Model {e.model} not found")
except APIError as e:
    print(f"API error: {e.status_code}")
```

See [Errors API](./errors.md) for complete error reference.
