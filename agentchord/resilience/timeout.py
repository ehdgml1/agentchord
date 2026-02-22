"""Timeout management implementation."""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, TypeVar

from agentchord.errors.exceptions import TimeoutError as AgentTimeoutError


T = TypeVar("T")


class TimeoutManager:
    """Hierarchical timeout management for LLM calls.

    Supports default timeouts with per-model overrides.

    Example:
        >>> manager = TimeoutManager(
        ...     default_timeout=60.0,
        ...     per_model_timeouts={"gpt-4": 120.0, "claude-3-opus": 180.0}
        ... )
        >>> result = await manager.execute(llm_call, model="gpt-4")
    """

    # Default timeouts for known slow models
    DEFAULT_MODEL_TIMEOUTS: dict[str, float] = {
        "gpt-4": 120.0,
        "gpt-4-turbo": 90.0,
        "claude-3-opus": 180.0,
        "claude-3-opus-20240229": 180.0,
    }

    def __init__(
        self,
        default_timeout: float = 60.0,
        per_model_timeouts: dict[str, float] | None = None,
        use_builtin_defaults: bool = True,
    ) -> None:
        """Initialize timeout manager.

        Args:
            default_timeout: Default timeout in seconds.
            per_model_timeouts: Model-specific timeout overrides.
            use_builtin_defaults: Whether to use built-in model defaults.
        """
        if default_timeout <= 0:
            raise ValueError("default_timeout must be positive")

        self._default_timeout = default_timeout
        self._per_model_timeouts: dict[str, float] = {}

        # Apply built-in defaults first
        if use_builtin_defaults:
            self._per_model_timeouts.update(self.DEFAULT_MODEL_TIMEOUTS)

        # User overrides take precedence
        if per_model_timeouts:
            self._per_model_timeouts.update(per_model_timeouts)

    @property
    def default_timeout(self) -> float:
        """Default timeout in seconds."""
        return self._default_timeout

    def get_timeout(self, model: str | None = None) -> float:
        """Get timeout for a model.

        Args:
            model: Model name (None uses default).

        Returns:
            Timeout in seconds.
        """
        if model is None:
            return self._default_timeout

        # Try exact match
        if model in self._per_model_timeouts:
            return self._per_model_timeouts[model]

        # Try prefix match for versioned models
        model_lower = model.lower()
        for known_model, timeout in self._per_model_timeouts.items():
            if model_lower.startswith(known_model.lower()):
                return timeout

        return self._default_timeout

    def set_timeout(self, model: str, timeout: float) -> None:
        """Set timeout for a specific model.

        Args:
            model: Model name.
            timeout: Timeout in seconds.
        """
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self._per_model_timeouts[model] = timeout

    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        timeout: float | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> T:
        """Execute function with timeout protection.

        Args:
            func: Async function to execute.
            *args: Positional arguments.
            timeout: Explicit timeout (overrides model timeout).
            model: Model name for timeout lookup.
            **kwargs: Keyword arguments.

        Returns:
            Result of function execution.

        Raises:
            TimeoutError: If execution times out.
        """
        effective_timeout = timeout if timeout is not None else self.get_timeout(model)

        try:
            return await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=effective_timeout,
            )
        except asyncio.TimeoutError as e:
            # Need to determine provider for the exception
            # Since we don't have provider info here, use "unknown"
            raise AgentTimeoutError(
                f"Operation timed out after {effective_timeout}s"
                + (f" for model {model}" if model else ""),
                provider="unknown",
                model=model,
                timeout_seconds=effective_timeout,
            ) from e
