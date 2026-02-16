# Resilience Guide

AgentWeave provides comprehensive resilience features to handle failures gracefully in production. This includes retry policies, circuit breakers, and timeout management.

## Quick Start

Enable resilience with automatic defaults:

```python
from agentweave import Agent
from agentweave.resilience import create_default_resilience

# Create resilience config with sensible defaults
resilience = create_default_resilience()

agent = Agent(
    name="robust_assistant",
    role="Reliable helper",
    model="gpt-4o-mini",
    resilience=resilience
)

# Retries automatically on transient failures
result = agent.run_sync("Hello")
print(result.output)
```

## Overview

AgentWeave applies resilience in this order (from outside to inside):

1. **Timeout** - Maximum time for entire operation
2. **Circuit Breaker** - Prevents cascading failures
3. **Retry** - Automatic retries with backoff
4. **Function** - Your actual API call

```
User → [Timeout → Circuit Breaker → Retry] → LLM API
```

## Retry Policy

Automatically retry transient failures with configurable backoff.

### Basic Retry

```python
from agentweave.resilience import RetryPolicy, RetryStrategy

# Simple fixed retry: 3 attempts, 1 second delay between
policy = RetryPolicy(
    max_retries=3,
    strategy=RetryStrategy.FIXED,
    base_delay=1.0
)

# Execute with retry
result = await policy.execute(some_async_func, arg1, arg2)
```

### Retry Strategies

Choose a strategy based on your use case:

#### FIXED Delay

Same delay between retries:

```python
policy = RetryPolicy(
    max_retries=3,
    strategy=RetryStrategy.FIXED,
    base_delay=2.0  # 2 seconds between retries
)
# Attempts: 0s → 2s → 4s (fixed 2s delays)
```

#### EXPONENTIAL Backoff

Exponentially increasing delay (recommended for API failures):

```python
policy = RetryPolicy(
    max_retries=4,
    strategy=RetryStrategy.EXPONENTIAL,
    base_delay=1.0,
    max_delay=60.0
)
# Attempt 1: immediate
# Attempt 2: 1s delay (1 * 2^0)
# Attempt 3: 2s delay (1 * 2^1)
# Attempt 4: 4s delay (1 * 2^2)
# Attempt 5: 8s delay (1 * 2^3)
```

#### LINEAR Backoff

Linearly increasing delay:

```python
policy = RetryPolicy(
    max_retries=3,
    strategy=RetryStrategy.LINEAR,
    base_delay=1.0
)
# Attempt 1: immediate
# Attempt 2: 1s delay (1 * 1)
# Attempt 3: 2s delay (1 * 2)
# Attempt 4: 3s delay (1 * 3)
```

### Jitter

Add randomness to prevent thundering herd:

```python
policy = RetryPolicy(
    max_retries=3,
    strategy=RetryStrategy.EXPONENTIAL,
    base_delay=1.0,
    jitter=True,  # Add random jitter
    jitter_factor=0.1  # +/- 10% of delay
)
# With jitter, delays vary slightly: 0.9s-1.1s, 1.8s-2.2s, etc.
```

### Retryable Errors

Only retry specific exceptions:

```python
from agentweave.errors.exceptions import RateLimitError, TimeoutError

policy = RetryPolicy(
    max_retries=3,
    retryable_errors=(
        RateLimitError,
        TimeoutError,
        ConnectionError,
    )
)

# This will retry on RateLimitError
# But not on ValueError or other exceptions
```

Default retryable errors:
- `RateLimitError`
- `TimeoutError`
- `APIError`
- `ConnectionError`
- `asyncio.TimeoutError`

### With Agents

```python
from agentweave import Agent
from agentweave.resilience import RetryPolicy, RetryStrategy

policy = RetryPolicy(
    max_retries=3,
    strategy=RetryStrategy.EXPONENTIAL,
    base_delay=1.0,
    max_delay=30.0,
    jitter=True
)

agent = Agent(
    name="resilient",
    role="Reliable assistant",
    model="gpt-4o-mini",
    resilience=ResilienceConfig(
        retry_enabled=True,
        retry_policy=policy
    )
)

# Automatically retries on transient failures
result = agent.run_sync("Hello")
```

## Circuit Breaker

Prevent cascading failures when a service is down.

### How It Works

Circuit breaker has three states:

```
CLOSED (normal) → OPEN (stop calling) → HALF_OPEN (test) → CLOSED
       ↓                    ↓                  ↓
    working          too many failures     recoverable?
```

### Basic Circuit Breaker

```python
from agentweave.resilience import CircuitBreaker

breaker = CircuitBreaker(
    failure_threshold=5,      # Open after 5 failures
    success_threshold=2,      # Close after 2 successes
    timeout=60.0              # Try again after 60 seconds
)

# Attempt calls - if too many fail, circuit opens
try:
    result = await breaker.execute(llm_api_call)
except CircuitBreakerOpenError:
    # Service is down, use fallback
    result = "Service temporarily unavailable"
```

### State Transitions

```python
breaker = CircuitBreaker(
    failure_threshold=3,    # Open after 3 failures
    success_threshold=2,    # Close after 2 successes
    timeout=30.0            # Check recovery after 30s
)

# CLOSED state: Normal operation
await breaker.execute(api_call)  # Works fine

# After 3 failures -> OPEN state
await breaker.execute(api_call)  # Fails immediately with CircuitBreakerOpenError

# Wait 30 seconds -> HALF_OPEN state
# Try again - if 2 successes -> CLOSED (back to normal)
# If 1 failure -> OPEN again (circuit opens again)
```

### Properties

```python
print(breaker.state)              # "CLOSED", "OPEN", or "HALF_OPEN"
print(breaker.failure_count)      # Number of failures since reset
print(breaker.success_count)      # Number of successes in HALF_OPEN
```

### With Agents

```python
from agentweave import Agent
from agentweave.resilience import ResilienceConfig, CircuitBreaker

breaker = CircuitBreaker(
    failure_threshold=5,
    success_threshold=3,
    timeout=60.0
)

agent = Agent(
    name="circuit_breaker_agent",
    role="Assistant",
    model="gpt-4o-mini",
    resilience=ResilienceConfig(
        circuit_breaker_enabled=True,
        circuit_breaker=breaker
    )
)
```

## Timeout Management

Prevent requests from hanging indefinitely.

### Basic Timeout

```python
from agentweave.resilience import TimeoutManager

manager = TimeoutManager(default_timeout=30.0)  # 30 seconds

result = await manager.execute(llm_api_call)
```

### Model-Specific Timeouts

Different timeouts for different models:

```python
manager = TimeoutManager(
    default_timeout=60.0,
    per_model_timeouts={
        "gpt-4o": 120.0,           # GPT-4O gets 2 minutes
        "gpt-4o-mini": 30.0,       # GPT-4O mini gets 30 seconds
        "ollama/llama3.2": 300.0,  # Local model gets 5 minutes
    }
)

# Timeout automatically selected based on model
result = await manager.execute(llm_api_call, model="gpt-4o")
```

### With Agents

```python
from agentweave import Agent
from agentweave.resilience import ResilienceConfig, TimeoutManager

timeout_manager = TimeoutManager(
    default_timeout=60.0,
    per_model_timeouts={
        "gpt-4o": 120.0,
        "gpt-4o-mini": 30.0,
    }
)

agent = Agent(
    name="fast_agent",
    role="Quick responder",
    model="gpt-4o-mini",
    resilience=ResilienceConfig(
        timeout_enabled=True,
        timeout_manager=timeout_manager
    )
)
```

## ResilienceConfig

Combine all resilience features into one config:

### All Three Layers

```python
from agentweave.resilience import (
    ResilienceConfig,
    RetryPolicy,
    RetryStrategy,
    CircuitBreaker,
    TimeoutManager
)

config = ResilienceConfig(
    # Retry configuration
    retry_enabled=True,
    retry_policy=RetryPolicy(
        max_retries=3,
        strategy=RetryStrategy.EXPONENTIAL,
        base_delay=1.0,
        max_delay=30.0
    ),

    # Circuit breaker configuration
    circuit_breaker_enabled=True,
    circuit_breaker=CircuitBreaker(
        failure_threshold=5,
        success_threshold=2,
        timeout=60.0
    ),

    # Timeout configuration
    timeout_enabled=True,
    timeout_manager=TimeoutManager(
        default_timeout=60.0,
        per_model_timeouts={
            "gpt-4o": 120.0,
            "gpt-4o-mini": 30.0,
        }
    )
)

agent = Agent(
    name="super_resilient",
    role="Bulletproof assistant",
    model="gpt-4o-mini",
    resilience=config
)
```

### Execute with ResilienceConfig

```python
# Method 1: Use agent (automatic)
result = agent.run_sync("Hello")

# Method 2: Use config directly
result = await config.execute(llm_api_call, model="gpt-4o")
```

### Wrap Functions

```python
# Wrap a function with resilience
wrapped_func = config.wrap(my_async_function, model="gpt-4o")

# Use wrapped function
result = await wrapped_func(arg1, arg2)
```

### Default Configuration

Pre-configured with sensible defaults:

```python
from agentweave.resilience import create_default_resilience

config = create_default_resilience()
# Provides:
# - 3 retries with exponential backoff
# - 60 second timeout
# - No circuit breaker (disabled by default)

agent = Agent(
    name="assistant",
    role="Helper",
    model="gpt-4o-mini",
    resilience=config
)
```

## Execution Order

Understanding the execution stack:

```python
# With this configuration:
config = ResilienceConfig(
    retry_enabled=True,
    circuit_breaker_enabled=True,
    timeout_enabled=True
)

# Execution flows like this:
async def execute(func):
    try:
        # Layer 3: Timeout (outermost)
        async with asyncio.timeout(60):
            # Layer 2: Circuit breaker
            if breaker.is_open():
                raise CircuitBreakerOpenError()

            # Layer 1: Retry (innermost)
            for attempt in range(max_retries + 1):
                try:
                    # Layer 0: Actual function
                    return await func()
                except Exception as e:
                    if not should_retry(e):
                        raise
                    await asyncio.sleep(delay)
    except asyncio.TimeoutError:
        # Caught by timeout layer
        pass
```

## Error Handling

Different errors behave differently:

```python
from agentweave.errors.exceptions import (
    RateLimitError,      # Retried
    TimeoutError,        # Retried
    APIError,            # Retried
    AuthenticationError, # NOT retried
    ModelNotFoundError   # NOT retried
)

# This will retry:
try:
    await agent.run_sync("Hello")
except RateLimitError:
    pass  # Retried automatically

# This won't retry (fails immediately):
try:
    await agent.run_sync("Hello")
except AuthenticationError:
    pass  # Failed immediately, not retried
```

## Monitoring and Debugging

### Check Retry Behavior

```python
policy = RetryPolicy(max_retries=3)

# Check configuration
print(f"Max retries: {policy.max_retries}")
print(f"Strategy: {policy.strategy}")
print(f"Base delay: {policy.base_delay}s")

# Check delay calculation
for attempt in range(3):
    delay = policy.get_delay(attempt)
    print(f"Attempt {attempt}: {delay:.1f}s delay")
```

### Check Circuit Breaker Status

```python
breaker = CircuitBreaker(failure_threshold=3)

# Monitor state
print(f"State: {breaker.state}")
print(f"Failures: {breaker.failure_count}")
print(f"Successes: {breaker.success_count}")

# Check if calls would be blocked
if breaker.state == "OPEN":
    print("Circuit is open - calls blocked")
```

### Logging

AgentWeave logs resilience events:

```python
import logging

# Enable logging to see retry/circuit breaker events
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("agentweave.resilience")

# Now you'll see retry attempts, circuit breaker state changes, etc.
result = agent.run_sync("Hello")
```

## Best Practices

### 1. Use Default Config for Most Cases

```python
from agentweave.resilience import create_default_resilience

# Good: sensible defaults
config = create_default_resilience()
agent = Agent(..., resilience=config)

# Don't: over-engineering
config = ResilienceConfig(
    retry_enabled=True,
    retry_policy=RetryPolicy(max_retries=10, strategy=RetryStrategy.FIXED),
    circuit_breaker_enabled=True,
    circuit_breaker=CircuitBreaker(failure_threshold=1),
    timeout_enabled=True,
    timeout_manager=TimeoutManager(default_timeout=5)
)
```

### 2. Match Timeouts to Model Speed

```python
manager = TimeoutManager(
    default_timeout=60.0,
    per_model_timeouts={
        "gpt-4o": 120.0,           # Slower
        "gpt-4o-mini": 30.0,       # Faster
        "ollama/llama3.2": 300.0,  # Local, potentially slow
    }
)
```

### 3. Exponential Backoff for APIs

```python
# Good: exponential backoff for API rate limits
policy = RetryPolicy(
    max_retries=4,
    strategy=RetryStrategy.EXPONENTIAL,
    base_delay=1.0
)

# Bad: fixed or linear for APIs (hammers when rate-limited)
policy = RetryPolicy(
    max_retries=4,
    strategy=RetryStrategy.FIXED,
    base_delay=1.0
)
```

### 4. Circuit Breaker for External Services

```python
# Good: circuit breaker prevents cascading failures
config = ResilienceConfig(
    circuit_breaker_enabled=True,
    circuit_breaker=CircuitBreaker(
        failure_threshold=5,
        timeout=60.0
    )
)

# Bad: without circuit breaker, continuously hammers failing service
config = ResilienceConfig(
    circuit_breaker_enabled=False
)
```

### 5. Log Failures for Debugging

```python
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

agent = Agent(..., resilience=create_default_resilience())

try:
    result = agent.run_sync("Hello")
except Exception as e:
    # Logs will show retry attempts, timeouts, etc.
    logging.error(f"Final failure: {e}")
```

## Complete Example

```python
from agentweave import Agent
from agentweave.resilience import (
    ResilienceConfig,
    RetryPolicy,
    RetryStrategy,
    CircuitBreaker,
    TimeoutManager,
)
import asyncio

async def main():
    # Configure resilience
    config = ResilienceConfig(
        # Retry on transient errors
        retry_enabled=True,
        retry_policy=RetryPolicy(
            max_retries=3,
            strategy=RetryStrategy.EXPONENTIAL,
            base_delay=1.0,
            max_delay=30.0,
            jitter=True
        ),

        # Prevent cascading failures
        circuit_breaker_enabled=True,
        circuit_breaker=CircuitBreaker(
            failure_threshold=5,
            success_threshold=2,
            timeout=60.0
        ),

        # Prevent hanging requests
        timeout_enabled=True,
        timeout_manager=TimeoutManager(
            default_timeout=60.0,
            per_model_timeouts={
                "gpt-4o": 120.0,
                "gpt-4o-mini": 30.0,
            }
        )
    )

    # Create resilient agent
    agent = Agent(
        name="resilient_assistant",
        role="Reliable helper",
        model="gpt-4o-mini",
        resilience=config
    )

    # This call will retry on failure, timeout after 30s,
    # and use circuit breaker to prevent cascading failures
    try:
        result = agent.run_sync("Explain resilience in 2 sentences")
        print(f"Success: {result.output}")
    except Exception as e:
        print(f"Failed after retries: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

## See Also

- [Providers Guide](providers.md) - Use resilience with different providers
- [Tools Guide](tools.md) - Apply resilience to tool calls
- [Agent Documentation](../api/core.md) - Agent API details
