"""Unit tests for OllamaProvider."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from agentchord.core.types import Message, MessageRole, ToolCall, Usage
from agentchord.errors.exceptions import APIError
from agentchord.errors.exceptions import TimeoutError as AgentweaveTimeoutError
from agentchord.llm.ollama import OllamaProvider


class TestOllamaProviderInit:
    """Test OllamaProvider initialization."""

    def test_model_prefix_stripping(self):
        """Test that 'ollama/' prefix is stripped for API calls."""
        provider = OllamaProvider(model="ollama/llama3.2")
        assert provider._ollama_model == "llama3.2"

    def test_full_model_name(self):
        """Test that model property returns full name with prefix."""
        provider = OllamaProvider(model="ollama/llama3.2")
        assert provider.model == "ollama/llama3.2"

    def test_provider_name(self):
        """Test that provider_name returns 'ollama'."""
        provider = OllamaProvider(model="ollama/llama3.2")
        assert provider.provider_name == "ollama"

    def test_cost_is_zero(self):
        """Test that both cost properties return 0.0 for local models."""
        provider = OllamaProvider(model="ollama/llama3.2")
        assert provider.cost_per_1k_input_tokens == 0.0
        assert provider.cost_per_1k_output_tokens == 0.0

    def test_custom_base_url(self):
        """Test that custom base_url is stored and trailing slash is stripped."""
        provider = OllamaProvider(
            model="ollama/llama3.2",
            base_url="http://custom-host:8080/"
        )
        assert provider._base_url == "http://custom-host:8080"

    def test_default_base_url(self):
        """Test that default base_url is localhost:11434."""
        provider = OllamaProvider(model="ollama/llama3.2")
        assert provider._base_url == "http://localhost:11434"


class TestOllamaComplete:
    """Test OllamaProvider.complete() method."""

    @pytest.mark.asyncio
    async def test_complete_basic(self):
        """Test basic completion with text response."""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "Hello! How can I help you today?",
                        "role": "assistant"
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 15
            }
        }
        mock_response.raise_for_status = MagicMock()

        # Mock httpx.AsyncClient
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("agentchord.llm.ollama.httpx.AsyncClient", return_value=mock_client):
            provider = OllamaProvider(model="ollama/llama3.2")
            messages = [Message(role=MessageRole.USER, content="Hello")]

            result = await provider.complete(messages)

            assert result.content == "Hello! How can I help you today?"
            assert result.model == "ollama/llama3.2"
            assert result.usage.prompt_tokens == 10
            assert result.usage.completion_tokens == 15
            assert result.finish_reason == "stop"
            assert result.tool_calls is None

    @pytest.mark.asyncio
    async def test_complete_with_tool_calls(self):
        """Test completion with tool calls in response."""
        # Mock response with tool calls
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "call_123",
                                "type": "function",
                                "function": {
                                    "name": "get_weather",
                                    "arguments": '{"city": "San Francisco"}'
                                }
                            }
                        ]
                    },
                    "finish_reason": "tool_calls"
                }
            ],
            "usage": {
                "prompt_tokens": 20,
                "completion_tokens": 30
            }
        }
        mock_response.raise_for_status = MagicMock()

        # Mock httpx.AsyncClient
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("agentchord.llm.ollama.httpx.AsyncClient", return_value=mock_client):
            provider = OllamaProvider(model="ollama/llama3.2")
            messages = [Message(role=MessageRole.USER, content="What's the weather?")]

            result = await provider.complete(messages)

            assert result.content == ""
            assert result.finish_reason == "tool_calls"
            assert result.tool_calls is not None
            assert len(result.tool_calls) == 1
            assert result.tool_calls[0].id == "call_123"
            assert result.tool_calls[0].name == "get_weather"
            assert result.tool_calls[0].arguments == {"city": "San Francisco"}

    @pytest.mark.asyncio
    async def test_complete_passes_tools(self):
        """Test that tools are passed in request payload."""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {"content": "Using tools", "role": "assistant"},
                    "finish_reason": "stop"
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 10}
        }
        mock_response.raise_for_status = MagicMock()

        # Mock httpx.AsyncClient
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        tools_param = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather for a city"
                }
            }
        ]

        with patch("agentchord.llm.ollama.httpx.AsyncClient", return_value=mock_client):
            provider = OllamaProvider(model="ollama/llama3.2")
            messages = [Message(role=MessageRole.USER, content="Check weather")]

            await provider.complete(messages, tools=tools_param)

            # Verify that post was called with tools in payload
            call_args = mock_client.post.call_args
            payload = call_args.kwargs["json"]
            assert "tools" in payload
            assert payload["tools"] == tools_param


class TestOllamaErrors:
    """Test OllamaProvider error handling."""

    @pytest.mark.asyncio
    async def test_connect_error(self):
        """Test ConnectError is converted to APIError with helpful message."""
        # Mock httpx.AsyncClient to raise ConnectError
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("agentchord.llm.ollama.httpx.AsyncClient", return_value=mock_client):
            provider = OllamaProvider(model="ollama/llama3.2")
            messages = [Message(role=MessageRole.USER, content="Hello")]

            with pytest.raises(APIError) as exc_info:
                await provider.complete(messages)

            error = exc_info.value
            assert "not running" in str(error)
            assert "http://localhost:11434" in str(error)
            assert error.provider == "ollama"
            assert error.model == "llama3.2"

    @pytest.mark.asyncio
    async def test_timeout_error(self):
        """Test TimeoutException is converted to AgentweaveTimeoutError."""
        # Mock httpx.AsyncClient to raise TimeoutException
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("agentchord.llm.ollama.httpx.AsyncClient", return_value=mock_client):
            provider = OllamaProvider(model="ollama/llama3.2", timeout=30.0)
            messages = [Message(role=MessageRole.USER, content="Hello")]

            with pytest.raises(AgentweaveTimeoutError) as exc_info:
                await provider.complete(messages)

            error = exc_info.value
            assert "timed out after 30.0s" in str(error)
            assert error.provider == "ollama"
            assert error.model == "llama3.2"
            assert error.timeout_seconds == 30.0

    @pytest.mark.asyncio
    async def test_http_error(self):
        """Test HTTPStatusError is converted to APIError with status code."""
        # Mock response with error status
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"

        # Create HTTPStatusError
        http_error = httpx.HTTPStatusError(
            "Server error",
            request=MagicMock(),
            response=mock_response
        )

        mock_response.raise_for_status = MagicMock(side_effect=http_error)

        # Mock httpx.AsyncClient
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("agentchord.llm.ollama.httpx.AsyncClient", return_value=mock_client):
            provider = OllamaProvider(model="ollama/llama3.2")
            messages = [Message(role=MessageRole.USER, content="Hello")]

            with pytest.raises(APIError) as exc_info:
                await provider.complete(messages)

            error = exc_info.value
            assert "500" in str(error)
            assert "Internal server error" in str(error)
            assert error.provider == "ollama"
            assert error.model == "llama3.2"
            assert error.status_code == 500


class TestOllamaMessageConversion:
    """Test OllamaProvider._convert_messages() method."""

    def test_convert_basic_messages(self):
        """Test conversion of basic system/user/assistant messages."""
        provider = OllamaProvider(model="ollama/llama3.2")

        messages = [
            Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
            Message(role=MessageRole.USER, content="Hello!"),
            Message(role=MessageRole.ASSISTANT, content="Hi there!"),
        ]

        converted = provider._convert_messages(messages)

        assert len(converted) == 3
        assert converted[0] == {
            "role": "system",
            "content": "You are a helpful assistant."
        }
        assert converted[1] == {
            "role": "user",
            "content": "Hello!"
        }
        assert converted[2] == {
            "role": "assistant",
            "content": "Hi there!"
        }

    def test_convert_tool_messages(self):
        """Test conversion of messages with tool calls and tool results."""
        provider = OllamaProvider(model="ollama/llama3.2")

        # Message with tool calls
        tool_call_msg = Message(
            role=MessageRole.ASSISTANT,
            content="",
            tool_calls=[
                ToolCall(
                    id="call_abc",
                    name="get_weather",
                    arguments={"city": "Boston"}
                )
            ]
        )

        # Tool result message
        tool_result_msg = Message(
            role=MessageRole.TOOL,
            content='{"temperature": 72}',
            tool_call_id="call_abc",
            name="get_weather"
        )

        messages = [tool_call_msg, tool_result_msg]
        converted = provider._convert_messages(messages)

        assert len(converted) == 2

        # Check tool call message
        assert converted[0]["role"] == "assistant"
        assert converted[0]["content"] == ""
        assert "tool_calls" in converted[0]
        assert len(converted[0]["tool_calls"]) == 1
        assert converted[0]["tool_calls"][0]["id"] == "call_abc"
        assert converted[0]["tool_calls"][0]["type"] == "function"
        assert converted[0]["tool_calls"][0]["function"]["name"] == "get_weather"
        assert converted[0]["tool_calls"][0]["function"]["arguments"] == '{"city": "Boston"}'

        # Check tool result message
        assert converted[1]["role"] == "tool"
        assert converted[1]["content"] == '{"temperature": 72}'
        assert converted[1]["tool_call_id"] == "call_abc"
        assert converted[1]["name"] == "get_weather"

    def test_parse_tool_calls_with_invalid_json(self):
        """Test that _parse_tool_calls handles invalid JSON in arguments."""
        provider = OllamaProvider(model="ollama/llama3.2")

        raw_tool_calls = [
            {
                "id": "call_xyz",
                "type": "function",
                "function": {
                    "name": "broken_tool",
                    "arguments": "invalid json{{"
                }
            }
        ]

        parsed = provider._parse_tool_calls(raw_tool_calls)

        assert len(parsed) == 1
        assert parsed[0].id == "call_xyz"
        assert parsed[0].name == "broken_tool"
        assert parsed[0].arguments == {}  # Falls back to empty dict
