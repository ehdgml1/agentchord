"""AgentChord - Protocol-First Multi-Agent Framework.

AgentChord provides a simple yet powerful framework for building
multi-agent AI systems with native support for MCP and A2A protocols.

Example:
    >>> from agentchord import Agent
    >>> agent = Agent(name="assistant", role="AI Helper")
    >>> result = agent.run_sync("Hello!")
    >>> print(result.output)

For more examples, see https://github.com/agentchord/agentchord
"""

__version__ = "0.2.0"

# Core exports
from agentchord.core.agent import Agent
from agentchord.core.config import AgentConfig, CostConfig, RetryConfig
from agentchord.core.types import (
    AgentResult,
    LLMResponse,
    Message,
    MessageRole,
    ToolCall,
    Usage,
)
from agentchord.core.state import WorkflowState, WorkflowResult, WorkflowStatus
from agentchord.core.workflow import Workflow
from agentchord.core.executor import MergeStrategy

# Error exports
from agentchord.errors.exceptions import (
    AgentError,
    AgentExecutionError,
    AgentTimeoutError,
    AgentChordError,
    APIError,
    AuthenticationError,
    ConfigurationError,
    CostLimitExceededError,
    InvalidConfigError,
    LLMError,
    MissingAPIKeyError,
    ModelNotFoundError,
    RateLimitError,
    TimeoutError,
    WorkflowError,
    WorkflowExecutionError,
    InvalidFlowError,
    AgentNotFoundInFlowError,
    EmptyWorkflowError,
)

# LLM Provider exports
from agentchord.llm.base import BaseLLMProvider

__all__ = [
    # Version
    "__version__",
    # Core
    "Agent",
    "AgentConfig",
    "CostConfig",
    "RetryConfig",
    # Types
    "AgentResult",
    "LLMResponse",
    "Message",
    "MessageRole",
    "ToolCall",
    "Usage",
    # Workflow
    "Workflow",
    "WorkflowState",
    "WorkflowResult",
    "WorkflowStatus",
    "MergeStrategy",
    # LLM
    "BaseLLMProvider",
    # Errors
    "AgentChordError",
    "ConfigurationError",
    "MissingAPIKeyError",
    "InvalidConfigError",
    "LLMError",
    "RateLimitError",
    "AuthenticationError",
    "APIError",
    "TimeoutError",
    "ModelNotFoundError",
    "AgentError",
    "AgentExecutionError",
    "AgentTimeoutError",
    "CostLimitExceededError",
    "WorkflowError",
    "WorkflowExecutionError",
    "InvalidFlowError",
    "AgentNotFoundInFlowError",
    "EmptyWorkflowError",
    # RAG
    "RAGPipeline",
    "create_rag_tools",
    "Document",
    "Chunk",
    "RAGResponse",
    "RAGEvaluator",
    "EmbeddingProvider",
    "HybridSearch",
    "BM25Search",
    # Orchestration
    "AgentTeam",
]


def __getattr__(name: str):
    """Lazy import for optional components."""
    # LLM Providers
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
    elif name == "ProviderRegistry":
        from agentchord.llm.registry import ProviderRegistry
        return ProviderRegistry
    elif name == "get_registry":
        from agentchord.llm.registry import get_registry
        return get_registry

    # MCP (requires mcp package)
    elif name == "MCPClient":
        from agentchord.protocols.mcp import MCPClient
        return MCPClient
    elif name == "MCPTool":
        from agentchord.protocols.mcp import MCPTool
        return MCPTool

    # A2A
    elif name == "A2AClient":
        from agentchord.protocols.a2a import A2AClient
        return A2AClient
    elif name == "A2AServer":
        from agentchord.protocols.a2a import A2AServer
        return A2AServer
    elif name == "AgentCard":
        from agentchord.protocols.a2a import AgentCard
        return AgentCard

    # Memory
    elif name == "ConversationMemory":
        from agentchord.memory import ConversationMemory
        return ConversationMemory
    elif name == "SemanticMemory":
        from agentchord.memory import SemanticMemory
        return SemanticMemory
    elif name == "WorkingMemory":
        from agentchord.memory import WorkingMemory
        return WorkingMemory
    elif name == "MemoryEntry":
        from agentchord.memory import MemoryEntry
        return MemoryEntry

    # Tracking
    elif name == "CostTracker":
        from agentchord.tracking import CostTracker
        return CostTracker
    elif name == "TokenUsage":
        from agentchord.tracking import TokenUsage
        return TokenUsage
    elif name == "CallbackManager":
        from agentchord.tracking import CallbackManager
        return CallbackManager

    # Resilience
    elif name == "RetryPolicy":
        from agentchord.resilience import RetryPolicy
        return RetryPolicy
    elif name == "CircuitBreaker":
        from agentchord.resilience import CircuitBreaker
        return CircuitBreaker
    elif name == "TimeoutManager":
        from agentchord.resilience import TimeoutManager
        return TimeoutManager
    elif name == "ResilienceConfig":
        from agentchord.resilience import ResilienceConfig
        return ResilienceConfig

    # Tools
    elif name == "Tool":
        from agentchord.tools import Tool
        return Tool
    elif name == "ToolExecutor":
        from agentchord.tools import ToolExecutor
        return ToolExecutor
    elif name == "tool":
        from agentchord.tools import tool
        return tool

    # Logging
    elif name == "get_logger":
        from agentchord.logging import get_logger
        return get_logger
    elif name == "configure_logging":
        from agentchord.logging import configure_logging
        return configure_logging
    elif name == "LogLevel":
        from agentchord.logging import LogLevel
        return LogLevel

    # Streaming
    elif name == "StreamChunk":
        from agentchord.core.types import StreamChunk
        return StreamChunk

    # Structured Output
    elif name == "OutputSchema":
        from agentchord.core.structured import OutputSchema
        return OutputSchema

    # Memory Stores (persistent backends)
    elif name == "MemoryStore":
        from agentchord.memory.stores import MemoryStore
        return MemoryStore
    elif name == "JSONFileStore":
        from agentchord.memory.stores import JSONFileStore
        return JSONFileStore
    elif name == "SQLiteStore":
        from agentchord.memory.stores import SQLiteStore
        return SQLiteStore

    # Telemetry (requires opentelemetry packages)
    elif name == "AgentChordTracer":
        from agentchord.telemetry import AgentChordTracer
        return AgentChordTracer
    elif name == "setup_telemetry":
        from agentchord.telemetry import setup_telemetry
        return setup_telemetry
    elif name == "TraceCollector":
        from agentchord.telemetry.collector import TraceCollector
        return TraceCollector
    elif name == "ExecutionTrace":
        from agentchord.telemetry.collector import ExecutionTrace
        return ExecutionTrace

    # Orchestration
    elif name == "AgentTeam":
        from agentchord.orchestration.team import AgentTeam
        return AgentTeam

    # RAG
    elif name == "RAGPipeline":
        from agentchord.rag.pipeline import RAGPipeline
        return RAGPipeline
    elif name == "create_rag_tools":
        from agentchord.rag.tools import create_rag_tools
        return create_rag_tools
    elif name == "Document":
        from agentchord.rag.types import Document
        return Document
    elif name == "Chunk":
        from agentchord.rag.types import Chunk
        return Chunk
    elif name == "RAGResponse":
        from agentchord.rag.types import RAGResponse
        return RAGResponse
    elif name == "RAGEvaluator":
        from agentchord.rag.evaluation import RAGEvaluator
        return RAGEvaluator
    elif name == "EmbeddingProvider":
        from agentchord.rag.embeddings.base import EmbeddingProvider
        return EmbeddingProvider
    elif name == "HybridSearch":
        from agentchord.rag.search.hybrid import HybridSearch
        return HybridSearch
    elif name == "BM25Search":
        from agentchord.rag.search.bm25 import BM25Search
        return BM25Search

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
