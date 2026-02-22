"""Ollama LLM provider for local model support.

This provider uses httpx to communicate with Ollama's OpenAI-compatible REST API.
Ollama is a free local tool that runs models like llama3.2, mistral, etc.
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from agentchord.core.types import (
    LLMResponse,
    Message,
    MessageRole,
    StreamChunk,
    ToolCall,
    Usage,
)
from agentchord.errors.exceptions import APIError, TimeoutError
from agentchord.llm.base import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    """Ollama LLM provider for local model support.

    Uses Ollama's OpenAI-compatible API endpoint at /v1/chat/completions.
    Model names should be passed as "ollama/llama3.2" but the provider
    strips the "ollama/" prefix when making API calls.

    Example:
        >>> provider = OllamaProvider(model="ollama/llama3.2")
        >>> response = await provider.complete([Message.user("Hello")])
    """

    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        timeout: float = 120.0,
    ) -> None:
        """Initialize Ollama provider.

        Args:
            model: Full model name with "ollama/" prefix (e.g., "ollama/llama3.2")
            base_url: Ollama server URL (default: http://localhost:11434)
            timeout: Request timeout in seconds (default: 120.0)
        """
        self._model = model
        # Strip "ollama/" prefix for actual API calls
        self._ollama_model = model.replace("ollama/", "", 1)
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    @property
    def model(self) -> str:
        """Return the full model identifier with ollama/ prefix."""
        return self._model

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "ollama"

    @property
    def cost_per_1k_input_tokens(self) -> float:
        """Cost per 1,000 input tokens in USD (free for local)."""
        return 0.0

    @property
    def cost_per_1k_output_tokens(self) -> float:
        """Cost per 1,000 output tokens in USD (free for local)."""
        return 0.0

    async def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a completion using Ollama.

        Args:
            messages: List of conversation messages.
            temperature: Sampling temperature (0.0-2.0).
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional parameters (e.g., tools).

        Returns:
            LLMResponse containing the generated content and usage stats.

        Raises:
            APIError: If Ollama server is not running or returns an error.
            TimeoutError: If the request times out.
        """
        url = f"{self._base_url}/v1/chat/completions"

        payload: dict[str, Any] = {
            "model": self._ollama_model,
            "messages": self._convert_messages(messages),
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
        }

        # Include tools if provided
        if "tools" in kwargs:
            payload["tools"] = kwargs["tools"]

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

        except httpx.ConnectError:
            raise APIError(
                f"Ollama server not running at {self._base_url}. "
                f"Install and start Ollama from https://ollama.com/",
                provider="ollama",
                model=self._ollama_model,
            )
        except httpx.TimeoutException:
            raise TimeoutError(
                f"Request to Ollama timed out after {self._timeout}s",
                provider="ollama",
                model=self._ollama_model,
                timeout_seconds=self._timeout,
            )
        except httpx.HTTPStatusError as e:
            raise APIError(
                f"Ollama API error: {e.response.status_code} - {e.response.text}",
                provider="ollama",
                model=self._ollama_model,
                status_code=e.response.status_code,
            )

        # Parse response
        choice = data["choices"][0]
        message = choice["message"]

        content = message.get("content", "")
        finish_reason = choice.get("finish_reason", "stop")

        # Parse tool calls if present
        tool_calls = None
        if "tool_calls" in message and message["tool_calls"]:
            tool_calls = self._parse_tool_calls(message["tool_calls"])

        # Parse usage
        usage_data = data.get("usage", {})
        usage = Usage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
        )

        return LLMResponse(
            content=content,
            model=self._model,  # Return full model name with prefix
            usage=usage,
            finish_reason=finish_reason,
            tool_calls=tool_calls,
            raw_response=data,
        )

    async def stream(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a completion using Ollama.

        Args:
            messages: List of conversation messages.
            temperature: Sampling temperature (0.0-2.0).
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional parameters (e.g., tools).

        Yields:
            StreamChunk containing incremental content.

        Raises:
            APIError: If Ollama server is not running or returns an error.
            TimeoutError: If the request times out.
        """
        url = f"{self._base_url}/v1/chat/completions"

        payload: dict[str, Any] = {
            "model": self._ollama_model,
            "messages": self._convert_messages(messages),
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
            "stream": True,
        }

        # Include tools if provided
        if "tools" in kwargs:
            payload["tools"] = kwargs["tools"]

        accumulated_content = ""

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        # Skip empty lines
                        if not line.strip():
                            continue

                        # Skip "data: " prefix
                        if not line.startswith("data: "):
                            continue

                        data_str = line[6:]  # Remove "data: " prefix

                        # Check for [DONE] marker
                        if data_str.strip() == "[DONE]":
                            break

                        try:
                            chunk_data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        # Parse chunk
                        choice = chunk_data.get("choices", [{}])[0]
                        delta = choice.get("delta", {})

                        content_delta = delta.get("content", "")
                        accumulated_content += content_delta

                        finish_reason = choice.get("finish_reason")

                        # Parse usage from final chunk
                        usage = None
                        if finish_reason and "usage" in chunk_data:
                            usage_data = chunk_data["usage"]
                            usage = Usage(
                                prompt_tokens=usage_data.get("prompt_tokens", 0),
                                completion_tokens=usage_data.get("completion_tokens", 0),
                            )

                        yield StreamChunk(
                            content=accumulated_content,
                            delta=content_delta,
                            finish_reason=finish_reason,
                            usage=usage,
                        )

        except httpx.ConnectError:
            raise APIError(
                f"Ollama server not running at {self._base_url}. "
                f"Install and start Ollama from https://ollama.com/",
                provider="ollama",
                model=self._ollama_model,
            )
        except httpx.TimeoutException:
            raise TimeoutError(
                f"Request to Ollama timed out after {self._timeout}s",
                provider="ollama",
                model=self._ollama_model,
                timeout_seconds=self._timeout,
            )
        except httpx.HTTPStatusError as e:
            raise APIError(
                f"Ollama API error: {e.response.status_code} - {e.response.text}",
                provider="ollama",
                model=self._ollama_model,
                status_code=e.response.status_code,
            )

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert Message objects to Ollama API format.

        Args:
            messages: List of Message objects.

        Returns:
            List of message dictionaries in OpenAI format.
        """
        result = []
        for msg in messages:
            msg_dict: dict[str, Any] = {
                "role": msg.role.value,
                "content": msg.content,
            }

            if msg.name:
                msg_dict["name"] = msg.name

            if msg.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in msg.tool_calls
                ]

            if msg.tool_call_id:
                msg_dict["tool_call_id"] = msg.tool_call_id

            result.append(msg_dict)

        return result

    def _parse_tool_calls(self, raw_tool_calls: list[dict[str, Any]]) -> list[ToolCall]:
        """Parse tool calls from Ollama API response.

        Args:
            raw_tool_calls: Raw tool call data from API.

        Returns:
            List of ToolCall objects.
        """
        tool_calls = []
        for tc in raw_tool_calls:
            function = tc.get("function", {})
            arguments_str = function.get("arguments", "{}")

            try:
                arguments = json.loads(arguments_str)
            except json.JSONDecodeError:
                arguments = {}

            tool_calls.append(
                ToolCall(
                    id=tc.get("id", ""),
                    name=function.get("name", ""),
                    arguments=arguments,
                )
            )

        return tool_calls
