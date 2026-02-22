"""Tests for LLM API endpoints."""
import pytest
import pytest_asyncio
import uuid
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.llm import router, OPENAI_MODELS, ANTHROPIC_MODELS, OLLAMA_MODELS, GEMINI_MODELS
from app.config import Settings
from app.auth import get_current_user
from app.auth.jwt import User


def create_mock_user() -> User:
    """Factory function to create mock user."""
    return User(
        id=str(uuid.uuid4()),
        email="test@example.com",
        role="admin",
    )


def create_mock_secret_store():
    """Create mock secret store for testing."""
    mock_store = AsyncMock()
    # Default: return None for all secret lookups (no user keys)
    mock_store.get.return_value = None
    mock_store.set.return_value = None
    mock_store.delete.return_value = None
    return mock_store


@pytest_asyncio.fixture
async def test_app_no_keys(monkeypatch):
    """Create FastAPI test app with no API keys configured."""
    app = FastAPI()
    app.include_router(router)

    # Add mock secret_store to app state
    app.state.secret_store = create_mock_secret_store()

    # Override dependencies
    def override_get_current_user():
        return create_mock_user()

    app.dependency_overrides[get_current_user] = override_get_current_user

    # Patch get_settings to return test settings
    test_settings = Settings(database_url="sqlite:///test.db")
    monkeypatch.setattr("app.api.llm.get_settings", lambda: test_settings)

    return app


@pytest_asyncio.fixture
async def test_app_with_openai(monkeypatch):
    """Create FastAPI test app with OpenAI key configured."""
    app = FastAPI()
    app.include_router(router)

    # Add mock secret_store to app state
    app.state.secret_store = create_mock_secret_store()

    def override_get_current_user():
        return create_mock_user()

    app.dependency_overrides[get_current_user] = override_get_current_user

    # Patch get_settings to return test settings with OpenAI key
    test_settings = Settings(
        database_url="sqlite:///test.db",
        openai_api_key="sk-test123",
    )
    monkeypatch.setattr("app.api.llm.get_settings", lambda: test_settings)

    return app


@pytest_asyncio.fixture
async def test_app_with_both(monkeypatch):
    """Create FastAPI test app with both API keys configured."""
    app = FastAPI()
    app.include_router(router)

    # Add mock secret_store to app state
    app.state.secret_store = create_mock_secret_store()

    def override_get_current_user():
        return create_mock_user()

    app.dependency_overrides[get_current_user] = override_get_current_user

    # Patch get_settings to return test settings with both keys
    test_settings = Settings(
        database_url="sqlite:///test.db",
        openai_api_key="sk-test123",
        anthropic_api_key="sk-ant-test",
    )
    monkeypatch.setattr("app.api.llm.get_settings", lambda: test_settings)

    return app


class TestListProviders:
    """Test GET /api/llm/providers endpoint."""

    def test_lists_providers_no_keys(self, test_app_no_keys):
        """Lists all providers but API-key ones not configured when no keys."""
        client = TestClient(test_app_no_keys)
        resp = client.get("/api/llm/providers")

        assert resp.status_code == 200
        data = resp.json()

        assert "providers" in data
        assert "defaultModel" in data
        assert len(data["providers"]) == 4

        provider_names = {p["name"] for p in data["providers"]}
        assert "openai" in provider_names
        assert "anthropic" in provider_names
        assert "ollama" in provider_names
        assert "google" in provider_names

        # OpenAI and Anthropic should not be configured, Ollama always is
        openai_p = next(p for p in data["providers"] if p["name"] == "openai")
        assert openai_p["configured"] is False
        anthropic_p = next(p for p in data["providers"] if p["name"] == "anthropic")
        assert anthropic_p["configured"] is False
        ollama_p = next(p for p in data["providers"] if p["name"] == "ollama")
        assert ollama_p["configured"] is True

    def test_lists_providers_with_openai(self, test_app_with_openai):
        """OpenAI provider shows as configured when key present."""
        client = TestClient(test_app_with_openai)
        resp = client.get("/api/llm/providers")

        assert resp.status_code == 200
        data = resp.json()

        # Find OpenAI provider
        openai_p = next(p for p in data["providers"] if p["name"] == "openai")
        assert openai_p["configured"] is True
        assert len(openai_p["models"]) > 0

        # Find Anthropic provider
        anthropic_p = next(p for p in data["providers"] if p["name"] == "anthropic")
        assert anthropic_p["configured"] is False

    def test_lists_providers_with_both(self, test_app_with_both):
        """OpenAI, Anthropic, and Ollama show as configured when both API keys present."""
        client = TestClient(test_app_with_both)
        resp = client.get("/api/llm/providers")

        assert resp.status_code == 200
        data = resp.json()

        # OpenAI, Anthropic, Ollama configured. Google not.
        configured = [p for p in data["providers"] if p["configured"]]
        assert len(configured) == 3

    def test_providers_have_models(self, test_app_no_keys):
        """Each provider lists its available models."""
        client = TestClient(test_app_no_keys)
        resp = client.get("/api/llm/providers")

        data = resp.json()
        for provider in data["providers"]:
            assert "models" in provider
            assert isinstance(provider["models"], list)
            assert len(provider["models"]) > 0

    def test_default_model_returned(self, test_app_no_keys):
        """Response includes default model."""
        client = TestClient(test_app_no_keys)
        resp = client.get("/api/llm/providers")

        data = resp.json()
        assert data["defaultModel"] == "gpt-4o-mini"


class TestListModels:
    """Test GET /api/llm/models endpoint."""

    def test_lists_all_models_no_keys(self, test_app_no_keys):
        """Lists Ollama models when no API keys configured."""
        client = TestClient(test_app_no_keys)
        resp = client.get("/api/llm/models")

        assert resp.status_code == 200
        data = resp.json()

        assert "models" in data
        assert len(data["models"]) > 0

        # When no keys configured, only Ollama models returned (always available)
        assert len(data["models"]) == len(OLLAMA_MODELS)

        # All should be Ollama models
        assert all(m["provider"] == "ollama" for m in data["models"])

    def test_model_fields(self, test_app_with_both):
        """Each model has all required fields."""
        client = TestClient(test_app_with_both)
        resp = client.get("/api/llm/models")

        data = resp.json()
        assert len(data["models"]) > 0

        model = data["models"][0]
        assert "id" in model
        assert "provider" in model
        assert "displayName" in model
        assert "contextWindow" in model
        assert "costPer1kInput" in model
        assert "costPer1kOutput" in model

        # Validate types
        assert isinstance(model["id"], str)
        assert isinstance(model["provider"], str)
        assert isinstance(model["displayName"], str)
        assert isinstance(model["contextWindow"], int)
        assert isinstance(model["costPer1kInput"], float)
        assert isinstance(model["costPer1kOutput"], float)

    def test_openai_models_present(self, test_app_with_openai):
        """OpenAI models are in the list when API key configured."""
        client = TestClient(test_app_with_openai)
        resp = client.get("/api/llm/models")

        data = resp.json()
        openai_models = [m for m in data["models"] if m["provider"] == "openai"]

        assert len(openai_models) == len(OPENAI_MODELS)

        # Check for key OpenAI models
        model_ids = {m["id"] for m in openai_models}
        assert "gpt-4o" in model_ids
        assert "gpt-4o-mini" in model_ids
        assert "o1" in model_ids
        assert "o1-mini" in model_ids

    def test_anthropic_models_present(self, test_app_with_both):
        """Anthropic models are in the list when API key configured."""
        client = TestClient(test_app_with_both)
        resp = client.get("/api/llm/models")

        data = resp.json()
        anthropic_models = [m for m in data["models"] if m["provider"] == "anthropic"]

        assert len(anthropic_models) == len(ANTHROPIC_MODELS)

        # Check for key Anthropic models
        model_ids = {m["id"] for m in anthropic_models}
        assert "claude-sonnet-4-5-20250929" in model_ids
        assert "claude-haiku-4-5-20251001" in model_ids
        assert "claude-opus-4-6" in model_ids

    def test_models_have_pricing(self, test_app_no_keys):
        """All models have pricing information."""
        client = TestClient(test_app_no_keys)
        resp = client.get("/api/llm/models")

        data = resp.json()

        for model in data["models"]:
            assert model["costPer1kInput"] >= 0
            assert model["costPer1kOutput"] >= 0
            assert model["contextWindow"] > 0

    def test_context_window_sizes(self, test_app_no_keys):
        """Models have realistic context window sizes."""
        client = TestClient(test_app_no_keys)
        resp = client.get("/api/llm/models")

        data = resp.json()

        for model in data["models"]:
            # Context windows should be reasonable (at least 8k, at most 2M for Gemini)
            assert 8000 <= model["contextWindow"] <= 2000000


class TestLLMKeyManagement:
    """Test LLM API key management endpoints."""

    def test_get_key_status_no_keys(self, test_app_no_keys):
        """Get key status when no keys configured."""
        client = TestClient(test_app_no_keys)
        resp = client.get("/api/llm/keys")

        assert resp.status_code == 200
        data = resp.json()

        assert "keys" in data
        assert len(data["keys"]) == 4  # openai, anthropic, google, ollama

        # Check all providers are present
        provider_names = {k["provider"] for k in data["keys"]}
        assert provider_names == {"openai", "anthropic", "google", "ollama"}

        # No server keys except Ollama
        for key_status in data["keys"]:
            if key_status["provider"] == "ollama":
                assert key_status["hasServerKey"] is True
                assert key_status["configured"] is True
            else:
                assert key_status["hasServerKey"] is False
                assert key_status["hasUserKey"] is False
                assert key_status["configured"] is False

    def test_get_key_status_with_server_keys(self, test_app_with_both):
        """Get key status when server keys are configured."""
        client = TestClient(test_app_with_both)
        resp = client.get("/api/llm/keys")

        assert resp.status_code == 200
        data = resp.json()

        # OpenAI and Anthropic should have server keys
        openai_status = next(k for k in data["keys"] if k["provider"] == "openai")
        assert openai_status["hasServerKey"] is True
        assert openai_status["configured"] is True

        anthropic_status = next(k for k in data["keys"] if k["provider"] == "anthropic")
        assert anthropic_status["hasServerKey"] is True
        assert anthropic_status["configured"] is True

    def test_get_key_status_with_user_keys(self, test_app_no_keys):
        """Get key status when user has stored keys."""
        # Set up mock to return user key for OpenAI
        test_app_no_keys.state.secret_store.get.return_value = "user-key-123"

        client = TestClient(test_app_no_keys)
        resp = client.get("/api/llm/keys")

        assert resp.status_code == 200
        data = resp.json()

        # All providers should show user keys (mock returns same for all)
        for key_status in data["keys"]:
            if key_status["provider"] == "ollama":
                # Ollama always configured
                assert key_status["configured"] is True
            else:
                # Others have user keys
                assert key_status["hasUserKey"] is True
                assert key_status["configured"] is True

    def test_set_key_success(self, test_app_no_keys):
        """Successfully set a user API key."""
        client = TestClient(test_app_no_keys)
        resp = client.put(
            "/api/llm/keys/openai",
            json={"apiKey": "sk-user-test-key"},
        )

        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

        # Verify secret_store.set was called
        test_app_no_keys.state.secret_store.set.assert_called_once()

    def test_set_key_invalid_provider(self, test_app_no_keys):
        """Setting key for invalid provider fails."""
        client = TestClient(test_app_no_keys)
        resp = client.put(
            "/api/llm/keys/invalid-provider",
            json={"apiKey": "some-key"},
        )

        assert resp.status_code == 400
        assert "Invalid provider" in resp.json()["detail"]

    def test_set_key_empty_key(self, test_app_no_keys):
        """Setting empty key fails validation."""
        client = TestClient(test_app_no_keys)
        resp = client.put(
            "/api/llm/keys/openai",
            json={"apiKey": ""},
        )

        assert resp.status_code == 422  # Validation error

    def test_delete_key_success(self, test_app_no_keys):
        """Successfully delete a user API key."""
        client = TestClient(test_app_no_keys)
        resp = client.delete("/api/llm/keys/anthropic")

        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

        # Verify secret_store.delete was called
        test_app_no_keys.state.secret_store.delete.assert_called_once()

    def test_delete_key_invalid_provider(self, test_app_no_keys):
        """Deleting key for invalid provider fails."""
        client = TestClient(test_app_no_keys)
        resp = client.delete("/api/llm/keys/invalid-provider")

        assert resp.status_code == 400
        assert "Invalid provider" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_validate_openai_key_valid(self, test_app_no_keys):
        """Validate a valid OpenAI API key."""
        with patch("httpx.AsyncClient") as mock_client_class:
            # Mock successful response
            mock_response = AsyncMock()
            mock_response.status_code = 200

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            client = TestClient(test_app_no_keys)
            resp = client.post(
                "/api/llm/keys/openai/validate",
                json={"apiKey": "sk-valid-key"},
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data["valid"] is True
            assert data["error"] is None

    @pytest.mark.asyncio
    async def test_validate_openai_key_invalid(self, test_app_no_keys):
        """Validate an invalid OpenAI API key."""
        with patch("httpx.AsyncClient") as mock_client_class:
            # Mock 401 unauthorized response
            mock_response = AsyncMock()
            mock_response.status_code = 401

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            client = TestClient(test_app_no_keys)
            resp = client.post(
                "/api/llm/keys/openai/validate",
                json={"apiKey": "sk-invalid-key"},
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data["valid"] is False
            assert "Invalid API key" in data["error"]

    @pytest.mark.asyncio
    async def test_validate_anthropic_key_valid(self, test_app_no_keys):
        """Validate a valid Anthropic API key."""
        with patch("httpx.AsyncClient") as mock_client_class:
            # Mock 400 response (valid key, bad request body is ok)
            mock_response = AsyncMock()
            mock_response.status_code = 400

            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            client = TestClient(test_app_no_keys)
            resp = client.post(
                "/api/llm/keys/anthropic/validate",
                json={"apiKey": "sk-ant-valid"},
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data["valid"] is True

    @pytest.mark.asyncio
    async def test_validate_anthropic_key_invalid(self, test_app_no_keys):
        """Validate an invalid Anthropic API key."""
        with patch("httpx.AsyncClient") as mock_client_class:
            # Mock 401 unauthorized response
            mock_response = AsyncMock()
            mock_response.status_code = 401

            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            client = TestClient(test_app_no_keys)
            resp = client.post(
                "/api/llm/keys/anthropic/validate",
                json={"apiKey": "sk-ant-invalid"},
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data["valid"] is False
            assert "Invalid API key" in data["error"]

    @pytest.mark.asyncio
    async def test_validate_key_connection_error(self, test_app_no_keys):
        """Handle connection errors during key validation."""
        with patch("httpx.AsyncClient") as mock_client_class:
            # Mock connection error
            import httpx
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("Connection failed")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            client = TestClient(test_app_no_keys)
            resp = client.post(
                "/api/llm/keys/openai/validate",
                json={"apiKey": "sk-test"},
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data["valid"] is False
            assert "Connection failed" in data["error"]

    def test_validate_key_invalid_provider(self, test_app_no_keys):
        """Validating key for invalid provider fails."""
        client = TestClient(test_app_no_keys)
        resp = client.post(
            "/api/llm/keys/invalid-provider/validate",
            json={"apiKey": "some-key"},
        )

        assert resp.status_code == 400
        assert "Invalid provider" in resp.json()["detail"]
