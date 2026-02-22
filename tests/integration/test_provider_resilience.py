"""Integration tests for Provider Registry and Resilience.

Tests the full flow from model name detection through provider creation
and resilience layers (retry, circuit breaker, timeout).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import MagicMock

import pytest

from agentchord.core.agent import Agent
from agentchord.core.types import LLMResponse, Message, StreamChunk, Usage
from agentchord.errors.exceptions import ModelNotFoundError
from agentchord.llm.base import BaseLLMProvider
from agentchord.llm.registry import ProviderRegistry, get_registry
from agentchord.resilience import (
    CircuitBreaker,
    CircuitOpenError,
    ResilienceConfig,
    RetryPolicy,
    RetryStrategy,
    TimeoutManager,
)
from tests.conftest import MockLLMProvider


class FlakeyProvider(BaseLLMProvider):
    """Provider that fails N times then succeeds."""

    def __init__(self, fail_count: int = 2, model: str = "flakey-model"):
        self._model = model
        self._fail_count = fail_count
        self.call_count = 0

    async def complete(self, messages, **kwargs) -> LLMResponse:
        self.call_count += 1
        if self.call_count <= self._fail_count:
            raise ConnectionError(f"Temporary failure #{self.call_count}")
        return LLMResponse(
            content="Success after retries",
            model=self._model,
            usage=Usage(prompt_tokens=10, completion_tokens=5),
            finish_reason="stop",
        )

    async def stream(self, messages, **kwargs) -> AsyncIterator[StreamChunk]:
        result = await self.complete(messages, **kwargs)
        yield StreamChunk(content=result.content, delta=result.content, finish_reason="stop", usage=result.usage)

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return "flakey"

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return 0.0

    @property
    def cost_per_1k_output_tokens(self) -> float:
        return 0.0


class AlwaysFailProvider(BaseLLMProvider):
    """Provider that always fails."""

    def __init__(self, model: str = "fail-model"):
        self._model = model
        self.call_count = 0

    async def complete(self, messages, **kwargs):
        self.call_count += 1
        raise ConnectionError(f"Permanent failure #{self.call_count}")

    async def stream(self, messages, **kwargs):
        raise ConnectionError("Permanent failure")
        yield  # make it a generator

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return "failing"

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return 0.0

    @property
    def cost_per_1k_output_tokens(self) -> float:
        return 0.0


class SlowProvider(BaseLLMProvider):
    """Provider that takes too long to respond."""

    def __init__(self, delay: float = 5.0, model: str = "slow-model"):
        self._model = model
        self._delay = delay

    async def complete(self, messages, **kwargs):
        await asyncio.sleep(self._delay)
        return LLMResponse(
            content="Slow response",
            model=self._model,
            usage=Usage(prompt_tokens=10, completion_tokens=5),
            finish_reason="stop",
        )

    async def stream(self, messages, **kwargs):
        await asyncio.sleep(self._delay)
        yield StreamChunk(content="Slow", delta="Slow", finish_reason="stop")

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return "slow"

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return 0.0

    @property
    def cost_per_1k_output_tokens(self) -> float:
        return 0.0


@pytest.mark.integration
class TestRegistryProviderFlow:
    """Test registry detection → creation → execution flow."""

    def test_registry_detects_all_built_in_providers(self):
        """Default registry detects all 4 providers."""
        registry = get_registry()

        assert registry.detect_provider("gpt-4o") == "openai"
        assert registry.detect_provider("claude-3-5-sonnet") == "anthropic"
        assert registry.detect_provider("ollama/llama3") == "ollama"
        assert registry.detect_provider("gemini-2.0-flash") == "gemini"

    def test_registry_unknown_model_raises(self):
        """Unknown model prefix raises ModelNotFoundError."""
        registry = get_registry()

        with pytest.raises(ModelNotFoundError):
            registry.detect_provider("unknown-model-xyz")

    def test_custom_provider_registration(self):
        """Register and use a custom provider."""
        registry = ProviderRegistry()

        def custom_factory(**kwargs) -> MockLLMProvider:
            return MockLLMProvider(model=kwargs.get("model", "custom"))

        registry.register("custom", custom_factory, ["custom-"])

        provider = registry.create_provider("custom-v1")
        assert provider.model == "custom-v1"
        assert provider.provider_name == "mock"

    def test_provider_priority_longest_prefix(self):
        """Longer prefix wins when multiple match."""
        registry = ProviderRegistry()

        def factory_a(**kwargs):
            return MockLLMProvider(model="provider-a")

        def factory_b(**kwargs):
            return MockLLMProvider(model="provider-b")

        registry.register("short", factory_a, ["gpt-"])
        registry.register("long", factory_b, ["gpt-4-"])

        assert registry.detect_provider("gpt-4-turbo") == "long"
        assert registry.detect_provider("gpt-3.5") == "short"


@pytest.mark.integration
class TestRetryIntegration:
    """Retry policy with actual provider failures."""

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_failures(self):
        """Provider fails twice, retry policy recovers on third attempt."""
        provider = FlakeyProvider(fail_count=2)

        config = ResilienceConfig(
            retry_enabled=True,
            retry_policy=RetryPolicy(
                max_retries=3,
                strategy=RetryStrategy.FIXED,
                base_delay=0.01,  # Fast for tests
            ),
            timeout_enabled=False,
            circuit_breaker_enabled=False,
        )

        agent = Agent(
            name="retry-test",
            role="Retry tester",
            llm_provider=provider,
            resilience=config,
        )

        result = await agent.run("Test input")

        assert result.output == "Success after retries"
        assert provider.call_count == 3  # 2 failures + 1 success

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises(self):
        """When all retries fail, error propagates."""
        provider = AlwaysFailProvider()

        config = ResilienceConfig(
            retry_enabled=True,
            retry_policy=RetryPolicy(
                max_retries=2,
                strategy=RetryStrategy.FIXED,
                base_delay=0.01,
            ),
            timeout_enabled=False,
            circuit_breaker_enabled=False,
        )

        agent = Agent(
            name="retry-fail",
            role="Will fail",
            llm_provider=provider,
            resilience=config,
        )

        from agentchord.errors.exceptions import AgentExecutionError
        with pytest.raises(AgentExecutionError):
            await agent.run("Test")


@pytest.mark.integration
class TestCircuitBreakerIntegration:
    """Circuit breaker with provider failures."""

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self):
        """Circuit breaker opens after enough failures."""
        cb = CircuitBreaker(failure_threshold=3, timeout=60)

        async def failing_func():
            raise ConnectionError("fail")

        for _ in range(3):
            with pytest.raises(ConnectionError):
                await cb.execute(failing_func)

        # Circuit should now be open
        with pytest.raises(CircuitOpenError):
            await cb.execute(failing_func)

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_agent(self):
        """Agent with circuit breaker stops after threshold."""
        provider = AlwaysFailProvider()

        config = ResilienceConfig(
            retry_enabled=False,
            circuit_breaker_enabled=True,
            circuit_breaker=CircuitBreaker(failure_threshold=2, timeout=60),
            timeout_enabled=False,
        )

        agent = Agent(
            name="cb-test",
            role="CB tester",
            llm_provider=provider,
            resilience=config,
        )

        from agentchord.errors.exceptions import AgentExecutionError

        # First 2 calls fail normally (provider gets called)
        with pytest.raises(AgentExecutionError):
            await agent.run("Test 1")
        with pytest.raises(AgentExecutionError):
            await agent.run("Test 2")

        assert provider.call_count == 2  # Provider was called both times

        # Third call should be blocked by circuit breaker (fast fail, provider NOT called)
        with pytest.raises(AgentExecutionError):
            await agent.run("Test 3")

        assert provider.call_count == 2  # Provider was NOT called again - circuit blocked it


@pytest.mark.integration
class TestTimeoutIntegration:
    """Timeout manager with slow providers."""

    @pytest.mark.asyncio
    async def test_timeout_cancels_slow_provider(self):
        """Timeout triggers when provider is too slow."""
        provider = SlowProvider(delay=5.0)

        config = ResilienceConfig(
            retry_enabled=False,
            circuit_breaker_enabled=False,
            timeout_enabled=True,
            timeout_manager=TimeoutManager(default_timeout=0.1, use_builtin_defaults=False),
        )

        agent = Agent(
            name="timeout-test",
            role="Timeout tester",
            model="slow-model",
            llm_provider=provider,
            resilience=config,
        )

        from agentchord.errors.exceptions import AgentExecutionError
        with pytest.raises(AgentExecutionError):
            await agent.run("Test")

    @pytest.mark.asyncio
    async def test_fast_provider_completes_within_timeout(self):
        """Normal provider completes before timeout."""
        provider = MockLLMProvider(response_content="Fast response")

        config = ResilienceConfig(
            retry_enabled=False,
            circuit_breaker_enabled=False,
            timeout_enabled=True,
            timeout_manager=TimeoutManager(default_timeout=10.0),
        )

        agent = Agent(
            name="fast-test",
            role="Fast tester",
            llm_provider=provider,
            resilience=config,
        )

        result = await agent.run("Test")
        assert result.output == "Fast response"


@pytest.mark.integration
class TestCombinedResilience:
    """All resilience layers working together."""

    @pytest.mark.asyncio
    async def test_retry_plus_timeout(self):
        """Retry with timeout: flakey provider succeeds within timeout."""
        provider = FlakeyProvider(fail_count=1)

        config = ResilienceConfig(
            retry_enabled=True,
            retry_policy=RetryPolicy(
                max_retries=3,
                strategy=RetryStrategy.FIXED,
                base_delay=0.01,
            ),
            timeout_enabled=True,
            timeout_manager=TimeoutManager(default_timeout=5.0),
            circuit_breaker_enabled=False,
        )

        agent = Agent(
            name="combo-test",
            role="Combo tester",
            llm_provider=provider,
            resilience=config,
        )

        result = await agent.run("Test")
        assert result.output == "Success after retries"
        assert provider.call_count == 2

    @pytest.mark.asyncio
    async def test_all_three_layers(self):
        """Retry + circuit breaker + timeout all active."""
        provider = FlakeyProvider(fail_count=1)

        config = ResilienceConfig(
            retry_enabled=True,
            retry_policy=RetryPolicy(max_retries=3, strategy=RetryStrategy.FIXED, base_delay=0.01),
            circuit_breaker_enabled=True,
            circuit_breaker=CircuitBreaker(failure_threshold=5, timeout=60),
            timeout_enabled=True,
            timeout_manager=TimeoutManager(default_timeout=5.0),
        )

        agent = Agent(
            name="all-layers",
            role="All resilience",
            llm_provider=provider,
            resilience=config,
        )

        result = await agent.run("Test")
        assert result.output == "Success after retries"
