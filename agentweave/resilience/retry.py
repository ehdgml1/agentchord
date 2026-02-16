"""Retry policy implementation."""

from __future__ import annotations

import asyncio
import random
from enum import Enum
from typing import Any, Awaitable, Callable, TypeVar

from agentweave.errors.exceptions import (
    AgentWeaveError,
    RateLimitError,
    TimeoutError,
    APIError,
)


class RetryStrategy(str, Enum):
    """Retry delay strategy."""

    FIXED = "fixed"           # Fixed delay between retries
    EXPONENTIAL = "exponential"  # Exponential backoff
    LINEAR = "linear"         # Linear increase


T = TypeVar("T")


class RetryPolicy:
    """Configurable retry policy for resilient operations.

    Supports fixed, exponential, and linear backoff strategies
    with optional jitter to prevent thundering herd.

    Example:
        >>> policy = RetryPolicy(max_retries=3, strategy=RetryStrategy.EXPONENTIAL)
        >>> result = await policy.execute(some_async_func, arg1, arg2)
    """

    # Default retryable exceptions
    DEFAULT_RETRYABLE: tuple[type[Exception], ...] = (
        RateLimitError,
        TimeoutError,
        APIError,
        ConnectionError,
        asyncio.TimeoutError,
    )

    def __init__(
        self,
        max_retries: int = 3,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        jitter_factor: float = 0.1,
        retryable_errors: tuple[type[Exception], ...] | None = None,
    ) -> None:
        """Initialize retry policy.

        Args:
            max_retries: Maximum number of retry attempts.
            strategy: Delay calculation strategy.
            base_delay: Base delay in seconds.
            max_delay: Maximum delay cap in seconds.
            jitter: Whether to add random jitter to delays.
            jitter_factor: Jitter as fraction of delay (0.0-1.0).
            retryable_errors: Exception types to retry on.
        """
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if base_delay <= 0:
            raise ValueError("base_delay must be positive")
        if max_delay < base_delay:
            raise ValueError("max_delay must be >= base_delay")

        self._max_retries = max_retries
        self._strategy = strategy
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._jitter = jitter
        self._jitter_factor = jitter_factor
        self._retryable_errors = retryable_errors or self.DEFAULT_RETRYABLE

    @property
    def max_retries(self) -> int:
        """Maximum retry attempts."""
        return self._max_retries

    @property
    def strategy(self) -> RetryStrategy:
        """Retry strategy."""
        return self._strategy

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number.

        Args:
            attempt: Attempt number (0-indexed, 0 is first retry).

        Returns:
            Delay in seconds.
        """
        if self._strategy == RetryStrategy.FIXED:
            delay = self._base_delay
        elif self._strategy == RetryStrategy.EXPONENTIAL:
            delay = self._base_delay * (2 ** attempt)
        elif self._strategy == RetryStrategy.LINEAR:
            delay = self._base_delay * (attempt + 1)
        else:
            delay = self._base_delay

        # Apply max cap
        delay = min(delay, self._max_delay)

        # Apply jitter
        if self._jitter:
            jitter_range = delay * self._jitter_factor
            delay += random.uniform(-jitter_range, jitter_range)
            delay = max(0.0, delay)  # Ensure non-negative

        return delay

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if operation should be retried.

        Args:
            error: The exception that occurred.
            attempt: Current attempt number (0-indexed).

        Returns:
            True if should retry, False otherwise.
        """
        if attempt >= self._max_retries:
            return False

        return isinstance(error, self._retryable_errors)

    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute function with retry logic.

        Args:
            func: Async function to execute.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.

        Returns:
            Result of successful execution.

        Raises:
            Exception: The last exception if all retries exhausted.
        """
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):  # +1 for initial attempt
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e

                if not self.should_retry(e, attempt):
                    raise

                if attempt < self._max_retries:
                    delay = self.get_delay(attempt)
                    await asyncio.sleep(delay)

        # Should not reach here, but satisfy type checker
        if last_error:
            raise last_error
        raise RuntimeError("Unexpected state in retry loop")
