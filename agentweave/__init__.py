"""AgentWeave - Protocol-First Multi-Agent Framework.

AgentWeave provides a simple yet powerful framework for building
multi-agent AI systems with native support for MCP and A2A protocols.

Example:
    >>> from agentweave import Agent
    >>> agent = Agent(name="assistant", role="AI Helper")
    >>> result = agent.run_sync("Hello!")
    >>> print(result.output)

For more examples, see https://github.com/agentweave/agentweave
"""

__version__ = "0.2.0"

# Core exports
from agentweave.core.agent import Agent
from agentweave.core.config import AgentConfig, CostConfig, RetryConfig
from agentweave.core.types import (
    AgentResult,
    LLMResponse,
    Message,
    MessageRole,
    ToolCall,
    Usage,
)
from agentweave.core.state import WorkflowState, WorkflowResult, WorkflowStatus
from agentweave.core.workflow import Workflow
from agentweave.core.executor import MergeStrategy

# Error exports
from agentweave.errors.exceptions import (
    AgentError,
    AgentExecutionError,
    AgentTimeoutError,
    AgentWeaveError,
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
from agentweave.llm.base import BaseLLMProvider

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
    "AgentWeaveError",
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
    elif name == "ProviderRegistry":
        from agentweave.llm.registry import ProviderRegistry
        return ProviderRegistry
    elif name == "get_registry":
        from agentweave.llm.registry import get_registry
        return get_registry

    # MCP (requires mcp package)
    elif name == "MCPClient":
        from agentweave.protocols.mcp import MCPClient
        return MCPClient
    elif name == "MCPTool":
        from agentweave.protocols.mcp import MCPTool
        return MCPTool

    # A2A
    elif name == "A2AClient":
        from agentweave.protocols.a2a import A2AClient
        return A2AClient
    elif name == "A2AServer":
        from agentweave.protocols.a2a import A2AServer
        return A2AServer
    elif name == "AgentCard":
        from agentweave.protocols.a2a import AgentCard
        return AgentCard

    # Memory
    elif name == "ConversationMemory":
        from agentweave.memory import ConversationMemory
        return ConversationMemory
    elif name == "SemanticMemory":
        from agentweave.memory import SemanticMemory
        return SemanticMemory
    elif name == "WorkingMemory":
        from agentweave.memory import WorkingMemory
        return WorkingMemory
    elif name == "MemoryEntry":
        from agentweave.memory import MemoryEntry
        return MemoryEntry

    # Tracking
    elif name == "CostTracker":
        from agentweave.tracking import CostTracker
        return CostTracker
    elif name == "TokenUsage":
        from agentweave.tracking import TokenUsage
        return TokenUsage
    elif name == "CallbackManager":
        from agentweave.tracking import CallbackManager
        return CallbackManager

    # Resilience
    elif name == "RetryPolicy":
        from agentweave.resilience import RetryPolicy
        return RetryPolicy
    elif name == "CircuitBreaker":
        from agentweave.resilience import CircuitBreaker
        return CircuitBreaker
    elif name == "TimeoutManager":
        from agentweave.resilience import TimeoutManager
        return TimeoutManager
    elif name == "ResilienceConfig":
        from agentweave.resilience import ResilienceConfig
        return ResilienceConfig

    # Tools
    elif name == "Tool":
        from agentweave.tools import Tool
        return Tool
    elif name == "ToolExecutor":
        from agentweave.tools import ToolExecutor
        return ToolExecutor
    elif name == "tool":
        from agentweave.tools import tool
        return tool

    # Logging
    elif name == "get_logger":
        from agentweave.logging import get_logger
        return get_logger
    elif name == "configure_logging":
        from agentweave.logging import configure_logging
        return configure_logging
    elif name == "LogLevel":
        from agentweave.logging import LogLevel
        return LogLevel

    # Streaming
    elif name == "StreamChunk":
        from agentweave.core.types import StreamChunk
        return StreamChunk

    # Structured Output
    elif name == "OutputSchema":
        from agentweave.core.structured import OutputSchema
        return OutputSchema

    # Memory Stores (persistent backends)
    elif name == "MemoryStore":
        from agentweave.memory.stores import MemoryStore
        return MemoryStore
    elif name == "JSONFileStore":
        from agentweave.memory.stores import JSONFileStore
        return JSONFileStore
    elif name == "SQLiteStore":
        from agentweave.memory.stores import SQLiteStore
        return SQLiteStore

    # Telemetry (requires opentelemetry packages)
    elif name == "AgentWeaveTracer":
        from agentweave.telemetry import AgentWeaveTracer
        return AgentWeaveTracer
    elif name == "setup_telemetry":
        from agentweave.telemetry import setup_telemetry
        return setup_telemetry
    elif name == "TraceCollector":
        from agentweave.telemetry.collector import TraceCollector
        return TraceCollector
    elif name == "ExecutionTrace":
        from agentweave.telemetry.collector import ExecutionTrace
        return ExecutionTrace

    # Orchestration
    elif name == "AgentTeam":
        from agentweave.orchestration.team import AgentTeam
        return AgentTeam

    # RAG
    elif name == "RAGPipeline":
        from agentweave.rag.pipeline import RAGPipeline
        return RAGPipeline
    elif name == "create_rag_tools":
        from agentweave.rag.tools import create_rag_tools
        return create_rag_tools
    elif name == "Document":
        from agentweave.rag.types import Document
        return Document
    elif name == "Chunk":
        from agentweave.rag.types import Chunk
        return Chunk
    elif name == "RAGResponse":
        from agentweave.rag.types import RAGResponse
        return RAGResponse
    elif name == "RAGEvaluator":
        from agentweave.rag.evaluation import RAGEvaluator
        return RAGEvaluator
    elif name == "EmbeddingProvider":
        from agentweave.rag.embeddings.base import EmbeddingProvider
        return EmbeddingProvider
    elif name == "HybridSearch":
        from agentweave.rag.search.hybrid import HybridSearch
        return HybridSearch
    elif name == "BM25Search":
        from agentweave.rag.search.bm25 import BM25Search
        return BM25Search

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
