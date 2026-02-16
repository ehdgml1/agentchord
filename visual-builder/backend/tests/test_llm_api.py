"""Tests for LLM API endpoints."""
import pytest
import pytest_asyncio
import uuid
from unittest.mock import patch
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


@pytest_asyncio.fixture
async def test_app_no_keys(monkeypatch):
    """Create FastAPI test app with no API keys configured."""
    app = FastAPI()
    app.include_router(router)

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
