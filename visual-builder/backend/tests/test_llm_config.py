"""Tests for LLM configuration settings."""
import pytest
from app.config import Settings


class TestLLMConfig:
    """Test LLM configuration in Settings."""

    def test_default_settings(self):
        """Default LLM settings are correct."""
        s = Settings(database_url="sqlite:///test.db")
        assert s.default_llm_model == "gpt-4o-mini"
        assert s.llm_timeout == 120.0
        assert s.llm_max_tokens == 4096
        assert s.llm_temperature == 0.7
        assert s.openai_api_key == ""
        assert s.anthropic_api_key == ""
        assert s.openai_base_url == ""

    def test_available_providers_none(self):
        """Ollama is always available by default (has default base_url)."""
        s = Settings(database_url="sqlite:///test.db")
        assert s.available_providers == ["ollama"]
        assert s.has_llm_keys is False

    def test_available_providers_openai(self):
        """OpenAI available when key is set."""
        s = Settings(database_url="sqlite:///test.db", openai_api_key="sk-test")
        assert "openai" in s.available_providers
        assert s.has_llm_keys is True

    def test_available_providers_anthropic(self):
        """Anthropic available when key is set."""
        s = Settings(database_url="sqlite:///test.db", anthropic_api_key="sk-ant-test")
        assert "anthropic" in s.available_providers
        assert s.has_llm_keys is True

    def test_available_providers_both(self):
        """Both API-key providers plus Ollama available when both keys set."""
        s = Settings(
            database_url="sqlite:///test.db",
            openai_api_key="sk-test",
            anthropic_api_key="sk-ant-test",
        )
        assert len(s.available_providers) == 3
        assert "openai" in s.available_providers
        assert "anthropic" in s.available_providers
        assert "ollama" in s.available_providers

    def test_custom_settings(self):
        """Custom LLM settings can be configured."""
        s = Settings(
            database_url="sqlite:///test.db",
            default_llm_model="claude-sonnet-4-5-20250929",
            llm_timeout=60.0,
            llm_max_tokens=8192,
            llm_temperature=0.3,
        )
        assert s.default_llm_model == "claude-sonnet-4-5-20250929"
        assert s.llm_timeout == 60.0
        assert s.llm_max_tokens == 8192
        assert s.llm_temperature == 0.3

    def test_openai_base_url_custom(self):
        """OpenAI base URL can be customized."""
        s = Settings(
            database_url="sqlite:///test.db",
            openai_api_key="sk-test",
            openai_base_url="https://custom.openai.proxy/v1",
        )
        assert s.openai_base_url == "https://custom.openai.proxy/v1"
        assert "openai" in s.available_providers
