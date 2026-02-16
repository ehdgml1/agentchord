"""Unit tests for Resilience module."""

from __future__ import annotations

import asyncio
import time

import pytest

from agentweave.resilience.retry import RetryPolicy, RetryStrategy
from agentweave.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitOpenError,
)
from agentweave.resilience.timeout import TimeoutManager
from agentweave.resilience.config import ResilienceConfig, create_default_resilience
from agentweave.errors.exceptions import RateLimitError, TimeoutError


class TestRetryPolicy:
    """Tests for RetryPolicy."""

    def test_fixed_delay(self) -> None:
        """Fixed strategy should return constant delay."""
        policy = RetryPolicy(
            strategy=RetryStrategy.FIXED,
            base_delay=1.0,
            jitter=False,
        )

        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 1.0
        assert policy.get_delay(2) == 1.0

    def test_exponential_delay(self) -> None:
        """Exponential strategy should double delay."""
        policy = RetryPolicy(
            strategy=RetryStrategy.EXPONENTIAL,
            base_delay=1.0,
            max_delay=100.0,
            jitter=False,
        )

        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 4.0

    def test_linear_delay(self) -> None:
        """Linear strategy should increase linearly."""
        policy = RetryPolicy(
            strategy=RetryStrategy.LINEAR,
            base_delay=1.0,
            max_delay=100.0,
            jitter=False,
        )

        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 3.0

    def test_max_delay_cap(self) -> None:
        """Should cap delay at max_delay."""
        policy = RetryPolicy(
            strategy=RetryStrategy.EXPONENTIAL,
            base_delay=1.0,
            max_delay=5.0,
            jitter=False,
        )

        assert policy.get_delay(10) == 5.0

    def test_should_retry_on_retryable_error(self) -> None:
        """Should retry on retryable errors."""
        policy = RetryPolicy(max_retries=3)

        assert policy.should_retry(RateLimitError("rate limit", provider="openai"), 0) is True
        assert policy.should_retry(RateLimitError("rate limit", provider="openai"), 2) is True
        assert policy.should_retry(RateLimitError("rate limit", provider="openai"), 3) is False

    def test_should_not_retry_on_other_error(self) -> None:
        """Should not retry on non-retryable errors."""
        policy = RetryPolicy(max_retries=3)

        assert policy.should_retry(ValueError("bad value"), 0) is False

    @pytest.mark.asyncio
    async def test_execute_success(self) -> None:
        """Should return result on success."""
        policy = RetryPolicy(max_retries=3)

        async def success() -> str:
            return "ok"

        result = await policy.execute(success)

        assert result == "ok"

    @pytest.mark.asyncio
    async def test_execute_retry_then_success(self) -> None:
        """Should retry and eventually succeed."""
        policy = RetryPolicy(max_retries=3, base_delay=0.01, jitter=False)
        attempts = [0]

        async def fail_twice() -> str:
            attempts[0] += 1
            if attempts[0] < 3:
                raise RateLimitError("retry", provider="openai")
            return "ok"

        result = await policy.execute(fail_twice)

        assert result == "ok"
        assert attempts[0] == 3


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    def test_initial_state_closed(self) -> None:
        """Should start in closed state."""
        breaker = CircuitBreaker()

        assert breaker.state == CircuitState.CLOSED

    def test_opens_after_failures(self) -> None:
        """Should open after failure threshold."""
        breaker = CircuitBreaker(failure_threshold=3)

        for _ in range(3):
            breaker.record_failure(Exception("fail"))

        assert breaker.state == CircuitState.OPEN

    def test_success_resets_failure_count(self) -> None:
        """Success should reset failure count in closed state."""
        breaker = CircuitBreaker(failure_threshold=3)

        breaker.record_failure(Exception("fail"))
        breaker.record_failure(Exception("fail"))
        breaker.record_success()

        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_rejects_when_open(self) -> None:
        """Should reject requests when open."""
        breaker = CircuitBreaker(failure_threshold=1, timeout=10.0)
        breaker.record_failure(Exception("fail"))

        async def func() -> str:
            return "ok"

        with pytest.raises(CircuitOpenError):
            await breaker.execute(func)

    def test_half_open_after_timeout(self) -> None:
        """Should transition to half-open after timeout."""
        breaker = CircuitBreaker(failure_threshold=1, timeout=0.1)
        breaker.record_failure(Exception("fail"))

        assert breaker.state == CircuitState.OPEN

        time.sleep(0.15)

        assert breaker.state == CircuitState.HALF_OPEN


class TestTimeoutManager:
    """Tests for TimeoutManager."""

    def test_default_timeout(self) -> None:
        """Should return default timeout."""
        manager = TimeoutManager(default_timeout=30.0)

        assert manager.get_timeout() == 30.0
        assert manager.get_timeout("unknown-model") == 30.0

    def test_model_specific_timeout(self) -> None:
        """Should return model-specific timeout."""
        manager = TimeoutManager(
            default_timeout=30.0,
            per_model_timeouts={"gpt-4": 120.0},
        )

        assert manager.get_timeout("gpt-4") == 120.0

    def test_builtin_defaults(self) -> None:
        """Should use builtin defaults for slow models."""
        manager = TimeoutManager(use_builtin_defaults=True)

        assert manager.get_timeout("claude-3-opus") == 180.0

    @pytest.mark.asyncio
    async def test_execute_success(self) -> None:
        """Should return result within timeout."""
        manager = TimeoutManager(default_timeout=1.0)

        async def quick() -> str:
            return "ok"

        result = await manager.execute(quick)

        assert result == "ok"

    @pytest.mark.asyncio
    async def test_execute_timeout(self) -> None:
        """Should raise on timeout."""
        manager = TimeoutManager(default_timeout=0.1)

        async def slow() -> str:
            await asyncio.sleep(1.0)
            return "ok"

        with pytest.raises(TimeoutError):
            await manager.execute(slow)


class TestResilienceConfig:
    """Tests for ResilienceConfig."""

    def test_create_default_resilience(self) -> None:
        """Should create config with defaults."""
        config = create_default_resilience()

        assert config.retry_enabled is True
        assert config.timeout_enabled is True
        assert config.circuit_breaker_enabled is False

    @pytest.mark.asyncio
    async def test_execute_with_all_layers(self) -> None:
        """Should execute through all layers."""
        config = ResilienceConfig(
            retry_enabled=True,
            retry_policy=RetryPolicy(max_retries=1, base_delay=0.01),
            timeout_enabled=True,
            timeout_manager=TimeoutManager(default_timeout=1.0),
        )

        async def success() -> str:
            return "ok"

        result = await config.execute(success)

        assert result == "ok"

    def test_wrap_function(self) -> None:
        """Should wrap function with resilience."""
        config = create_default_resilience()

        async def func() -> str:
            return "ok"

        wrapped = config.wrap(func)

        assert callable(wrapped)

    def test_disabled_layers(self) -> None:
        """Should skip disabled layers."""
        config = ResilienceConfig(
            retry_enabled=False,
            circuit_breaker_enabled=False,
            timeout_enabled=False,
        )

        assert config.get_retry_policy() is None
        assert config.get_circuit_breaker() is None
        assert config.get_timeout_manager() is None
