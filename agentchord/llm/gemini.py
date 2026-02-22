"""Google Gemini LLM provider.

This provider uses httpx to communicate with Gemini's OpenAI-compatible REST API.
Supports models like gemini-2.0-flash, gemini-1.5-pro, etc.
"""

from __future__ import annotations

import json
import os
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
from agentchord.errors.exceptions import (
    APIError,
    AuthenticationError,
    MissingAPIKeyError,
    TimeoutError,
)
from agentchord.llm.base import BaseLLMProvider

# Model pricing information (as of 2025)
MODEL_COSTS = {
    "gemini-2.5-pro": {"input": 0.00125, "output": 0.005},
    "gemini-2.0-flash": {"input": 0.0001, "output": 0.0004},
    "gemini-2.0-flash-lite": {"input": 0.0, "output": 0.0},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
}
DEFAULT_COST = {"input": 0.0001, "output": 0.0004}


class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM provider.

    Uses Gemini's OpenAI-compatible API endpoint at
    https://generativelanguage.googleapis.com/v1beta/openai/.
    Requires a Google API key from AI Studio.

    Example:
        >>> provider = GeminiProvider(model="gemini-2.0-flash")
        >>> response = await provider.complete([Message.user("Hello")])
    """

    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        api_key: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        """Initialize Gemini provider.

        Args:
            model: Model name (e.g., "gemini-2.0-flash", "gemini-1.5-pro")
            api_key: Google API key. If None, reads from GOOGLE_API_KEY env var.
            timeout: Request timeout in seconds (default: 60.0)

        Raises:
            MissingAPIKeyError: If no API key is provided or found in environment.
        """
        self._model = model
        self._api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        self._base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
        self._timeout = timeout

    def _require_api_key(self) -> str:
        """Ensure API key is available."""
        if not self._api_key:
            raise MissingAPIKeyError("gemini")
        return self._api_key

    @property
    def model(self) -> str:
        """Return the model identifier."""
        return self._model

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "gemini"

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
        """Generate a completion using Gemini.

        Args:
            messages: List of conversation messages.
            temperature: Sampling temperature (0.0-2.0).
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional parameters (e.g., tools).

        Returns:
            LLMResponse containing the generated content and usage stats.

        Raises:
            MissingAPIKeyError: If API key is not set.
            AuthenticationError: If API key is invalid.
            APIError: If Gemini API returns an error.
            TimeoutError: If the request times out.
        """
        url = f"{self._base_url}/chat/completions"

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": self._convert_messages(messages),
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
        }

        # Include tools if provided
        if "tools" in kwargs:
            payload["tools"] = kwargs["tools"]

        api_key = self._require_api_key()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

        except httpx.ConnectError as e:
            raise APIError(
                f"Failed to connect to Gemini API at {self._base_url}: {str(e)}",
                provider="gemini",
                model=self._model,
            )
        except httpx.TimeoutException:
            raise TimeoutError(
                f"Request to Gemini timed out after {self._timeout}s",
                provider="gemini",
                model=self._model,
                timeout_seconds=self._timeout,
            )
        except httpx.HTTPStatusError as e:
            self._handle_error(e)

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
            model=self._model,
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
        """Stream a completion using Gemini.

        Args:
            messages: List of conversation messages.
            temperature: Sampling temperature (0.0-2.0).
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional parameters (e.g., tools).

        Yields:
            StreamChunk containing incremental content.

        Raises:
            MissingAPIKeyError: If API key is not set.
            AuthenticationError: If API key is invalid.
            APIError: If Gemini API returns an error.
            TimeoutError: If the request times out.
        """
        url = f"{self._base_url}/chat/completions"

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": self._convert_messages(messages),
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
            "stream": True,
        }

        # Include tools if provided
        if "tools" in kwargs:
            payload["tools"] = kwargs["tools"]

        api_key = self._require_api_key()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        accumulated_content = ""

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
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

        except httpx.ConnectError as e:
            raise APIError(
                f"Failed to connect to Gemini API at {self._base_url}: {str(e)}",
                provider="gemini",
                model=self._model,
            )
        except httpx.TimeoutException:
            raise TimeoutError(
                f"Request to Gemini timed out after {self._timeout}s",
                provider="gemini",
                model=self._model,
                timeout_seconds=self._timeout,
            )
        except httpx.HTTPStatusError as e:
            self._handle_error(e)

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert Message objects to OpenAI API format.

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
        """Parse tool calls from Gemini API response.

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

    def _handle_error(self, error: httpx.HTTPStatusError) -> None:
        """Handle HTTP errors from Gemini API.

        Args:
            error: The HTTP status error.

        Raises:
            AuthenticationError: For 401/403 errors.
            APIError: For all other HTTP errors.
        """
        status_code = error.response.status_code
        error_text = error.response.text

        if status_code in (401, 403):
            raise AuthenticationError(
                f"Invalid or missing API key. Get a key at https://aistudio.google.com/app/apikey",
                provider="gemini",
            )

        raise APIError(
            f"Gemini API error: {status_code} - {error_text}",
            provider="gemini",
            model=self._model,
            status_code=status_code,
        )
