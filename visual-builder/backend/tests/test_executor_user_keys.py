"""Tests for executor user key fallback and Gemini embedding creation.

This test suite verifies:
1. LLM provider creation with user key fallback (env → DB → ValueError)
2. Embedding provider creation with user key fallback
3. Gemini embedding provider creation
4. Per-node embedding parameter override
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.executor import WorkflowExecutor
from app.config import Settings


@pytest.fixture
def mock_secret_store():
    """Create mock secret store for DB key lookup."""
    store = AsyncMock()
    store.get = AsyncMock(return_value=None)
    return store


@pytest.fixture
def mock_state_store():
    """Create mock state store."""
    return AsyncMock()


@pytest.fixture
def mock_mcp_manager():
    """Create mock MCP manager."""
    return AsyncMock()


@pytest.fixture
def executor(mock_mcp_manager, mock_secret_store, mock_state_store):
    """Create executor with mock secret store."""
    executor = WorkflowExecutor(
        mcp_manager=mock_mcp_manager,
        secret_store=mock_secret_store,
        state_store=mock_state_store,
    )
    return executor


class TestLLMProviderUserKeyFallback:
    """Test LLM provider creation with user key fallback."""

    @pytest.mark.asyncio
    async def test_llm_provider_uses_env_key_when_available(self, executor, mock_secret_store):
        """When settings.openai_api_key is set, uses it (no DB lookup)."""
        settings = Settings(
            database_url="sqlite:///test.db",
            openai_api_key="sk-env-key-123",
        )

        provider = await executor._create_llm_provider("gpt-4o", settings, user_id="user-1")

        assert provider.model == "gpt-4o"
        assert provider._api_key == "sk-env-key-123"
        # DB should NOT be called when env key available
        mock_secret_store.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_llm_provider_falls_back_to_db_key(self, executor, mock_secret_store):
        """When settings key is None, looks up LLM_OPENAI_API_KEY from DB."""
        settings = Settings(
            database_url="sqlite:///test.db",
            openai_api_key="",
        )
        mock_secret_store.get.return_value = "sk-db-key-123"

        provider = await executor._create_llm_provider("gpt-4o", settings, user_id="user-1")

        assert provider.model == "gpt-4o"
        assert provider._api_key == "sk-db-key-123"
        mock_secret_store.get.assert_called_once_with("LLM_OPENAI_API_KEY", owner_id="user-1")

    @pytest.mark.asyncio
    async def test_llm_provider_db_key_anthropic(self, executor, mock_secret_store):
        """For Anthropic model (claude-*), looks up LLM_ANTHROPIC_API_KEY."""
        settings = Settings(
            database_url="sqlite:///test.db",
            anthropic_api_key="",
        )
        mock_secret_store.get.return_value = "sk-ant-db-key-456"

        provider = await executor._create_llm_provider(
            "claude-sonnet-4-5-20250929", settings, user_id="user-2"
        )

        assert provider.model == "claude-sonnet-4-5-20250929"
        assert provider._api_key == "sk-ant-db-key-456"
        mock_secret_store.get.assert_called_once_with("LLM_ANTHROPIC_API_KEY", owner_id="user-2")

    @pytest.mark.asyncio
    async def test_llm_provider_db_key_gemini(self, executor, mock_secret_store):
        """For Gemini model (gemini-*), looks up LLM_GEMINI_API_KEY."""
        settings = Settings(
            database_url="sqlite:///test.db",
            gemini_api_key="",
        )
        mock_secret_store.get.return_value = "sk-gemini-db-key-789"

        provider = await executor._create_llm_provider("gemini-2.0-flash", settings, user_id="user-3")

        assert provider.model == "gemini-2.0-flash"
        assert provider._api_key == "sk-gemini-db-key-789"
        mock_secret_store.get.assert_called_once_with("LLM_GEMINI_API_KEY", owner_id="user-3")

    @pytest.mark.asyncio
    async def test_llm_provider_no_key_raises(self, executor, mock_secret_store):
        """When neither env nor DB key available, raises ValueError."""
        settings = Settings(
            database_url="sqlite:///test.db",
            openai_api_key="",
        )
        # No user_id provided, so no DB lookup happens
        mock_secret_store.get.return_value = None

        with pytest.raises(ValueError, match="OpenAI API key not configured"):
            await executor._create_llm_provider("gpt-4o", settings, user_id=None)

    @pytest.mark.asyncio
    async def test_llm_provider_db_key_not_found_raises(self, executor, mock_secret_store):
        """When DB returns None, raises ValueError."""
        settings = Settings(
            database_url="sqlite:///test.db",
            openai_api_key="",
        )
        mock_secret_store.get.return_value = None

        with pytest.raises(ValueError, match="OpenAI API key not configured"):
            await executor._create_llm_provider("gpt-4o", settings, user_id="user-4")

        mock_secret_store.get.assert_called_once_with("LLM_OPENAI_API_KEY", owner_id="user-4")


class TestEmbeddingProviderUserKeyFallback:
    """Test embedding provider creation with user key fallback."""

    @pytest.mark.asyncio
    async def test_embedding_provider_uses_env_key_when_available(self, executor, mock_secret_store):
        """When settings.openai_api_key is set, uses it (no DB lookup)."""
        settings = Settings(
            database_url="sqlite:///test.db",
            openai_api_key="sk-env-embed-123",
            embedding_provider="openai",
            embedding_model="text-embedding-3-small",
            embedding_dimensions=1536,
        )

        provider = await executor._create_embedding_provider(settings, user_id="user-1")

        assert provider.model_name == "text-embedding-3-small"
        assert provider.dimensions == 1536
        # DB should NOT be called when env key available
        mock_secret_store.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_embedding_provider_falls_back_to_db_key(self, executor, mock_secret_store):
        """When env key is None, looks up LLM_OPENAI_API_KEY from DB."""
        settings = Settings(
            database_url="sqlite:///test.db",
            openai_api_key="",
            embedding_provider="openai",
            embedding_model="text-embedding-3-small",
            embedding_dimensions=1536,
        )
        mock_secret_store.get.return_value = "sk-db-embed-456"

        provider = await executor._create_embedding_provider(settings, user_id="user-2")

        assert provider.model_name == "text-embedding-3-small"
        assert provider.dimensions == 1536
        mock_secret_store.get.assert_called_once_with("LLM_OPENAI_API_KEY", owner_id="user-2")

    @pytest.mark.asyncio
    async def test_embedding_provider_gemini_creation(self, executor, mock_secret_store):
        """When provider='gemini', creates GeminiEmbeddings with correct API key."""
        settings = Settings(
            database_url="sqlite:///test.db",
            gemini_api_key="",
            embedding_provider="gemini",
            embedding_model="gemini-embedding-001",
            embedding_dimensions=3072,
        )
        mock_secret_store.get.return_value = "sk-gemini-embed-789"

        provider = await executor._create_embedding_provider(settings, user_id="user-3")

        assert provider.model_name == "gemini-embedding-001"
        assert provider.dimensions == 3072
        mock_secret_store.get.assert_called_once_with("LLM_GEMINI_API_KEY", owner_id="user-3")

    @pytest.mark.asyncio
    async def test_embedding_provider_per_node_override(self, executor, mock_secret_store):
        """When provider/model/dimensions params passed, uses those instead of settings defaults."""
        settings = Settings(
            database_url="sqlite:///test.db",
            openai_api_key="sk-env-key",
            embedding_provider="openai",
            embedding_model="text-embedding-3-small",
            embedding_dimensions=1536,
        )

        # Per-node override: use Gemini with custom model and dimensions
        mock_secret_store.get.return_value = "sk-gemini-override"
        provider = await executor._create_embedding_provider(
            settings,
            user_id="user-4",
            provider="gemini",
            model="text-embedding-005",
            dimensions=512,
        )

        assert provider.model_name == "text-embedding-005"
        assert provider.dimensions == 512
        mock_secret_store.get.assert_called_once_with("LLM_GEMINI_API_KEY", owner_id="user-4")

    @pytest.mark.asyncio
    async def test_embedding_provider_openai_to_gemini_fallback(self, executor, mock_secret_store):
        """When OpenAI key missing but Gemini key available, falls back to Gemini."""
        settings = Settings(
            database_url="sqlite:///test.db",
            openai_api_key="",
            gemini_api_key="sk-gemini-fallback",
            embedding_provider="openai",
        )
        mock_secret_store.get.return_value = None

        provider = await executor._create_embedding_provider(settings, user_id="user-5")

        # Should fall back to Gemini
        assert provider.model_name == "gemini-embedding-001"
        assert provider.dimensions == 3072

    @pytest.mark.asyncio
    async def test_embedding_provider_no_key_falls_back_to_hash(self, executor, mock_secret_store):
        """When no API key available, falls back to _HashEmbeddingProvider."""
        settings = Settings(
            database_url="sqlite:///test.db",
            openai_api_key="",
            embedding_provider="openai",
        )
        mock_secret_store.get.return_value = None

        provider = await executor._create_embedding_provider(settings, user_id="user-6")

        # Should be hash-based fallback
        assert provider.model_name == "hash-embedding"
        assert provider.dimensions == 32

    @pytest.mark.asyncio
    async def test_embedding_provider_ollama_base_url_fallback(self, executor, mock_secret_store):
        """For Ollama, supports base_url override from DB."""
        settings = Settings(
            database_url="sqlite:///test.db",
            ollama_base_url="http://localhost:11434",
            embedding_provider="ollama",
            embedding_model="nomic-embed-text",
            embedding_dimensions=768,
        )
        mock_secret_store.get.return_value = "http://custom-ollama:11434"

        provider = await executor._create_embedding_provider(settings, user_id="user-6")

        assert provider.model_name == "nomic-embed-text"
        assert provider.dimensions == 768
        mock_secret_store.get.assert_called_once_with("LLM_OLLAMA_BASE_URL", owner_id="user-6")


class TestIntegrationWithExecution:
    """Test integration of user_id passing through execution flow."""

    @pytest.mark.asyncio
    async def test_run_agent_passes_user_id_to_llm_provider(self, executor, mock_secret_store):
        """Verify _run_agent extracts context['_user_id'] and passes to _create_llm_provider."""
        from app.core.executor import WorkflowNode

        mock_secret_store.get.return_value = "sk-user-key-123"

        node = WorkflowNode(
            id="agent-1",
            type="agent",
            data={
                "model": "gpt-4o-mini",
                "systemPrompt": "You are a helpful assistant.",
            },
        )

        # Mock context with user_id and input
        context = {"_user_id": "user-7", "input": "test input"}

        # Patch get_settings to return settings without API key
        # Patch Agent.run to avoid actual LLM call
        with patch("app.config.get_settings") as mock_settings, \
             patch("agentchord.Agent.run") as mock_agent_run, \
             patch.object(executor, '_create_llm_provider', wraps=executor._create_llm_provider) as mock_create:

            mock_settings.return_value = Settings(
                database_url="sqlite:///test.db",
                openai_api_key="",
            )

            # Mock agent response
            mock_response = MagicMock()
            mock_response.output = "Test response"
            mock_agent_run.return_value = mock_response

            result = await executor._run_agent(node, context)

            # Verify user_id was passed to provider creation
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args[0][0] == "gpt-4o-mini"  # model
            # settings is positional arg 1
            assert call_args[1]["user_id"] == "user-7"  # user_id kwarg

        # Verify DB lookup was called with correct owner_id
        mock_secret_store.get.assert_called_with("LLM_OPENAI_API_KEY", owner_id="user-7")
