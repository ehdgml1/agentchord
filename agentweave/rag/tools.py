"""Agentic RAG tools for Agent tool-calling integration.

Provides RAG pipeline operations as AgentWeave Tools, enabling
agents to autonomously decide when and how to search knowledge bases.

This is the key differentiator from static RAG:
    Static RAG: Every query goes through retrieval
    Agentic RAG: Agent decides IF and WHEN to search

Example:
    pipeline = RAGPipeline(llm=provider, embedding_provider=embedder)
    await pipeline.ingest([TextLoader("docs/")])

    agent = Agent(
        name="assistant",
        role="Knowledge-augmented assistant",
        tools=create_rag_tools(pipeline),
    )
    result = await agent.run("What is AgentWeave's architecture?")
    # Agent autonomously calls rag_search when needed
"""

from __future__ import annotations

from typing import Any

from agentweave.rag.pipeline import RAGPipeline
from agentweave.tools.base import Tool, ToolParameter


def create_rag_tools(
    pipeline: RAGPipeline,
    *,
    search_limit: int = 5,
) -> list[Tool]:
    """Create RAG tools from a pipeline for agent use.

    Returns tools that agents can call to search the knowledge base.
    The agent's LLM decides when to use these tools based on the query.

    Args:
        pipeline: Configured RAGPipeline with ingested documents.
        search_limit: Default number of results per search.

    Returns:
        List of Tool instances for agent registration.
    """

    async def rag_search(query: str, limit: int = search_limit) -> str:
        """Search the knowledge base for relevant information.

        Args:
            query: Natural language search query.
            limit: Maximum number of results.

        Returns:
            Formatted context string with source information.
        """
        retrieval = await pipeline.retrieve(query, limit=limit)

        if not retrieval.results:
            return "No relevant information found in the knowledge base."

        parts: list[str] = []
        for i, result in enumerate(retrieval.results, 1):
            source = result.chunk.metadata.get("source", result.chunk.document_id or "unknown")
            parts.append(
                f"[{i}] (score: {result.score:.3f}, source: {source})\n{result.chunk.content}"
            )

        return "\n\n---\n\n".join(parts)

    async def rag_query(question: str) -> str:
        """Search the knowledge base AND generate an answer.

        Use this when you want a direct answer synthesized from
        the knowledge base rather than raw search results.

        Args:
            question: Question to answer from the knowledge base.

        Returns:
            Generated answer with source references.
        """
        response = await pipeline.query(question, limit=search_limit)

        source_info = ""
        if response.source_documents:
            source_info = f"\n\nSources: {', '.join(response.source_documents)}"

        return f"{response.answer}{source_info}"

    search_tool = Tool(
        name="rag_search",
        description=(
            "Search the knowledge base for information relevant to a query. "
            "Returns raw context passages with relevance scores. "
            "Use this when you need to find specific information."
        ),
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description="Natural language search query",
                required=True,
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="Maximum number of results (default: 5)",
                required=False,
                default=search_limit,
            ),
        ],
        func=rag_search,
    )

    query_tool = Tool(
        name="rag_query",
        description=(
            "Ask a question and get an answer synthesized from the knowledge base. "
            "Use this when you need a direct answer rather than raw search results."
        ),
        parameters=[
            ToolParameter(
                name="question",
                type="string",
                description="Question to answer from the knowledge base",
                required=True,
            ),
        ],
        func=rag_query,
    )

    return [search_tool, query_tool]
