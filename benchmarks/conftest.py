"""Benchmark fixtures."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest

from agentweave.core.agent import Agent
from agentweave.core.types import LLMResponse, Message, StreamChunk, Usage
from agentweave.llm.base import BaseLLMProvider


class BenchmarkProvider(BaseLLMProvider):
    """Ultra-fast mock provider for benchmarking.

    Optimized for minimal overhead to accurately measure framework performance.
    """

    def __init__(
        self,
        response: str = "Benchmark response",
        model: str = "bench-model",
    ) -> None:
        self._response = response
        self._model = model

    async def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        """Return immediate response with minimal overhead."""
        return LLMResponse(
            content=self._response,
            model=self._model,
            usage=Usage(prompt_tokens=10, completion_tokens=5),
            finish_reason="stop",
        )

    async def stream(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """Return immediate stream chunk."""
        yield StreamChunk(
            content=self._response,
            delta=self._response,
            finish_reason="stop",
            usage=Usage(prompt_tokens=10, completion_tokens=5),
        )

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return "benchmark"

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return 0.0

    @property
    def cost_per_1k_output_tokens(self) -> float:
        return 0.0


@pytest.fixture
def bench_provider() -> BenchmarkProvider:
    """Create a benchmark provider."""
    return BenchmarkProvider()


@pytest.fixture
def bench_agent(bench_provider: BenchmarkProvider) -> Agent:
    """Create a benchmark agent."""
    return Agent(name="bench", role="Benchmark", llm_provider=bench_provider)
