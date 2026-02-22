import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from agentchord.llm.gemini import GeminiProvider, MODEL_COSTS
from agentchord.core.types import Message, MessageRole, ToolCall
from agentchord.errors.exceptions import APIError, AuthenticationError, MissingAPIKeyError
from agentchord.errors.exceptions import TimeoutError as AgentChordTimeoutError


class TestGeminiProviderInit:
    """Tests for GeminiProvider initialization."""

    def test_model_default(self):
        provider = GeminiProvider(api_key="test-key")
        assert provider.model == "gemini-2.0-flash"

    def test_custom_model(self):
        provider = GeminiProvider(model="gemini-1.5-pro", api_key="test-key")
        assert provider.model == "gemini-1.5-pro"

    def test_provider_name(self):
        provider = GeminiProvider(api_key="test-key")
        assert provider.provider_name == "gemini"

    def test_cost_lookup(self):
        provider = GeminiProvider(model="gemini-2.0-flash", api_key="test-key")
        assert provider.cost_per_1k_input_tokens == 0.0001
        assert provider.cost_per_1k_output_tokens == 0.0004

    def test_cost_unknown_model(self):
        provider = GeminiProvider(model="gemini-unknown", api_key="test-key")
        assert provider.cost_per_1k_input_tokens == 0.0001  # DEFAULT_COST

    def test_missing_api_key_deferred(self):
        """API key check is deferred to _require_api_key(), not __init__."""
        # Should NOT raise at init time (no env var, no param)
        with patch.dict("os.environ", {}, clear=True):
            provider = GeminiProvider.__new__(GeminiProvider)
            provider._model = "gemini-2.0-flash"
            provider._api_key = None
            provider._base_url = "https://example.com"
            provider._timeout = 60.0
            with pytest.raises(MissingAPIKeyError):
                provider._require_api_key()

    def test_api_key_from_env(self):
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "env-key"}):
            provider = GeminiProvider()
            assert provider._api_key == "env-key"


class TestGeminiComplete:
    """Tests for GeminiProvider complete method."""

    @pytest.mark.asyncio
    async def test_complete_basic(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello from Gemini"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("agentchord.llm.gemini.httpx.AsyncClient", return_value=mock_client):
            provider = GeminiProvider(api_key="test-key")
            messages = [Message(role=MessageRole.USER, content="Hi")]
            result = await provider.complete(messages)

        assert result.content == "Hello from Gemini"
        assert result.usage.prompt_tokens == 10
        assert result.usage.completion_tokens == 5
        assert result.model == "gemini-2.0-flash"

    @pytest.mark.asyncio
    async def test_complete_with_tool_calls(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "",
                    "tool_calls": [{
                        "id": "call_1",
                        "function": {"name": "search", "arguments": '{"q": "test"}'},
                    }],
                },
                "finish_reason": "tool_calls",
            }],
            "usage": {"prompt_tokens": 15, "completion_tokens": 8},
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("agentchord.llm.gemini.httpx.AsyncClient", return_value=mock_client):
            provider = GeminiProvider(api_key="test-key")
            messages = [Message(role=MessageRole.USER, content="Search")]
            result = await provider.complete(messages)

        assert result.tool_calls is not None
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "search"
        assert result.tool_calls[0].arguments == {"q": "test"}

    @pytest.mark.asyncio
    async def test_complete_sends_auth_header(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("agentchord.llm.gemini.httpx.AsyncClient", return_value=mock_client):
            provider = GeminiProvider(api_key="my-secret-key")
            await provider.complete([Message(role=MessageRole.USER, content="Hi")])

        call_args = mock_client.post.call_args
        headers = call_args.kwargs.get("headers", {})
        assert headers["Authorization"] == "Bearer my-secret-key"


class TestGeminiErrors:
    """Tests for GeminiProvider error handling."""

    @pytest.mark.asyncio
    async def test_connect_error(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("agentchord.llm.gemini.httpx.AsyncClient", return_value=mock_client):
            provider = GeminiProvider(api_key="test-key")
            with pytest.raises(APIError, match="Failed to connect"):
                await provider.complete([Message(role=MessageRole.USER, content="Hi")])

    @pytest.mark.asyncio
    async def test_timeout_error(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("agentchord.llm.gemini.httpx.AsyncClient", return_value=mock_client):
            provider = GeminiProvider(api_key="test-key")
            with pytest.raises(AgentChordTimeoutError):
                await provider.complete([Message(role=MessageRole.USER, content="Hi")])

    @pytest.mark.asyncio
    async def test_auth_error_401(self):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError("401", request=MagicMock(), response=mock_response)
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("agentchord.llm.gemini.httpx.AsyncClient", return_value=mock_client):
            provider = GeminiProvider(api_key="bad-key")
            with pytest.raises(AuthenticationError):
                await provider.complete([Message(role=MessageRole.USER, content="Hi")])

    @pytest.mark.asyncio
    async def test_http_error_500(self):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError("500", request=MagicMock(), response=mock_response)
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("agentchord.llm.gemini.httpx.AsyncClient", return_value=mock_client):
            provider = GeminiProvider(api_key="test-key")
            with pytest.raises(APIError, match="500"):
                await provider.complete([Message(role=MessageRole.USER, content="Hi")])


class TestGeminiRegistry:
    """Tests for GeminiProvider registry integration."""

    def test_detect_gemini_model(self):
        import agentchord.llm.registry as registry_module
        registry_module._default_registry = None
        try:
            from agentchord.llm.registry import get_registry
            registry = get_registry()
            assert registry.detect_provider("gemini-2.0-flash") == "gemini"
            assert registry.detect_provider("gemini-1.5-pro") == "gemini"
        finally:
            registry_module._default_registry = None
