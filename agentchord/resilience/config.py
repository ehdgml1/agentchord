"""Resilience configuration and integration."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, TypeVar

from pydantic import BaseModel, ConfigDict

from agentchord.resilience.retry import RetryPolicy
from agentchord.resilience.circuit_breaker import CircuitBreaker
from agentchord.resilience.timeout import TimeoutManager


T = TypeVar("T")


class ResilienceConfig(BaseModel):
    """Unified resilience configuration.

    Combines retry, circuit breaker, and timeout management
    into a single configuration object.

    Example:
        >>> config = ResilienceConfig(
        ...     retry_enabled=True,
        ...     retry_policy=RetryPolicy(max_retries=3),
        ...     circuit_breaker_enabled=True,
        ...     circuit_breaker=CircuitBreaker(failure_threshold=5),
        ...     timeout_manager=TimeoutManager(default_timeout=60),
        ... )
        >>> result = await config.execute(llm_call, model="gpt-4")
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Retry settings
    retry_enabled: bool = True
    retry_policy: RetryPolicy | None = None

    # Circuit breaker settings
    circuit_breaker_enabled: bool = False
    circuit_breaker: CircuitBreaker | None = None

    # Timeout settings
    timeout_enabled: bool = True
    timeout_manager: TimeoutManager | None = None

    def get_retry_policy(self) -> RetryPolicy | None:
        """Get retry policy if enabled."""
        if not self.retry_enabled:
            return None
        return self.retry_policy or RetryPolicy()

    def get_circuit_breaker(self) -> CircuitBreaker | None:
        """Get circuit breaker if enabled."""
        if not self.circuit_breaker_enabled:
            return None
        return self.circuit_breaker or CircuitBreaker()

    def get_timeout_manager(self) -> TimeoutManager | None:
        """Get timeout manager if enabled."""
        if not self.timeout_enabled:
            return None
        return self.timeout_manager or TimeoutManager()

    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        model: str | None = None,
        **kwargs: Any,
    ) -> T:
        """Execute function with all resilience layers.

        Execution order:
        1. Timeout (outermost)
        2. Circuit breaker
        3. Retry (innermost)
        4. Actual function

        Args:
            func: Async function to execute.
            *args: Positional arguments.
            model: Model name (for timeout lookup).
            **kwargs: Keyword arguments.

        Returns:
            Result of function execution.
        """
        # Build execution chain from inside out
        # Use default argument to capture closure variables properly
        current_func = func

        # Layer 1: Retry (innermost)
        retry_policy = self.get_retry_policy()
        if retry_policy:
            def make_retry_wrapper(
                policy: RetryPolicy,
                inner: Callable[..., Awaitable[T]],
            ) -> Callable[..., Awaitable[T]]:
                async def with_retry(*a: Any, **kw: Any) -> T:
                    return await policy.execute(inner, *a, **kw)
                return with_retry
            current_func = make_retry_wrapper(retry_policy, current_func)

        # Layer 2: Circuit breaker
        circuit_breaker = self.get_circuit_breaker()
        if circuit_breaker:
            def make_cb_wrapper(
                cb: CircuitBreaker,
                inner: Callable[..., Awaitable[T]],
            ) -> Callable[..., Awaitable[T]]:
                async def with_circuit_breaker(*a: Any, **kw: Any) -> T:
                    return await cb.execute(inner, *a, **kw)
                return with_circuit_breaker
            current_func = make_cb_wrapper(circuit_breaker, current_func)

        # Layer 3: Timeout (outermost)
        timeout_manager = self.get_timeout_manager()
        if timeout_manager:
            def make_timeout_wrapper(
                tm: TimeoutManager,
                inner: Callable[..., Awaitable[T]],
                mdl: str | None,
            ) -> Callable[..., Awaitable[T]]:
                async def with_timeout(*a: Any, **kw: Any) -> T:
                    return await tm.execute(inner, *a, model=mdl, **kw)
                return with_timeout
            current_func = make_timeout_wrapper(timeout_manager, current_func, model)

        return await current_func(*args, **kwargs)

    def wrap(
        self,
        func: Callable[..., Awaitable[T]],
        model: str | None = None,
    ) -> Callable[..., Awaitable[T]]:
        """Wrap a function with resilience layers.

        Args:
            func: Async function to wrap.
            model: Model name for timeout lookup.

        Returns:
            Wrapped function with resilience.
        """
        async def wrapped(*args: Any, **kwargs: Any) -> T:
            return await self.execute(func, *args, model=model, **kwargs)
        return wrapped


# Convenience function
def create_default_resilience() -> ResilienceConfig:
    """Create resilience config with sensible defaults.

    Returns:
        ResilienceConfig with retry (3 attempts, exponential backoff)
        and timeout (60s default) enabled.
    """
    return ResilienceConfig(
        retry_enabled=True,
        retry_policy=RetryPolicy(max_retries=3),
        timeout_enabled=True,
        timeout_manager=TimeoutManager(default_timeout=60.0),
    )
