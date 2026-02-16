"""Anthropic Claude LLM provider implementation."""

from __future__ import annotations

import os
from typing import Any, AsyncIterator

from agentweave.core.types import LLMResponse, Message, MessageRole, StreamChunk, ToolCall, Usage
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
    "claude-sonnet-4-5-20250929": {"input": 0.003, "output": 0.015},
    "claude-haiku-4-5-20251001": {"input": 0.001, "output": 0.005},
    "claude-opus-4-6": {"input": 0.005, "output": 0.025},
    "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    "claude-3-5-sonnet-latest": {"input": 0.003, "output": 0.015},
    "claude-3-5-haiku-20241022": {"input": 0.0008, "output": 0.004},
    "claude-3-5-haiku-latest": {"input": 0.0008, "output": 0.004},
    "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
    "claude-3-opus-latest": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
    "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
}

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
DEFAULT_COST = {"input": 0.003, "output": 0.015}


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude API provider.

    Example:
        >>> provider = AnthropicProvider(model="claude-3-5-sonnet-latest")
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
        """Initialize Anthropic provider.

        Args:
            model: Model identifier (e.g., 'claude-3-5-sonnet-latest').
            api_key: Anthropic API key. Defaults to ANTHROPIC_API_KEY env var.
            base_url: Custom API base URL for proxies.
            timeout: Request timeout in seconds.
        """
        self._model = model
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._base_url = base_url
        self._timeout = timeout
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
            except ImportError as e:
                raise ImportError(
                    "Anthropic package not installed. "
                    "Install with: pip install agentweave[anthropic]"
                ) from e

            if not self._api_key:
                raise MissingAPIKeyError("anthropic")

            kwargs: dict[str, Any] = {
                "api_key": self._api_key,
                "timeout": self._timeout,
            }
            if self._base_url:
                kwargs["base_url"] = self._base_url

            self._client = AsyncAnthropic(**kwargs)
        return self._client

    @property
    def model(self) -> str:
        """Return the model identifier."""
        return self._model

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "anthropic"

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
        """Generate a completion using Anthropic API.

        Args:
            messages: List of conversation messages.
            temperature: Sampling temperature (0.0-1.0 for Claude).
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional Anthropic-specific parameters.

        Returns:
            LLMResponse with generated content and usage.
        """
        client = self._get_client()
        system_prompt, anthropic_messages = self._extract_system_and_messages(messages)

        try:
            create_kwargs: dict[str, Any] = {
                "model": self._model,
                "messages": anthropic_messages,
                "max_tokens": max_tokens,
                "temperature": min(temperature, 1.0),  # Claude max is 1.0
                **kwargs,
            }
            if system_prompt:
                create_kwargs["system"] = system_prompt

            response = await client.messages.create(**create_kwargs)
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
        """Stream a completion using Anthropic API."""
        client = self._get_client()
        system_prompt, anthropic_messages = self._extract_system_and_messages(messages)

        create_kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens,
            "temperature": min(temperature, 1.0),
            **kwargs,
        }
        if system_prompt:
            create_kwargs["system"] = system_prompt

        try:
            async with client.messages.stream(**create_kwargs) as stream:
                content = ""
                async for text in stream.text_stream:
                    content += text
                    yield StreamChunk(
                        content=content,
                        delta=text,
                    )

                # Get final message for usage stats
                final_message = await stream.get_final_message()
                yield StreamChunk(
                    content=content,
                    delta="",
                    finish_reason=final_message.stop_reason,
                    usage=Usage(
                        prompt_tokens=final_message.usage.input_tokens,
                        completion_tokens=final_message.usage.output_tokens,
                    ),
                )
        except Exception as e:
            self._handle_error(e)

    def _extract_system_and_messages(
        self, messages: list[Message]
    ) -> tuple[str | None, list[dict[str, Any]]]:
        """Extract system message and convert other messages to Anthropic format.

        Anthropic handles system messages separately from other messages.
        """
        system_prompt: str | None = None
        anthropic_messages: list[dict[str, Any]] = []

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_prompt = msg.content
            elif msg.role == MessageRole.TOOL:
                anthropic_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.tool_call_id or "",
                        "content": msg.content,
                    }],
                })
            elif msg.role == MessageRole.ASSISTANT and msg.tool_calls:
                content_blocks: list[dict[str, Any]] = []
                if msg.content:
                    content_blocks.append({"type": "text", "text": msg.content})
                for tc in msg.tool_calls:
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments,
                    })
                anthropic_messages.append({
                    "role": "assistant",
                    "content": content_blocks,
                })
            else:
                role = "user" if msg.role == MessageRole.USER else "assistant"
                anthropic_messages.append({
                    "role": role,
                    "content": msg.content,
                })

        return system_prompt, anthropic_messages

    def _convert_response(self, response: Any) -> LLMResponse:
        """Convert Anthropic response to AgentWeave format."""
        content = ""
        tool_calls = []

        for block in response.content:
            if hasattr(block, "text"):
                content = block.text
            elif hasattr(block, "type") and block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input if isinstance(block.input, dict) else {},
                ))

        return LLMResponse(
            content=content,
            model=response.model,
            usage=Usage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
            ),
            finish_reason=response.stop_reason or "end_turn",
            tool_calls=tool_calls if tool_calls else None,
            raw_response={
                "id": response.id,
                "type": response.type,
                "role": response.role,
                "model": response.model,
                "stop_reason": response.stop_reason,
            },
        )

    def _handle_error(self, error: Exception) -> None:
        """Convert Anthropic errors to AgentWeave errors."""
        try:
            import anthropic
        except ImportError:
            raise error

        if isinstance(error, anthropic.RateLimitError):
            raise RateLimitError(
                str(error),
                provider="anthropic",
                model=self._model,
            ) from error
        elif isinstance(error, anthropic.AuthenticationError):
            raise AuthenticationError(
                str(error),
                provider="anthropic",
            ) from error
        elif isinstance(error, anthropic.APITimeoutError):
            raise TimeoutError(
                str(error),
                provider="anthropic",
                model=self._model,
                timeout_seconds=self._timeout,
            ) from error
        elif isinstance(error, anthropic.APIError):
            raise APIError(
                str(error),
                provider="anthropic",
                model=self._model,
            ) from error
        raise error
