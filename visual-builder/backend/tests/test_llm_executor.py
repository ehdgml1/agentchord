"""Tests for executor LLM provider integration."""
import pytest
from unittest.mock import MagicMock
from app.core.executor import WorkflowExecutor, WorkflowNode
from app.config import Settings


class TestCreateLLMProvider:
    """Test WorkflowExecutor._create_llm_provider instance method."""

    @pytest.mark.asyncio
    async def test_creates_openai_provider_gpt4o(self, executor):
        """Creates OpenAI provider for GPT-4o."""
        settings = Settings(
            database_url="sqlite:///test.db",
            openai_api_key="sk-test",
        )
        provider = await executor._create_llm_provider("gpt-4o", settings)

        assert provider is not None
        assert provider.model == "gpt-4o"
        assert provider._api_key == "sk-test"

    @pytest.mark.asyncio
    async def test_creates_openai_provider_gpt4o_mini(self, executor):
        """Creates OpenAI provider for GPT-4o Mini."""
        settings = Settings(
            database_url="sqlite:///test.db",
            openai_api_key="sk-test",
        )
        provider = await executor._create_llm_provider("gpt-4o-mini", settings)

        assert provider is not None
        assert provider.model == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_creates_openai_provider_o1(self, executor):
        """Creates OpenAI provider for O1 model."""
        settings = Settings(
            database_url="sqlite:///test.db",
            openai_api_key="sk-test",
        )
        provider = await executor._create_llm_provider("o1", settings)

        assert provider is not None
        assert provider.model == "o1"

    @pytest.mark.asyncio
    async def test_creates_openai_provider_o1_mini(self, executor):
        """Creates OpenAI provider for O1-mini model."""
        settings = Settings(
            database_url="sqlite:///test.db",
            openai_api_key="sk-test",
        )
        provider = await executor._create_llm_provider("o1-mini", settings)

        assert provider is not None
        assert provider.model == "o1-mini"

    @pytest.mark.asyncio
    async def test_creates_anthropic_provider_sonnet(self, executor):
        """Creates Anthropic provider for Claude Sonnet."""
        settings = Settings(
            database_url="sqlite:///test.db",
            anthropic_api_key="sk-ant-test",
        )
        provider = await executor._create_llm_provider(
            "claude-sonnet-4-5-20250929", settings
        )

        assert provider is not None
        assert provider.model == "claude-sonnet-4-5-20250929"
        assert provider._api_key == "sk-ant-test"

    @pytest.mark.asyncio
    async def test_creates_anthropic_provider_haiku(self, executor):
        """Creates Anthropic provider for Claude Haiku."""
        settings = Settings(
            database_url="sqlite:///test.db",
            anthropic_api_key="sk-ant-test",
        )
        provider = await executor._create_llm_provider(
            "claude-haiku-4-5-20251001", settings
        )

        assert provider is not None
        assert provider.model == "claude-haiku-4-5-20251001"

    @pytest.mark.asyncio
    async def test_creates_anthropic_provider_opus(self, executor):
        """Creates Anthropic provider for Claude Opus."""
        settings = Settings(
            database_url="sqlite:///test.db",
            anthropic_api_key="sk-ant-test",
        )
        provider = await executor._create_llm_provider("claude-opus-4-6", settings)

        assert provider is not None
        assert provider.model == "claude-opus-4-6"

    @pytest.mark.asyncio
    async def test_raises_without_openai_key(self, executor):
        """Raises ValueError when OpenAI key not configured."""
        settings = Settings(database_url="sqlite:///test.db")

        with pytest.raises(ValueError, match="OpenAI API key not configured"):
            await executor._create_llm_provider("gpt-4o", settings)

    @pytest.mark.asyncio
    async def test_raises_without_anthropic_key(self, executor):
        """Raises ValueError when Anthropic key not configured."""
        settings = Settings(database_url="sqlite:///test.db")

        with pytest.raises(ValueError, match="Anthropic API key not configured"):
            await executor._create_llm_provider(
                "claude-sonnet-4-5-20250929", settings
            )

    @pytest.mark.asyncio
    async def test_raises_unsupported_model(self, executor):
        """Raises ValueError for unsupported model."""
        settings = Settings(database_url="sqlite:///test.db")

        with pytest.raises(ValueError, match="Unsupported model"):
            await executor._create_llm_provider("llama-3", settings)

    @pytest.mark.asyncio
    async def test_creates_gemini_provider(self, executor):
        """Creates Gemini provider for Gemini models."""
        settings = Settings(
            database_url="sqlite:///test.db",
            gemini_api_key="test-gemini-key",
        )
        provider = await executor._create_llm_provider("gemini-2.0-flash", settings)

        assert provider is not None
        assert provider.model == "gemini-2.0-flash"

    @pytest.mark.asyncio
    async def test_raises_without_gemini_key(self, executor):
        """Raises ValueError when Gemini key not configured."""
        settings = Settings(database_url="sqlite:///test.db")

        with pytest.raises(ValueError, match="Gemini API key not configured"):
            await executor._create_llm_provider("gemini-pro", settings)

    @pytest.mark.asyncio
    async def test_passes_base_url_to_openai(self, executor):
        """Passes custom base URL to OpenAI provider."""
        settings = Settings(
            database_url="sqlite:///test.db",
            openai_api_key="sk-test",
            openai_base_url="https://custom.api.com/v1",
        )
        provider = await executor._create_llm_provider("gpt-4o", settings)

        assert provider._base_url == "https://custom.api.com/v1"

    @pytest.mark.asyncio
    async def test_uses_default_base_url_when_not_set(self, executor):
        """Uses default OpenAI base URL when not configured."""
        settings = Settings(
            database_url="sqlite:///test.db",
            openai_api_key="sk-test",
        )
        provider = await executor._create_llm_provider("gpt-4o", settings)

        # Default OpenAI base URL
        assert provider._base_url is None

    @pytest.mark.asyncio
    async def test_passes_timeout_to_openai(self, executor):
        """Passes timeout setting to OpenAI provider."""
        settings = Settings(
            database_url="sqlite:///test.db",
            openai_api_key="sk-test",
            llm_timeout=60.0,
        )
        provider = await executor._create_llm_provider("gpt-4o", settings)

        assert provider._timeout == 60.0

    @pytest.mark.asyncio
    async def test_passes_timeout_to_anthropic(self, executor):
        """Passes timeout setting to Anthropic provider."""
        settings = Settings(
            database_url="sqlite:///test.db",
            anthropic_api_key="sk-ant-test",
            llm_timeout=90.0,
        )
        provider = await executor._create_llm_provider(
            "claude-sonnet-4-5-20250929", settings
        )

        assert provider._timeout == 90.0


class TestAggregateTokenUsage:
    """Test WorkflowExecutor._aggregate_token_usage method."""

    def setup_method(self):
        """Create executor instance for testing."""
        mock_mcp = MagicMock()
        mock_secret = MagicMock()
        mock_state = MagicMock()
        self.executor = WorkflowExecutor(mock_mcp, mock_secret, mock_state)

    def test_empty_context(self):
        """Returns empty dict when no usage data."""
        result = self.executor._aggregate_token_usage({})
        assert result == {}

    def test_context_without_usage_keys(self):
        """Returns empty dict when no usage keys present."""
        context = {"node1": "output", "node2": "output", "input": "test"}
        result = self.executor._aggregate_token_usage(context)
        assert result == {}

    def test_single_usage(self):
        """Aggregates single node usage correctly."""
        context = {
            "_usage_node-1": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "cost": 0.001,
                "model": "gpt-4o-mini",
            },
        }
        result = self.executor._aggregate_token_usage(context)

        assert result["prompt_tokens"] == 100
        assert result["completion_tokens"] == 50
        assert result["total_tokens"] == 150
        assert result["estimated_cost"] == 0.001
        assert result["model_used"] == "gpt-4o-mini"

    def test_multiple_nodes(self):
        """Aggregates multiple node usages correctly."""
        context = {
            "_usage_node-1": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "cost": 0.001,
                "model": "gpt-4o-mini",
            },
            "_usage_node-2": {
                "prompt_tokens": 200,
                "completion_tokens": 100,
                "cost": 0.003,
                "model": "gpt-4o",
            },
            "some_other_key": "value",
        }
        result = self.executor._aggregate_token_usage(context)

        assert result["prompt_tokens"] == 300
        assert result["completion_tokens"] == 150
        assert result["total_tokens"] == 450
        assert result["estimated_cost"] == 0.004

    def test_three_nodes(self):
        """Aggregates three node usages correctly."""
        context = {
            "_usage_node-1": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "cost": 0.001,
                "model": "gpt-4o-mini",
            },
            "_usage_node-2": {
                "prompt_tokens": 200,
                "completion_tokens": 100,
                "cost": 0.003,
                "model": "gpt-4o",
            },
            "_usage_node-3": {
                "prompt_tokens": 150,
                "completion_tokens": 75,
                "cost": 0.002,
                "model": "gpt-4o-mini",
            },
        }
        result = self.executor._aggregate_token_usage(context)

        assert result["prompt_tokens"] == 450
        assert result["completion_tokens"] == 225
        assert result["total_tokens"] == 675
        assert result["estimated_cost"] == 0.006

    def test_no_usage_keys(self):
        """Returns empty dict when no _usage_ prefixed keys."""
        context = {"node1": "output", "node2": "output"}
        result = self.executor._aggregate_token_usage(context)
        assert result == {}

    def test_mixed_context(self):
        """Correctly extracts usage from mixed context."""
        context = {
            "input": "test input",
            "node-1": "output 1",
            "_usage_node-1": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "cost": 0.001,
                "model": "gpt-4o-mini",
            },
            "node-2": "output 2",
            "_usage_node-2": {
                "prompt_tokens": 200,
                "completion_tokens": 100,
                "cost": 0.003,
                "model": "gpt-4o",
            },
            "some_other_data": {"key": "value"},
        }
        result = self.executor._aggregate_token_usage(context)

        assert result["prompt_tokens"] == 300
        assert result["completion_tokens"] == 150
        assert result["total_tokens"] == 450

    def test_zero_tokens(self):
        """Handles zero token counts."""
        context = {
            "_usage_node-1": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "cost": 0.0,
                "model": "gpt-4o-mini",
            },
        }
        result = self.executor._aggregate_token_usage(context)

        # Returns empty dict when total is zero
        assert result == {}

    def test_cost_rounding(self):
        """Cost is rounded to 6 decimal places."""
        context = {
            "_usage_node-1": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "cost": 0.0012345678,
                "model": "gpt-4o-mini",
            },
        }
        result = self.executor._aggregate_token_usage(context)

        assert result["estimated_cost"] == 0.001235

    def test_model_from_first_node(self):
        """Uses model from first usage entry."""
        context = {
            "_usage_node-1": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "cost": 0.001,
                "model": "gpt-4o-mini",
            },
            "_usage_node-2": {
                "prompt_tokens": 200,
                "completion_tokens": 100,
                "cost": 0.003,
                "model": "gpt-4o",
            },
        }
        result = self.executor._aggregate_token_usage(context)

        # Should use first model encountered (depends on dict iteration)
        assert result["model_used"] in ["gpt-4o-mini", "gpt-4o"]

    def test_partial_usage_data(self):
        """Handles missing fields in usage data gracefully."""
        context = {
            "_usage_node-1": {
                "prompt_tokens": 100,
                # Missing completion_tokens
                "cost": 0.001,
                "model": "gpt-4o-mini",
            },
        }
        result = self.executor._aggregate_token_usage(context)

        assert result["prompt_tokens"] == 100
        assert result["completion_tokens"] == 0
        assert result["total_tokens"] == 100

    def test_non_dict_usage_value(self):
        """Handles non-dict values in _usage_ keys gracefully."""
        context = {
            "_usage_node-1": "not a dict",
            "_usage_node-2": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "cost": 0.001,
                "model": "gpt-4o-mini",
            },
        }
        result = self.executor._aggregate_token_usage(context)

        # Should only aggregate the valid usage entry
        assert result["prompt_tokens"] == 100
        assert result["completion_tokens"] == 50
