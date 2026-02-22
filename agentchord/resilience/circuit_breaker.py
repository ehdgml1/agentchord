"""Circuit breaker pattern implementation."""

from __future__ import annotations

import asyncio
import time
from enum import Enum
from typing import Any, Awaitable, Callable, TypeVar

from agentchord.errors.exceptions import AgentChordError


class CircuitOpenError(AgentChordError):
    """Raised when circuit is open and request is rejected."""

    def __init__(
        self,
        message: str = "Circuit breaker is open",
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"      # Normal operation, requests allowed
    OPEN = "open"          # Failure mode, requests rejected
    HALF_OPEN = "half_open"  # Testing mode, limited requests


T = TypeVar("T")


class CircuitBreaker:
    """Circuit breaker pattern for fault tolerance.

    Protects against cascading failures by tracking failures
    and temporarily blocking requests when threshold is reached.

    States:
        - CLOSED: Normal operation, requests pass through
        - OPEN: Too many failures, requests rejected immediately
        - HALF_OPEN: Testing if service recovered

    Example:
        >>> breaker = CircuitBreaker(failure_threshold=5, timeout=30)
        >>> try:
        ...     result = await breaker.execute(some_api_call)
        ... except CircuitOpenError:
        ...     # Circuit is open, use fallback
        ...     result = fallback_value
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: float = 30.0,
        excluded_exceptions: tuple[type[Exception], ...] = (),
    ) -> None:
        """Initialize circuit breaker.

        Args:
            failure_threshold: Failures needed to open circuit.
            success_threshold: Successes needed to close circuit from half-open.
            timeout: Seconds to wait before transitioning from open to half-open.
            excluded_exceptions: Exceptions that don't count as failures.
        """
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if success_threshold < 1:
            raise ValueError("success_threshold must be at least 1")
        if timeout <= 0:
            raise ValueError("timeout must be positive")

        self._failure_threshold = failure_threshold
        self._success_threshold = success_threshold
        self._timeout = timeout
        self._excluded_exceptions = excluded_exceptions

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Current circuit state."""
        self._check_state_transition()
        return self._state

    @property
    def failure_count(self) -> int:
        """Current failure count."""
        return self._failure_count

    @property
    def is_closed(self) -> bool:
        """Check if circuit allows requests."""
        return self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def record_success(self) -> None:
        """Record a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._success_threshold:
                self._close()
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            self._failure_count = 0

    def record_failure(self, error: Exception) -> None:
        """Record a failed call.

        Args:
            error: The exception that occurred.
        """
        # Don't count excluded exceptions
        if isinstance(error, self._excluded_exceptions):
            return

        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            # Any failure in half-open goes back to open
            self._open()
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self._failure_threshold:
                self._open()

    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute function with circuit breaker protection.

        Args:
            func: Async function to execute.
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            Result of function execution.

        Raises:
            CircuitOpenError: If circuit is open.
        """
        async with self._lock:
            self._check_state_transition()

            if self._state == CircuitState.OPEN:
                retry_after = self._get_retry_after()
                raise CircuitOpenError(
                    f"Circuit breaker is open. Retry after {retry_after:.1f}s",
                    retry_after=retry_after,
                )

        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure(e)
            raise

    def reset(self) -> None:
        """Manually reset circuit to closed state."""
        self._close()

    def _open(self) -> None:
        """Transition to open state."""
        self._state = CircuitState.OPEN
        self._success_count = 0

    def _close(self) -> None:
        """Transition to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None

    def _half_open(self) -> None:
        """Transition to half-open state."""
        self._state = CircuitState.HALF_OPEN
        self._success_count = 0

    def _check_state_transition(self) -> None:
        """Check if state should transition."""
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._half_open()

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self._last_failure_time is None:
            return True
        elapsed = time.monotonic() - self._last_failure_time
        return elapsed >= self._timeout

    def _get_retry_after(self) -> float:
        """Get seconds until circuit might close."""
        if self._last_failure_time is None:
            return 0.0
        elapsed = time.monotonic() - self._last_failure_time
        return max(0.0, self._timeout - elapsed)
