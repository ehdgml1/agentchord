"""Base LLM provider interface.

All LLM providers must implement this abstract base class.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from agentweave.core.types import LLMResponse, Message, StreamChunk


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers.

    All LLM providers (OpenAI, Anthropic, etc.) must implement this interface.
    This ensures consistent behavior across different providers.

    Example:
        >>> class MyProvider(BaseLLMProvider):
        ...     async def complete(self, messages, **kwargs):
        ...         # Implementation here
        ...         pass
    """

    @property
    @abstractmethod
    def model(self) -> str:
        """Return the model identifier."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'openai', 'anthropic')."""
        ...

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a completion for the given messages.

        Args:
            messages: List of conversation messages.
            temperature: Sampling temperature (0.0-2.0).
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional provider-specific parameters.

        Returns:
            LLMResponse containing the generated content and usage stats.

        Raises:
            RateLimitError: If rate limit is exceeded.
            AuthenticationError: If authentication fails.
            APIError: If the API returns an error.
            TimeoutError: If the request times out.
        """
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a completion for the given messages.

        Args:
            messages: List of conversation messages.
            temperature: Sampling temperature (0.0-2.0).
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional provider-specific parameters.

        Yields:
            StreamChunk containing incremental content.
        """
        ...

    @property
    @abstractmethod
    def cost_per_1k_input_tokens(self) -> float:
        """Cost per 1,000 input tokens in USD."""
        ...

    @property
    @abstractmethod
    def cost_per_1k_output_tokens(self) -> float:
        """Cost per 1,000 output tokens in USD."""
        ...

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate the cost for given token usage.

        Args:
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Estimated cost in USD.
        """
        input_cost = (input_tokens / 1000) * self.cost_per_1k_input_tokens
        output_cost = (output_tokens / 1000) * self.cost_per_1k_output_tokens
        return input_cost + output_cost

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model!r})"
