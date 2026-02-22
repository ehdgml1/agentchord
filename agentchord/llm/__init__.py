"""LLM provider implementations."""

from agentchord.llm.base import BaseLLMProvider
from agentchord.llm.registry import ProviderRegistry, ProviderInfo, get_registry

__all__ = [
    "BaseLLMProvider",
    "ProviderRegistry",
    "ProviderInfo",
    "get_registry",
]

# Lazy imports for optional dependencies
def __getattr__(name: str):
    if name == "OpenAIProvider":
        from agentchord.llm.openai import OpenAIProvider
        return OpenAIProvider
    elif name == "AnthropicProvider":
        from agentchord.llm.anthropic import AnthropicProvider
        return AnthropicProvider
    elif name == "OllamaProvider":
        from agentchord.llm.ollama import OllamaProvider
        return OllamaProvider
    elif name == "GeminiProvider":
        from agentchord.llm.gemini import GeminiProvider
        return GeminiProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
