# ADR-001: Use ABC-based Provider Abstraction with Prefix Registry

## Status
Accepted

## Context

AgentChord integrates with multiple LLM providers (OpenAI, Anthropic, Ollama, Gemini), each having different API clients, response formats, and authentication mechanisms. We needed an abstraction layer that would:

1. Provide a unified interface across all providers
2. Enable runtime provider selection based on model names (e.g., `gpt-4o` → OpenAI, `claude-3-5-sonnet` → Anthropic)
3. Handle provider-specific quirks transparently
4. Support lazy loading to avoid importing unused provider SDKs
5. Allow dynamic registration/unregistration of providers (for extensibility and testing)

Initial alternatives considered:
- **Strategy pattern with factory function**: Simple but requires hardcoded provider detection logic
- **Plugin architecture**: Overly complex for the 4 built-in providers
- **Direct provider classes without abstraction**: Violates DRY, makes testing difficult

## Decision

We implemented a **two-layer abstraction**:

### Layer 1: BaseLLMProvider ABC

Located in `agentchord/llm/base.py`, `BaseLLMProvider` defines the contract that all providers must implement:

```python
class BaseLLMProvider(ABC):
    @property
    @abstractmethod
    def model(self) -> str: ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    async def complete(
        self, messages: list[Message], *,
        temperature: float = 0.7, max_tokens: int = 4096, **kwargs
    ) -> LLMResponse: ...

    @abstractmethod
    async def stream(
        self, messages: list[Message], *,
        temperature: float = 0.7, max_tokens: int = 4096, **kwargs
    ) -> AsyncIterator[StreamChunk]: ...

    @property
    @abstractmethod
    def cost_per_1k_input_tokens(self) -> float: ...

    @property
    @abstractmethod
    def cost_per_1k_output_tokens(self) -> float: ...
```

**Key design points**:
- **Unified response type**: All providers return `LLMResponse` with normalized `tool_calls`, `usage`, and `finish_reason`
- **Cost calculation**: Abstract properties allow provider-specific pricing tables (e.g., `MODEL_COSTS` in `openai.py`)
- **Lazy client initialization**: Providers use `_get_client()` to defer SDK imports until first use

### Layer 2: ProviderRegistry

Located in `agentchord/llm/registry.py`, `ProviderRegistry` manages provider registration and auto-detection:

```python
class ProviderRegistry:
    def register(
        self, name: str, factory: Callable,
        prefixes: list[str],
        default_cost_input: float = 0.0,
        default_cost_output: float = 0.0
    ) -> None: ...

    def detect_provider(self, model: str) -> str: ...

    def create_provider(self, model: str, **kwargs) -> BaseLLMProvider: ...
```

**Prefix-based detection**: Model names are matched against registered prefixes in **longest-first order**:
```python
# Sorted by prefix length descending to avoid false matches
# e.g., "gpt-4o" matches "gpt-" before "gpt" if both exist
self._prefix_map = sorted(pairs, key=lambda p: len(p[0]), reverse=True)
```

**Built-in provider registration** (from `_register_defaults()`):
- OpenAI: `["gpt-", "o1", "text-"]` → `OpenAIProvider`
- Anthropic: `["claude-"]` → `AnthropicProvider`
- Ollama: `["ollama/"]` → `OllamaProvider`
- Gemini: `["gemini-"]` → `GeminiProvider`

**Global singleton**:
```python
def get_registry() -> ProviderRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = ProviderRegistry()
        _register_defaults(_default_registry)
    return _default_registry
```

### Provider-Specific Adaptation Examples

**Anthropic content blocks** (`anthropic.py:241-254`):
```python
def _convert_response(self, response: Any) -> LLMResponse:
    content = ""
    tool_calls = []
    for block in response.content:
        if hasattr(block, "text"):
            content = block.text  # Text block
        elif block.type == "tool_use":
            tool_calls.append(ToolCall(...))  # Tool use block
```

**OpenAI tool call JSON parsing** (`openai.py:234-240`):
```python
@staticmethod
def _parse_tool_arguments(arguments: str) -> dict[str, Any]:
    try:
        return json.loads(arguments)
    except (json.JSONDecodeError, TypeError):
        return {}  # Fail gracefully
```

**Temperature clamping for Claude** (`anthropic.py:137`):
```python
"temperature": min(temperature, 1.0),  # Claude max is 1.0
```

## Consequences

### Positive
- **Type safety**: mypy enforces all providers implement the full ABC contract
- **Extensibility**: Users can register custom providers at runtime:
  ```python
  registry = get_registry()
  registry.register("custom", CustomProviderFactory, ["custom-"])
  ```
- **Testability**: Mock providers can be registered in tests without touching production code
- **Encapsulation**: Provider-specific quirks (Anthropic's `system` parameter, OpenAI's `tool_calls` JSON parsing) are hidden behind the abstraction
- **Lazy imports**: Provider SDKs are only imported when first used, reducing startup time

### Negative
- **Indirection**: Two-layer design adds cognitive overhead compared to direct provider usage
- **Prefix collisions**: If two providers use overlapping prefixes (e.g., `"gpt-"` and `"gpt"`), longest-match heuristic may not always be correct
- **Silent fallbacks**: Some providers (e.g., `OpenAIProvider._parse_tool_arguments`) fail gracefully, which may hide malformed API responses
- **Global state**: `get_registry()` returns a singleton, making it harder to isolate in parallel tests

### Neutral
- **Factory pattern overhead**: Each provider requires a factory function in `_register_defaults()`, adding boilerplate
- **Cost tables**: Each provider maintains a hardcoded `MODEL_COSTS` dict that must be manually updated when pricing changes
- **Error translation**: Each provider must translate SDK-specific errors (e.g., `openai.RateLimitError`) to AgentChord errors (`RateLimitError`)

## References
- Implementation: `agentchord/llm/base.py`, `agentchord/llm/registry.py`
- Providers: `agentchord/llm/{openai,anthropic,ollama,gemini}.py`
- Tests: `agentchord/tests/unit/llm/test_registry.py` (25 tests)
