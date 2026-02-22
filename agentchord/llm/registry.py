"""LLM Provider Registry.

Manages provider registration and auto-detection from model names.
Replaces the hardcoded _detect_provider/_create_provider pattern.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from agentchord.errors.exceptions import ModelNotFoundError
from agentchord.llm.base import BaseLLMProvider


@dataclass
class ProviderInfo:
    """Information about a registered LLM provider."""

    name: str
    factory: Callable[..., BaseLLMProvider]
    prefixes: list[str]
    default_cost_input: float = 0.0
    default_cost_output: float = 0.0


class ProviderRegistry:
    """Registry for managing LLM provider registration and auto-detection.

    Example:
        >>> registry = ProviderRegistry()
        >>> registry.register("openai", factory_fn, ["gpt-", "o1"])
        >>> provider = registry.create_provider("gpt-4o")
    """

    def __init__(self) -> None:
        self._providers: dict[str, ProviderInfo] = {}
        self._prefix_map: list[tuple[str, str]] = []  # (prefix, provider_name), sorted by length desc

    def register(
        self,
        name: str,
        factory: Callable[..., BaseLLMProvider],
        prefixes: list[str],
        default_cost_input: float = 0.0,
        default_cost_output: float = 0.0,
    ) -> None:
        """Register a provider with its factory and model prefixes."""
        info = ProviderInfo(
            name=name,
            factory=factory,
            prefixes=prefixes,
            default_cost_input=default_cost_input,
            default_cost_output=default_cost_output,
        )
        self._providers[name] = info
        self._rebuild_prefix_map()

    def unregister(self, name: str) -> bool:
        """Remove a provider. Returns True if found."""
        if name not in self._providers:
            return False
        del self._providers[name]
        self._rebuild_prefix_map()
        return True

    def _rebuild_prefix_map(self) -> None:
        """Rebuild prefix map sorted by longest prefix first."""
        pairs: list[tuple[str, str]] = []
        for info in self._providers.values():
            for prefix in info.prefixes:
                pairs.append((prefix, info.name))
        self._prefix_map = sorted(pairs, key=lambda p: len(p[0]), reverse=True)

    def detect_provider(self, model: str) -> str:
        """Detect provider name from model string using prefix matching."""
        for prefix, provider_name in self._prefix_map:
            if model.startswith(prefix):
                return provider_name
        raise ModelNotFoundError(model)

    def create_provider(self, model: str, **kwargs: Any) -> BaseLLMProvider:
        """Create a provider instance for the given model."""
        provider_name = self.detect_provider(model)
        info = self._providers[provider_name]
        return info.factory(model=model, **kwargs)

    def list_providers(self) -> list[str]:
        """List all registered provider names."""
        return list(self._providers.keys())

    def get_provider_info(self, name: str) -> ProviderInfo | None:
        """Get provider info by name."""
        return self._providers.get(name)


_default_registry: ProviderRegistry | None = None


def get_registry() -> ProviderRegistry:
    """Get the default provider registry, creating it lazily with built-in providers."""
    global _default_registry
    if _default_registry is None:
        _default_registry = ProviderRegistry()
        _register_defaults(_default_registry)
    return _default_registry


def _register_defaults(registry: ProviderRegistry) -> None:
    """Register built-in providers with lazy imports."""

    def _create_openai(**kwargs: Any) -> BaseLLMProvider:
        from agentchord.llm.openai import OpenAIProvider
        return OpenAIProvider(**kwargs)

    def _create_anthropic(**kwargs: Any) -> BaseLLMProvider:
        from agentchord.llm.anthropic import AnthropicProvider
        return AnthropicProvider(**kwargs)

    def _create_ollama(**kwargs: Any) -> BaseLLMProvider:
        from agentchord.llm.ollama import OllamaProvider
        return OllamaProvider(**kwargs)

    def _create_gemini(**kwargs: Any) -> BaseLLMProvider:
        from agentchord.llm.gemini import GeminiProvider
        return GeminiProvider(**kwargs)

    registry.register(
        name="openai",
        factory=_create_openai,
        prefixes=["gpt-", "o1", "text-"],
        default_cost_input=0.01,
        default_cost_output=0.03,
    )
    registry.register(
        name="anthropic",
        factory=_create_anthropic,
        prefixes=["claude-"],
        default_cost_input=0.003,
        default_cost_output=0.015,
    )
    registry.register(
        name="ollama",
        factory=_create_ollama,
        prefixes=["ollama/"],
        default_cost_input=0.0,
        default_cost_output=0.0,
    )
    registry.register(
        name="gemini",
        factory=_create_gemini,
        prefixes=["gemini-"],
        default_cost_input=0.0001,
        default_cost_output=0.0004,
    )
