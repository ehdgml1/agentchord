# Errors API Reference

Complete API reference for all exception types in AgentWeave.

All exceptions inherit from `AgentWeaveError` and include a `retryable` flag to indicate if the operation can be retried.

## AgentWeaveError

Base exception for all AgentWeave errors.

```python
from agentweave.errors import AgentWeaveError

try:
    result = await agent.run("Hello")
except AgentWeaveError as e:
    print(f"AgentWeave error: {e}")
    if e.retryable:
        print("This error can be retried")
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `message` | `str` | Error message |
| `retryable` | `bool` | True if operation can be retried |

## Configuration Errors

Errors related to configuration and setup.

### ConfigurationError

Base class for configuration errors.

```python
from agentweave.errors import ConfigurationError

try:
    agent = Agent(name="test", role="test", model="invalid")
except ConfigurationError as e:
    print(f"Configuration error: {e}")
```

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `retryable` | `bool` | Always False |

### MissingAPIKeyError

API key is missing or not configured.

```python
from agentweave.errors import MissingAPIKeyError

try:
    provider = OpenAIProvider(model="gpt-4o", api_key=None)
except MissingAPIKeyError as e:
    print(f"Missing API key: {e.provider}")
    print(f"Set {e.provider.upper()}_API_KEY environment variable")
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `provider` | `str` | Provider name (openai, anthropic, etc.) |
| `retryable` | `bool` | False |

**Example:**

```python
import os
from agentweave.errors import MissingAPIKeyError

# Set environment variable
os.environ["OPENAI_API_KEY"] = "sk-..."

# Try again
provider = OpenAIProvider(model="gpt-4o")
```

### InvalidConfigError

Invalid configuration value.

```python
from agentweave.errors import InvalidConfigError

try:
    config = AgentConfig(
        model="gpt-4o",
        temperature=3.0  # Invalid: must be 0.0-2.0
    )
except InvalidConfigError as e:
    print(f"Invalid config: {e.field}")
    print(f"Value: {e.value}")
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `field` | `str` | Configuration field name |
| `value` | `object` | Invalid value |
| `retryable` | `bool` | False |

## LLM Errors

Errors from LLM providers.

### LLMError

Base class for LLM-related errors.

```python
from agentweave.errors import LLMError

try:
    response = await provider.complete(messages)
except LLMError as e:
    print(f"LLM error from {e.provider}: {e}")
    print(f"Model: {e.model}")
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `provider` | `str` | Provider name (openai, anthropic, etc.) |
| `model` | `str \| None` | Model name if available |
| `retryable` | `bool` | Depends on specific error |

### RateLimitError

Rate limit exceeded. Can be retried after backoff.

```python
from agentweave.errors import RateLimitError
import asyncio

try:
    response = await provider.complete(messages)
except RateLimitError as e:
    print(f"Rate limited by {e.provider}")
    if e.retry_after:
        print(f"Wait {e.retry_after} seconds before retrying")
        await asyncio.sleep(e.retry_after)
        response = await provider.complete(messages)
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `provider` | `str` | Provider name |
| `model` | `str \| None` | Model name |
| `retry_after` | `float \| None` | Seconds to wait before retry |
| `retryable` | `bool` | Always True |

### AuthenticationError

Authentication failed. Cannot be retried without fixing credentials.

```python
from agentweave.errors import AuthenticationError

try:
    provider = OpenAIProvider(model="gpt-4o", api_key="invalid-key")
    response = await provider.complete(messages)
except AuthenticationError as e:
    print(f"Auth failed for {e.provider}")
    print("Check your API key and permissions")
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `provider` | `str` | Provider name |
| `retryable` | `bool` | Always False |

### APIError

General API error. May be retried.

```python
from agentweave.errors import APIError

try:
    response = await provider.complete(messages)
except APIError as e:
    print(f"API error: {e}")
    print(f"Status code: {e.status_code}")
    if e.retryable:
        # Retry with backoff
        response = await retry_policy.execute(provider.complete, messages)
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `provider` | `str` | Provider name |
| `model` | `str \| None` | Model name |
| `status_code` | `int \| None` | HTTP status code |
| `retryable` | `bool` | True for 5xx errors, False for 4xx |

### TimeoutError

Request timed out. Can be retried.

```python
from agentweave.errors import TimeoutError

try:
    response = await provider.complete(messages, timeout=5.0)
except TimeoutError as e:
    print(f"Timeout from {e.provider}")
    print(f"Waited {e.timeout_seconds} seconds")
    # Retry with longer timeout
    response = await provider.complete(messages, timeout=30.0)
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `provider` | `str` | Provider name |
| `model` | `str \| None` | Model name |
| `timeout_seconds` | `float` | Timeout that was exceeded |
| `retryable` | `bool` | Always True |

### ModelNotFoundError

Model not found or not supported.

```python
from agentweave.errors import ModelNotFoundError

try:
    provider = OpenAIProvider(model="gpt-999")  # Doesn't exist
except ModelNotFoundError as e:
    print(f"Model not found: {e.model}")
    print(f"Provider: {e.provider}")
    print("Use a valid model name")
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `model` | `str` | Invalid model name |
| `provider` | `str \| None` | Provider name |
| `retryable` | `bool` | Always False |

## Agent Errors

Errors related to agent execution.

### AgentError

Base class for agent-related errors.

```python
from agentweave.errors import AgentError

try:
    result = await agent.run("Hello")
except AgentError as e:
    print(f"Agent error: {e}")
    print(f"Agent: {e.agent_name}")
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `agent_name` | `str` | Name of agent that failed |
| `retryable` | `bool` | Depends on specific error |

### AgentExecutionError

Error during agent execution.

```python
from agentweave.errors import AgentExecutionError

try:
    result = await agent.run("Hello")
except AgentExecutionError as e:
    print(f"Execution failed for {e.agent_name}")
    print(f"Error: {e}")
    if e.retryable:
        result = await agent.run("Hello")  # Retry
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `agent_name` | `str` | Agent name |
| `retryable` | `bool` | Always True |

### AgentTimeoutError

Agent execution timed out.

```python
from agentweave.errors import AgentTimeoutError

try:
    result = await agent.run("Complex query")
except AgentTimeoutError as e:
    print(f"Agent {e.agent_name} timed out")
    print(f"Timeout: {e.timeout_seconds}s")

    # Retry with longer timeout
    agent_with_longer_timeout = Agent(
        name=agent.name,
        role=agent.role,
        timeout=e.timeout_seconds * 2
    )
    result = await agent_with_longer_timeout.run("Complex query")
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `agent_name` | `str` | Agent name |
| `timeout_seconds` | `float` | Timeout that was exceeded |
| `retryable` | `bool` | Always True |

## Cost Errors

### CostLimitExceededError

Cost limit exceeded.

```python
from agentweave.errors import CostLimitExceededError

tracker = CostTracker(budget_limit=5.0, raise_on_exceed=True)

try:
    result = await agent.run("Expensive operation")
except CostLimitExceededError as e:
    print(f"Budget limit exceeded!")
    print(f"Limit: ${e.limit:.2f}")
    print(f"Current: ${e.current_cost:.2f}")
    print(f"Agent: {e.agent_name}")
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `current_cost` | `float` | Current cost in USD |
| `limit` | `float` | Budget limit in USD |
| `agent_name` | `str \| None` | Agent that exceeded budget |
| `retryable` | `bool` | Always False |

## Workflow Errors

Errors related to workflow execution.

### WorkflowError

Base class for workflow-related errors.

```python
from agentweave.errors import WorkflowError

try:
    result = await workflow.run("Input")
except WorkflowError as e:
    print(f"Workflow error: {e}")
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `retryable` | `bool` | Depends on specific error |

### InvalidFlowError

Invalid flow DSL syntax.

```python
from agentweave.errors import InvalidFlowError

try:
    executor = SequentialExecutor(["agent1", "agent2"])
    workflow = Workflow(
        agents={"agent1": a1, "agent2": a2},
        executor=executor
    )
except InvalidFlowError as e:
    print(f"Invalid flow: {e.flow}")
    print(f"Reason: {e.reason}")
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `flow` | `str` | Flow DSL string |
| `reason` | `str` | Why it's invalid |
| `retryable` | `bool` | Always False |

### AgentNotFoundInFlowError

Agent referenced in flow does not exist.

```python
from agentweave.errors import AgentNotFoundInFlowError

try:
    executor = SequentialExecutor(["researcher", "writer"])
    workflow = Workflow(
        agents={"researcher": agent},  # Missing "writer"
        executor=executor
    )
except AgentNotFoundInFlowError as e:
    print(f"Agent not found: {e.agent_name}")
    print(f"Available: {e.available}")
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `agent_name` | `str` | Missing agent name |
| `available` | `list[str]` | Available agent names |
| `retryable` | `bool` | Always False |

### WorkflowExecutionError

Error during workflow execution.

```python
from agentweave.errors import WorkflowExecutionError

try:
    result = await workflow.run("Input")
except WorkflowExecutionError as e:
    print(f"Workflow failed: {e}")
    print(f"Failed agent: {e.failed_agent}")
    print(f"Step: {e.step_index}")
    if e.retryable:
        result = await workflow.run("Input")  # Retry
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `failed_agent` | `str \| None` | Agent that failed |
| `step_index` | `int \| None` | Step index where failure occurred |
| `retryable` | `bool` | Always True |

### EmptyWorkflowError

Workflow has no agents or steps defined.

```python
from agentweave.errors import EmptyWorkflowError

try:
    workflow = Workflow(agents={}, executor=executor)
    result = await workflow.run("Input")
except EmptyWorkflowError as e:
    print(f"Workflow is empty")
    print("Add agents before running")
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `retryable` | `bool` | Always False |

## Resilience Errors

### CircuitOpenError

Raised when circuit breaker is open and request is rejected.

```python
from agentweave.resilience import CircuitBreaker, CircuitOpenError

breaker = CircuitBreaker(failure_threshold=5, timeout=30.0)

try:
    result = await breaker.execute(api_call)
except CircuitOpenError as e:
    print(f"Circuit is open")
    if e.retry_after:
        print(f"Retry after {e.retry_after}s")
    # Use fallback
    result = fallback_value
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `message` | `str` | Error message |
| `retry_after` | `float \| None` | Seconds to wait before retry |

## Error Handling Best Practices

### 1. Catch Specific Errors

```python
from agentweave.errors import (
    RateLimitError,
    AuthenticationError,
    APIError,
    AgentTimeoutError
)

try:
    result = await agent.run("Hello")
except RateLimitError as e:
    print(f"Rate limited, wait {e.retry_after}s")
except AuthenticationError:
    print("Check your API key")
except APIError as e:
    print(f"API error: {e.status_code}")
except AgentTimeoutError as e:
    print(f"Timeout: {e.timeout_seconds}s")
```

### 2. Use Retryable Flag

```python
from agentweave.errors import AgentWeaveError

try:
    result = await agent.run("Hello")
except AgentWeaveError as e:
    if e.retryable:
        # Safe to retry
        result = await agent.run("Hello")
    else:
        # Don't retry, fix the issue
        raise
```

### 3. Combine with Resilience Patterns

```python
from agentweave.resilience import RetryPolicy, RetryStrategy
from agentweave.errors import APIError

policy = RetryPolicy(
    max_retries=3,
    strategy=RetryStrategy.EXPONENTIAL,
    retryable_errors=(APIError, TimeoutError)
)

result = await policy.execute(agent.run, "Hello")
```

### 4. Log and Monitor Errors

```python
import logging
from agentweave.errors import AgentWeaveError

logger = logging.getLogger(__name__)

try:
    result = await agent.run("Hello")
except AgentWeaveError as e:
    logger.error(
        f"AgentWeave error: {e}",
        extra={
            "error_type": type(e).__name__,
            "retryable": e.retryable
        }
    )
```

See complete error handling in [Core API](./core.md) documentation.
