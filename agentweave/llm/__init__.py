"""LLM provider implementations."""

from agentweave.llm.base import BaseLLMProvider
from agentweave.llm.registry import ProviderRegistry, ProviderInfo, get_registry

__all__ = [
    "BaseLLMProvider",
    "ProviderRegistry",
    "ProviderInfo",
    "get_registry",
]

# Lazy imports for optional dependencies
def __getattr__(name: str):
    if name == "OpenAIProvider":
        from agentweave.llm.openai import OpenAIProvider
        return OpenAIProvider
    elif name == "AnthropicProvider":
        from agentweave.llm.anthropic import AnthropicProvider
        return AnthropicProvider
    elif name == "OllamaProvider":
        from agentweave.llm.ollama import OllamaProvider
        return OllamaProvider
    elif name == "GeminiProvider":
        from agentweave.llm.gemini import GeminiProvider
        return GeminiProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
