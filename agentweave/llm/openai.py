"""OpenAI LLM provider implementation."""

from __future__ import annotations

import json
import os
from typing import Any, AsyncIterator

from agentweave.core.types import LLMResponse, Message, MessageRole, StreamChunk, Usage, ToolCall
from agentweave.errors.exceptions import (
    APIError,
    AuthenticationError,
    MissingAPIKeyError,
    RateLimitError,
    TimeoutError,
)
from agentweave.llm.base import BaseLLMProvider

# Pricing as of 2025 (USD per 1K tokens)
MODEL_COSTS: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4.1": {"input": 0.002, "output": 0.008},
    "gpt-4.1-mini": {"input": 0.0004, "output": 0.0016},
    "o1": {"input": 0.015, "output": 0.06},
    "o1-mini": {"input": 0.003, "output": 0.012},
}

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_COST = {"input": 0.01, "output": 0.03}


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider.

    Example:
        >>> provider = OpenAIProvider(model="gpt-4o-mini")
        >>> response = await provider.complete([Message.user("Hello!")])
        >>> print(response.content)
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        """Initialize OpenAI provider.

        Args:
            model: Model identifier (e.g., 'gpt-4o', 'gpt-4o-mini').
            api_key: OpenAI API key. Defaults to OPENAI_API_KEY env var.
            base_url: Custom API base URL for proxies.
            timeout: Request timeout in seconds.
        """
        self._model = model
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._base_url = base_url
        self._timeout = timeout
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as e:
                raise ImportError(
                    "OpenAI package not installed. "
                    "Install with: pip install agentweave[openai]"
                ) from e

            if not self._api_key:
                raise MissingAPIKeyError("openai")

            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                timeout=self._timeout,
            )
        return self._client

    @property
    def model(self) -> str:
        """Return the model identifier."""
        return self._model

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "openai"

    @property
    def cost_per_1k_input_tokens(self) -> float:
        """Cost per 1,000 input tokens in USD."""
        costs = MODEL_COSTS.get(self._model, DEFAULT_COST)
        return costs["input"]

    @property
    def cost_per_1k_output_tokens(self) -> float:
        """Cost per 1,000 output tokens in USD."""
        costs = MODEL_COSTS.get(self._model, DEFAULT_COST)
        return costs["output"]

    async def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a completion using OpenAI API.

        Args:
            messages: List of conversation messages.
            temperature: Sampling temperature (0.0-2.0).
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional OpenAI-specific parameters.

        Returns:
            LLMResponse with generated content and usage.
        """
        client = self._get_client()
        openai_messages = self._convert_messages(messages)

        try:
            response = await client.chat.completions.create(
                model=self._model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
        except Exception as e:
            self._handle_error(e)

        return self._convert_response(response)

    async def stream(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a completion using OpenAI API."""
        client = self._get_client()
        openai_messages = self._convert_messages(messages)

        try:
            response = await client.chat.completions.create(
                model=self._model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs,
            )
        except Exception as e:
            self._handle_error(e)

        content = ""
        async for chunk in response:
            if not chunk.choices:
                continue

            choice = chunk.choices[0]
            delta = choice.delta.content or ""
            content += delta

            yield StreamChunk(
                content=content,
                delta=delta,
                finish_reason=choice.finish_reason,
            )

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert AgentWeave messages to OpenAI format."""
        result = []
        for msg in messages:
            converted: dict[str, Any] = {
                "role": msg.role.value,
                "content": msg.content,
            }
            if msg.name:
                converted["name"] = msg.name
            if msg.tool_calls:
                converted["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": json.dumps(tc.arguments) if isinstance(tc.arguments, dict) else str(tc.arguments)},
                    }
                    for tc in msg.tool_calls
                ]
            if msg.tool_call_id:
                converted["tool_call_id"] = msg.tool_call_id
            result.append(converted)
        return result

    def _convert_response(self, response: Any) -> LLMResponse:
        """Convert OpenAI response to AgentWeave format."""
        choice = response.choices[0]

        # Extract tool calls if present
        tool_calls = None
        if choice.message.tool_calls:
            tool_calls = [
                ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=self._parse_tool_arguments(tc.function.arguments),
                )
                for tc in choice.message.tool_calls
            ]

        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            usage=Usage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
            ),
            finish_reason=choice.finish_reason or "stop",
            tool_calls=tool_calls,
            raw_response=response.model_dump(),
        )

    @staticmethod
    def _parse_tool_arguments(arguments: str) -> dict[str, Any]:
        """Parse tool call arguments from JSON string."""
        import json
        try:
            return json.loads(arguments)
        except (json.JSONDecodeError, TypeError):
            return {}

    def _handle_error(self, error: Exception) -> None:
        """Convert OpenAI errors to AgentWeave errors."""
        try:
            import openai
        except ImportError:
            raise error

        if isinstance(error, openai.RateLimitError):
            raise RateLimitError(
                str(error),
                provider="openai",
                model=self._model,
            ) from error
        elif isinstance(error, openai.AuthenticationError):
            raise AuthenticationError(
                str(error),
                provider="openai",
            ) from error
        elif isinstance(error, openai.APITimeoutError):
            raise TimeoutError(
                str(error),
                provider="openai",
                model=self._model,
                timeout_seconds=self._timeout,
            ) from error
        elif isinstance(error, openai.APIError):
            raise APIError(
                str(error),
                provider="openai",
                model=self._model,
            ) from error
        raise error
