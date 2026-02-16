"""Unit tests for LLM Provider Registry.

Tests provider registration, detection, creation, and default registry.
"""

from unittest.mock import MagicMock

import pytest

import agentweave.llm.registry as registry_module
from agentweave.errors.exceptions import ModelNotFoundError
from agentweave.llm.registry import ProviderInfo, ProviderRegistry, get_registry


class TestProviderRegistration:
    """Test provider registration and unregistration."""

    def test_register_provider(self):
        """Register a provider and verify it's listed."""
        registry = ProviderRegistry()
        factory = MagicMock()

        registry.register(
            name="test_provider",
            factory=factory,
            prefixes=["test-"],
            default_cost_input=0.01,
            default_cost_output=0.02,
        )

        assert "test_provider" in registry.list_providers()

    def test_unregister_provider(self):
        """Register, unregister, verify gone."""
        registry = ProviderRegistry()
        factory = MagicMock()

        registry.register("test_provider", factory, ["test-"])
        assert "test_provider" in registry.list_providers()

        result = registry.unregister("test_provider")
        assert result is True
        assert "test_provider" not in registry.list_providers()

    def test_unregister_nonexistent(self):
        """Unregistering nonexistent provider returns False."""
        registry = ProviderRegistry()
        result = registry.unregister("nonexistent")
        assert result is False

    def test_get_provider_info(self):
        """Register and retrieve provider info."""
        registry = ProviderRegistry()
        factory = MagicMock()

        registry.register(
            name="test_provider",
            factory=factory,
            prefixes=["test-", "tst-"],
            default_cost_input=0.05,
            default_cost_output=0.10,
        )

        info = registry.get_provider_info("test_provider")
        assert info is not None
        assert info.name == "test_provider"
        assert info.factory is factory
        assert info.prefixes == ["test-", "tst-"]
        assert info.default_cost_input == 0.05
        assert info.default_cost_output == 0.10


class TestProviderDetection:
    """Test provider detection from model names."""

    def test_detect_openai_gpt(self):
        """Detect OpenAI from gpt- prefix."""
        registry = ProviderRegistry()
        factory = MagicMock()
        registry.register("openai", factory, ["gpt-", "o1"])

        result = registry.detect_provider("gpt-4o")
        assert result == "openai"

    def test_detect_openai_o1(self):
        """Detect OpenAI from o1 prefix."""
        registry = ProviderRegistry()
        factory = MagicMock()
        registry.register("openai", factory, ["gpt-", "o1"])

        result = registry.detect_provider("o1-mini")
        assert result == "openai"

    def test_detect_anthropic(self):
        """Detect Anthropic from claude- prefix."""
        registry = ProviderRegistry()
        factory = MagicMock()
        registry.register("anthropic", factory, ["claude-"])

        result = registry.detect_provider("claude-3-5-sonnet")
        assert result == "anthropic"

    def test_detect_ollama(self):
        """Detect Ollama from ollama/ prefix."""
        registry = ProviderRegistry()
        factory = MagicMock()
        registry.register("ollama", factory, ["ollama/"])

        result = registry.detect_provider("ollama/llama3.2")
        assert result == "ollama"

    def test_detect_unknown_raises(self):
        """Unknown model raises ModelNotFoundError."""
        registry = ProviderRegistry()
        factory = MagicMock()
        registry.register("openai", factory, ["gpt-"])

        with pytest.raises(ModelNotFoundError):
            registry.detect_provider("unknown-model")

    def test_longest_prefix_wins(self):
        """When multiple prefixes match, longest prefix wins."""
        registry = ProviderRegistry()
        factory1 = MagicMock()
        factory2 = MagicMock()

        # Register provider with shorter prefix
        registry.register("provider1", factory1, ["gpt-"])
        # Register provider with longer prefix (subset of the first)
        registry.register("provider2", factory2, ["gpt-4-"])

        # Should match the longer prefix
        result = registry.detect_provider("gpt-4-turbo")
        assert result == "provider2"

        # Should still match the shorter prefix for other models
        result = registry.detect_provider("gpt-3.5-turbo")
        assert result == "provider1"


class TestProviderCreation:
    """Test provider instance creation."""

    def test_create_provider_calls_factory(self):
        """Create provider calls factory with model."""
        registry = ProviderRegistry()
        factory = MagicMock()
        registry.register("test_provider", factory, ["test-"])

        registry.create_provider("test-model")

        factory.assert_called_once()
        call_kwargs = factory.call_args.kwargs
        assert call_kwargs["model"] == "test-model"

    def test_create_provider_passes_kwargs(self):
        """Create provider forwards additional kwargs to factory."""
        registry = ProviderRegistry()
        factory = MagicMock()
        registry.register("test_provider", factory, ["test-"])

        registry.create_provider(
            "test-model",
            api_key="secret",
            timeout=30,
            custom_param="value"
        )

        factory.assert_called_once()
        call_kwargs = factory.call_args.kwargs
        assert call_kwargs["model"] == "test-model"
        assert call_kwargs["api_key"] == "secret"
        assert call_kwargs["timeout"] == 30
        assert call_kwargs["custom_param"] == "value"


class TestDefaultRegistry:
    """Test default registry singleton and built-in providers."""

    def setup_method(self):
        """Reset default registry before each test."""
        registry_module._default_registry = None

    def teardown_method(self):
        """Reset default registry after each test."""
        registry_module._default_registry = None

    def test_get_registry_returns_singleton(self):
        """Calling get_registry() twice returns same instance."""
        registry1 = get_registry()
        registry2 = get_registry()
        assert registry1 is registry2

    def test_default_has_openai(self):
        """Default registry detects OpenAI models."""
        registry = get_registry()
        result = registry.detect_provider("gpt-4o")
        assert result == "openai"

    def test_default_has_anthropic(self):
        """Default registry detects Anthropic models."""
        registry = get_registry()
        result = registry.detect_provider("claude-3-5-sonnet")
        assert result == "anthropic"

    def test_default_has_ollama(self):
        """Default registry detects Ollama models."""
        registry = get_registry()
        result = registry.detect_provider("ollama/llama3.2")
        assert result == "ollama"

    def test_list_default_providers(self):
        """Default registry has all built-in providers."""
        registry = get_registry()
        providers = registry.list_providers()
        assert set(providers) == {"openai", "anthropic", "ollama", "gemini"}
