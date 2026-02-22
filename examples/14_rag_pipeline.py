"""Example 14: RAG Pipeline with Document Ingestion and Retrieval.

This example demonstrates how to build a Retrieval-Augmented Generation (RAG)
pipeline that ingests documents, retrieves relevant context, and generates
answers grounded in that context.
"""

from __future__ import annotations

import asyncio
import hashlib
from typing import AsyncIterator

from agentchord import RAGPipeline, Document
from agentchord.core.types import LLMResponse, Message, Usage
from agentchord.llm.base import BaseLLMProvider
from agentchord.rag.embeddings.base import EmbeddingProvider
from agentchord.rag.chunking.recursive import RecursiveCharacterChunker


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock embedding provider that returns deterministic hash-based vectors."""

    def __init__(self):
        self._model_name = "mock-embedding"
        self._dimensions = 64

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, text: str) -> list[float]:
        """Generate deterministic embedding from text hash."""
        # Use hash to create deterministic vector
        text_hash = hashlib.sha256(text.encode()).digest()
        # Convert bytes to normalized floats
        vector = []
        for i in range(self._dimensions):
            byte_val = text_hash[i % len(text_hash)]
            normalized = (byte_val / 255.0) * 2.0 - 1.0  # Scale to [-1, 1]
            vector.append(normalized)
        return vector

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts."""
        return [await self.embed(text) for text in texts]


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider that generates answers based on context."""

    @property
    def model(self) -> str:
        return "mock-rag-llm"

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return 0.0

    @property
    def cost_per_1k_output_tokens(self) -> float:
        return 0.0

    async def complete(self, messages, temperature=0.7, max_tokens=4096, **kwargs):
        """Generate answer mentioning the context."""
        # Extract context from system message
        context_snippets = []
        for msg in messages:
            if msg.role == "system" and "context" in msg.content.lower():
                # Extract context chunks (simplified)
                if "Paris" in msg.content:
                    context_snippets.append("Paris information")
                if "London" in msg.content:
                    context_snippets.append("London information")

        if context_snippets:
            answer = f"Based on the provided context ({', '.join(context_snippets)}), I can answer your question. The documents mention relevant details about your query."
        else:
            answer = "I don't have sufficient context to answer this question."

        return LLMResponse(
            content=answer,
            model=self.model,
            usage=Usage(prompt_tokens=100, completion_tokens=50),
            finish_reason="stop",
        )

    async def stream(self, messages, temperature=0.7, max_tokens=4096, **kwargs) -> AsyncIterator[str]:
        raise NotImplementedError("Stream not used in this example")
        yield  # Make this a generator


async def example_basic_rag() -> None:
    """Example: Basic RAG pipeline with ingest and query."""
    print("=== Example 1: Basic RAG Pipeline ===\n")

    # Create RAG pipeline with mock providers
    async with RAGPipeline(
        llm=MockLLMProvider(),
        embedding_provider=MockEmbeddingProvider(),
        chunker=RecursiveCharacterChunker(chunk_size=200, chunk_overlap=50),
    ) as pipeline:
        # Create sample documents
        documents = [
            Document(
                content="Paris is the capital of France. It is known for the Eiffel Tower and the Louvre Museum.",
                metadata={"source": "geography.txt", "topic": "cities"},
            ),
            Document(
                content="London is the capital of the United Kingdom. Famous landmarks include Big Ben and Buckingham Palace.",
                metadata={"source": "geography.txt", "topic": "cities"},
            ),
            Document(
                content="Tokyo is the capital of Japan. It is known for its modern architecture and traditional temples.",
                metadata={"source": "geography.txt", "topic": "cities"},
            ),
        ]

        # Ingest documents
        print("Ingesting documents...")
        await pipeline.ingest_documents(documents)
        print(f"Ingested {len(documents)} documents\n")

        # Query the pipeline
        query = "What is the capital of France?"
        print(f"Query: {query}\n")

        response = await pipeline.query(query, limit=2)

        print(f"Answer: {response.answer}\n")
        print(f"Retrieved {len(response.retrieval.results)} sources:")
        for i, result in enumerate(response.retrieval.results, 1):
            print(f"  {i}. {result.chunk.content[:80]}...")
            print(f"     Score: {result.score:.4f}")
            print(f"     Source: {result.chunk.metadata.get('source', 'unknown')}\n")

        print(f"Retrieval time: {response.retrieval.total_ms:.2f}ms")
        print(f"Generation time: {response.usage.get('generation_ms', 0.0):.2f}ms\n")


async def example_retrieve_and_generate() -> None:
    """Example: Separate retrieve and generate steps."""
    print("=== Example 2: Separate Retrieve and Generate ===\n")

    async with RAGPipeline(
        llm=MockLLMProvider(),
        embedding_provider=MockEmbeddingProvider(),
    ) as pipeline:
        # Ingest documents
        documents = [
            Document(content="Python is a high-level programming language."),
            Document(content="JavaScript is primarily used for web development."),
            Document(content="Rust is a systems programming language focused on safety."),
        ]
        await pipeline.ingest_documents(documents)

        query = "What is Python used for?"

        # Step 1: Retrieve relevant documents
        print(f"Query: {query}\n")
        print("Step 1: Retrieving relevant documents...")
        retrieval_result = await pipeline.retrieve(query, limit=2)

        print(f"Retrieved {len(retrieval_result.results)} chunks:")
        for result in retrieval_result.results:
            print(f"  - {result.chunk.content[:60]}... (score: {result.score:.4f})")
        print()

        # Step 2: Generate answer from retrieved context
        print("Step 2: Generating answer from context...")
        rag_response = await pipeline.generate(query, retrieval_result)

        print(f"Answer: {rag_response.answer}\n")


async def main() -> None:
    """Run all RAG pipeline examples."""
    await example_basic_rag()
    await example_retrieve_and_generate()

    print("=== Key Features of RAG Pipeline ===")
    print("1. Document Ingestion: Chunk and embed documents into vector store")
    print("2. Semantic Search: Retrieve relevant context using embeddings")
    print("3. Grounded Generation: Generate answers based on retrieved context")
    print("4. Source Attribution: Track which documents contributed to the answer")
    print("5. Async Context Manager: Automatic cleanup of resources")


if __name__ == "__main__":
    asyncio.run(main())
