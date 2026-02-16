# Changelog

All notable changes to AgentWeave will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- **Multi-Agent Orchestration** (`agentweave.orchestration`)
  - `AgentTeam` class with 4 built-in strategies: Coordinator, Round Robin, Debate, Map Reduce
  - Delegation-as-tools pattern for natural language-driven task routing via coordinator
  - `MessageBus` for structured agent-to-agent communication (async pub/sub with message history)
  - `SharedContext` for thread-safe shared state with modification tracking
  - `TeamResult` with automatic cost/token aggregation across all agents
  - Streaming support via `TeamEvent` for real-time team execution updates
  - Examples: `15_multi_agent_team.py`, `16_debate_strategy.py`
  - Documentation: `docs/guides/orchestration.md` (comprehensive guide), `docs/api/orchestration.md` (API reference)

## [0.1.0] - 2025-05-15

### Added

- **Core Agent System**: `Agent` class with async `run()`, `stream()`, and `run_sync()` methods
- **Multi-Provider LLM Support**: OpenAI, Anthropic, Ollama, and Gemini providers with unified interface
- **Provider Registry**: Auto-detection of providers by model name prefix (gpt-, claude-, ollama/, gemini-)
- **Tool Calling**: Full tool execution loop with `@tool` decorator, `Tool` class, and `ToolExecutor`
- **MCP Integration**: `MCPClient` for Model Context Protocol with `MCPTool` adapter bridging MCP tools to Agent tools
- **A2A Protocol**: `A2AClient` and `A2AServer` for Agent-to-Agent communication with `AgentCard` discovery
- **Workflow Engine**: `Workflow` class with flow DSL (`"A -> B"`, `"[A, B]"`, `"A -> [B, C] -> D"`) for sequential, parallel, and mixed execution
- **Memory System**: `ConversationMemory`, `SemanticMemory`, `WorkingMemory` with `MemoryEntry` tracking
- **Persistent Memory Stores**: `MemoryStore` ABC with `JSONFileStore` (file-based) and `SQLiteStore` (async SQLite via aiosqlite)
- **Structured Output**: `OutputSchema[T]` wrapping Pydantic models with OpenAI `response_format` support and system prompt injection for other providers
- **Streaming**: `Agent.stream()` with hybrid tool-calling support (complete() for tool rounds, stream for final response)
- **Cost Tracking**: `CostTracker` with per-model pricing, budget limits, and `TokenUsage` aggregation
- **Resilience**: `RetryPolicy`, `CircuitBreaker`, `TimeoutManager` with configurable `ResilienceConfig`
- **OpenTelemetry**: `AgentWeaveTracer` with context manager spans for agent/workflow/LLM/tool operations, `AgentWeaveMetrics` counters and histograms, graceful no-op fallback
- **Trace Collector**: `TraceCollector` with `TraceSpan`/`ExecutionTrace` dataclasses, callback-driven span hierarchy, JSON/JSONL export
- **Lifecycle Management**: Agent and Workflow async context managers (`async with`) for automatic memory flush, MCP disconnect, and cleanup
- **Structured Logging**: `get_logger()`, `configure_logging()`, `LogLevel` with JSON and text output modes
- **Callback System**: `CallbackManager` with event-driven hooks for agent, LLM, tool, and workflow events
- **Configuration**: `AgentConfig`, `CostConfig`, `RetryConfig` with Pydantic validation
- **Benchmarks**: 23 performance benchmarks covering agent latency, memory operations, workflow execution, and structured output
- **Documentation**: Full MkDocs site with getting-started guide, core concepts, 5 advanced guides, 7 API reference docs, and examples index
- **CI/CD**: GitHub Actions with lint, typecheck, and test matrix (Python 3.10-3.12)
- **Examples**: 13+ example scripts demonstrating all major features
- **Retrieval-Augmented Generation (RAG)**: Complete RAG system with pipeline orchestration
  - Document loaders: Text, PDF, Web, Directory
  - Chunking strategies: Recursive character, Semantic (embedding-based), Parent-child
  - Embedding providers: OpenAI, Ollama, SentenceTransformer
  - Vector stores: In-memory, ChromaDB, FAISS
  - Search: BM25 (Okapi), Hybrid search with Reciprocal Rank Fusion (RRF)
  - Reranking: Cross-encoder (sentence-transformers), LLM-based
  - `RAGPipeline` for end-to-end ingest → retrieve → generate
  - `create_rag_tools()` for Agentic RAG via tool calling
  - RAGAS-style evaluation (Faithfulness, Answer Relevancy, Context Relevancy)
- **701 unit/integration tests** with 82%+ code coverage

### Security

- Path traversal prevention in `JSONFileStore` namespace validation
- Atomic `save_many` operations in `SQLiteStore` to prevent data loss
- Idempotent `Agent.close()` to prevent double-cleanup issues
- Embedding dimension validation in InMemoryVectorStore and FAISSVectorStore
- OpenAI embedding batch size limit (2048) enforcement
- Format string injection prevention in RAG prompt templates

[0.1.0]: https://github.com/agentweave/agentweave/releases/tag/v0.1.0
