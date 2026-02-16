# Resilience API Reference

Complete API reference for resilience patterns that enable fault tolerance and reliability.

## RetryStrategy

Backoff strategies for retries.

```python
from agentweave.resilience import RetryStrategy

# Use fixed delay
strategy = RetryStrategy.FIXED

# Use exponential backoff
strategy = RetryStrategy.EXPONENTIAL

# Use linear increase
strategy = RetryStrategy.LINEAR
```

**Values:**

| Value | Description |
|-------|-------------|
| `FIXED` | Fixed delay between retries |
| `EXPONENTIAL` | Exponential backoff: delay = base * (2 ^ attempt) |
| `LINEAR` | Linear increase: delay = base * attempt |

## RetryPolicy

Configurable retry policy with multiple backoff strategies.

```python
from agentweave.resilience import RetryPolicy, RetryStrategy

# Basic retry with exponential backoff
policy = RetryPolicy(
    max_retries=3,
    strategy=RetryStrategy.EXPONENTIAL,
    base_delay=1.0,
    max_delay=60.0
)

# Execute with retry
result = await policy.execute(some_async_func, arg1, arg2)
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_retries` | `int` | 3 | Maximum number of retry attempts |
| `strategy` | `RetryStrategy` | EXPONENTIAL | Backoff strategy |
| `base_delay` | `float` | 1.0 | Base delay in seconds |
| `max_delay` | `float` | 60.0 | Maximum delay in seconds |
| `jitter` | `bool` | True | Add random jitter to delays |
| `jitter_factor` | `float` | 0.1 | Jitter as fraction of delay |
| `retryable_errors` | `tuple[type[Exception], ...] \| None` | None | Exceptions to retry on |

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `execute` | `async execute(func: Callable, *args, **kwargs) -> T` | `T` | Execute function with retries |

**Default Retryable Exceptions:**

- `RateLimitError`
- `TimeoutError`
- `APIError`
- `ConnectionError`
- `asyncio.TimeoutError`

**Example: Retry with Custom Exceptions**

```python
from agentweave.resilience import RetryPolicy, RetryStrategy

# Retry only on specific exceptions
policy = RetryPolicy(
    max_retries=5,
    strategy=RetryStrategy.EXPONENTIAL,
    base_delay=2.0,
    retryable_errors=(ConnectionError, TimeoutError)
)

async def api_call():
    # Function that might fail
    pass

try:
    result = await policy.execute(api_call)
except Exception as e:
    print(f"Failed after retries: {e}")
```

**Example: Delay Calculation**

```python
# With EXPONENTIAL strategy:
# Attempt 1: delay = 1.0s
# Attempt 2: delay = 2.0s (1.0 * 2^1)
# Attempt 3: delay = 4.0s (1.0 * 2^2)
# Attempt 4: delay = 8.0s (1.0 * 2^3)
# Attempt 5: delay = 16.0s (1.0 * 2^4)

policy = RetryPolicy(
    max_retries=5,
    strategy=RetryStrategy.EXPONENTIAL,
    base_delay=1.0,
    max_delay=60.0,
    jitter=True
)
```

## CircuitBreaker

Circuit breaker pattern for protecting against cascading failures.

```python
from agentweave.resilience import CircuitBreaker, CircuitState

breaker = CircuitBreaker(
    failure_threshold=5,
    success_threshold=2,
    timeout=30.0
)

try:
    result = await breaker.execute(some_api_call)
except CircuitOpenError:
    # Circuit is open, use fallback
    result = fallback_value
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `failure_threshold` | `int` | 5 | Failures to trigger open |
| `success_threshold` | `int` | 2 | Successes to close from half-open |
| `timeout` | `float` | 30.0 | Seconds before half-open attempt |
| `excluded_exceptions` | `tuple[type[Exception], ...]` | () | Exceptions that don't count as failures |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `state` | `CircuitState` | Current state: CLOSED, OPEN, HALF_OPEN |
| `failure_count` | `int` | Current failure count |
| `is_closed` | `bool` | True if circuit is closed (normal operation) |

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `execute` | `async execute(func: Callable, *args, **kwargs) -> T` | `T` | Execute with circuit protection |
| `record_success` | `record_success() -> None` | `None` | Record successful call |
| `record_failure` | `record_failure(error: Exception) -> None` | `None` | Record failed call |
| `reset` | `reset() -> None` | `None` | Reset to CLOSED state |

**States:**

| State | Description |
|-------|-------------|
| `CLOSED` | Normal operation, requests pass through |
| `OPEN` | Too many failures, requests rejected immediately |
| `HALF_OPEN` | Testing recovery, limited requests allowed |

**Example: Circuit Breaker with API**

```python
breaker = CircuitBreaker(
    failure_threshold=5,      # Open after 5 failures
    success_threshold=2,      # Close after 2 successes from half-open
    timeout=60.0              # Try recovery after 60 seconds
)

async def call_external_api():
    try:
        result = await breaker.execute(api.get_data)
        return result
    except CircuitOpenError:
        logger.warning("Circuit breaker is open, using cached data")
        return cached_data
```

## CircuitState

Enum for circuit breaker states.

```python
from agentweave.resilience import CircuitState

if breaker.state == CircuitState.CLOSED:
    print("Normal operation")
elif breaker.state == CircuitState.OPEN:
    print("Circuit is open, service unavailable")
elif breaker.state == CircuitState.HALF_OPEN:
    print("Testing recovery")
```

**Values:**

| Value | Description |
|-------|-------------|
| `CLOSED` | Normal operation |
| `OPEN` | Failure mode |
| `HALF_OPEN` | Testing mode |

## TimeoutManager

Manages timeouts for different models and operations.

```python
from agentweave.resilience import TimeoutManager

manager = TimeoutManager(
    default_timeout=60.0,
    use_builtin_defaults=True
)

# Get timeout for model
timeout = manager.get_timeout("gpt-4o")

# Override timeout for model
manager.set_timeout("gpt-4o", 120.0)

# Execute with timeout management
result = await manager.execute(
    some_async_func,
    timeout=30.0,
    model="gpt-4o"
)
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `default_timeout` | `float` | 60.0 | Default timeout in seconds |
| `per_model_timeouts` | `dict[str, float] \| None` | None | Model-specific timeouts |
| `use_builtin_defaults` | `bool` | True | Use built-in model defaults |

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `get_timeout` | `get_timeout(model: str \| None) -> float` | `float` | Get timeout for model |
| `set_timeout` | `set_timeout(model: str, timeout: float) -> None` | `None` | Set timeout for model |
| `execute` | `async execute(func: Callable, *args, timeout: float \| None = None, model: str \| None = None, **kwargs) -> T` | `T` | Execute with timeout |

**Built-in Model Defaults:**

| Model | Timeout |
|-------|---------|
| gpt-4o | 60s |
| gpt-4o-mini | 30s |
| claude-3-5-sonnet | 60s |
| claude-3-opus | 120s |
| gemini-2.0-flash | 45s |

## ResilienceConfig

Combined resilience configuration for agents.

```python
from agentweave.resilience import (
    ResilienceConfig,
    RetryPolicy,
    RetryStrategy,
    CircuitBreaker
)
from agentweave.core import Agent

# Create resilience configuration
resilience = ResilienceConfig(
    retry_enabled=True,
    retry_policy=RetryPolicy(
        max_retries=3,
        strategy=RetryStrategy.EXPONENTIAL
    ),
    circuit_breaker_enabled=True,
    circuit_breaker=CircuitBreaker(failure_threshold=5),
    timeout_enabled=True
)

# Use in agent
agent = Agent(
    name="robust_agent",
    role="You are reliable",
    resilience=resilience
)

# Agent automatically uses resilience patterns
result = await agent.run("Do something")
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `retry_enabled` | `bool` | True | Enable retry policy |
| `retry_policy` | `RetryPolicy \| None` | None | Custom retry policy |
| `circuit_breaker_enabled` | `bool` | False | Enable circuit breaker |
| `circuit_breaker` | `CircuitBreaker \| None` | None | Custom circuit breaker |
| `timeout_enabled` | `bool` | True | Enable timeout management |
| `timeout_manager` | `TimeoutManager \| None` | None | Custom timeout manager |

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `execute` | `async execute(func: Callable, *args, model: str \| None = None, **kwargs) -> T` | `T` | Execute with all resilience patterns |
| `wrap` | `wrap(func: Callable, model: str \| None = None) -> Callable` | `Callable` | Wrap function with resilience |

## CircuitOpenError

Exception raised when circuit breaker is open.

```python
from agentweave.resilience import CircuitBreaker, CircuitOpenError

breaker = CircuitBreaker()

try:
    result = await breaker.execute(api_call)
except CircuitOpenError as e:
    print(f"Circuit is open, retry after {e.retry_after}s")
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `message` | `str` | Error message |
| `retry_after` | `float \| None` | Seconds to wait before retry |

## Complete Example: Production-Ready Agent

```python
from agentweave.resilience import (
    ResilienceConfig,
    RetryPolicy,
    RetryStrategy,
    CircuitBreaker,
    TimeoutManager
)
from agentweave.core import Agent

# Configure resilience
retry = RetryPolicy(
    max_retries=5,
    strategy=RetryStrategy.EXPONENTIAL,
    base_delay=1.0,
    max_delay=30.0
)

breaker = CircuitBreaker(
    failure_threshold=10,
    success_threshold=3,
    timeout=60.0
)

timeout = TimeoutManager(
    default_timeout=60.0,
    use_builtin_defaults=True
)

resilience = ResilienceConfig(
    retry_enabled=True,
    retry_policy=retry,
    circuit_breaker_enabled=True,
    circuit_breaker=breaker,
    timeout_enabled=True,
    timeout_manager=timeout
)

# Create robust agent
agent = Agent(
    name="production_agent",
    role="You handle production workloads",
    model="gpt-4o",
    resilience=resilience
)

# Agent automatically handles failures with retries, circuit breaking, and timeouts
result = await agent.run("Process user request")
print(f"Result: {result.output}")
```

## Best Practices

1. **Use Exponential Backoff**: Reduces server load during outages

```python
policy = RetryPolicy(
    max_retries=5,
    strategy=RetryStrategy.EXPONENTIAL,
    base_delay=1.0
)
```

2. **Set Reasonable Timeouts**: Prevent hanging requests

```python
manager = TimeoutManager(default_timeout=30.0)
```

3. **Enable Circuit Breaker for External APIs**: Prevent cascading failures

```python
breaker = CircuitBreaker(
    failure_threshold=5,
    timeout=60.0
)
```

4. **Monitor Circuit Breaker State**: Know when services are down

```python
if breaker.state == CircuitState.OPEN:
    logger.error("External API is down, using fallback")
```

5. **Combine All Patterns**: For maximum reliability

```python
resilience = ResilienceConfig(
    retry_enabled=True,
    circuit_breaker_enabled=True,
    timeout_enabled=True
)
```

See the [Resilience Guide](../guides/resilience.md) for more details.
