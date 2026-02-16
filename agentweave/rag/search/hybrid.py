"""Hybrid search combining dense and sparse retrieval.

Uses Reciprocal Rank Fusion (RRF) to merge results from vector
similarity search and BM25 keyword search.

RRF Score Formula:
    rrf_score(d) = Σ 1 / (k + rank_i(d))

Where:
    k = smoothing constant (default: 60)
    rank_i(d) = rank of document d in result list i (1-indexed)

RRF is robust, parameter-free fusion that doesn't require
score normalization between different retrieval methods.

Reference:
    Cormack, Clarke & Buettcher (2009). "Reciprocal Rank Fusion outperforms
    Condorcet and Individual Rank Learning Methods"
"""
from __future__ import annotations

import time
from typing import Any

from agentweave.rag.embeddings.base import EmbeddingProvider
from agentweave.rag.search.bm25 import BM25Search
from agentweave.rag.search.reranker import Reranker
from agentweave.rag.types import Chunk, RetrievalResult, SearchResult
from agentweave.rag.vectorstore.base import VectorStore


class HybridSearch:
    """Hybrid search combining dense vector and sparse BM25 retrieval.

    Uses Reciprocal Rank Fusion (RRF) to merge results from both
    retrieval methods into a single ranked list.

    Optionally supports a second-stage reranker for improved precision.

    Example:
        hybrid = HybridSearch(
            vectorstore=InMemoryVectorStore(),
            embedding_provider=OpenAIEmbeddings(),
            bm25=BM25Search(),
        )
        await hybrid.add(chunks)
        result = await hybrid.search("query", limit=5)
    """

    def __init__(
        self,
        vectorstore: VectorStore,
        embedding_provider: EmbeddingProvider,
        bm25: BM25Search | None = None,
        reranker: Reranker | None = None,
        *,
        rrf_k: int = 60,
        vector_weight: float = 1.0,
        bm25_weight: float = 1.0,
        vector_candidates: int = 25,
        bm25_candidates: int = 25,
    ) -> None:
        """Initialize hybrid search.

        Args:
            vectorstore: Vector store backend for dense retrieval.
            embedding_provider: Embedding provider for query vectorization.
            bm25: Optional BM25 index for sparse retrieval.
                  If None, creates an empty BM25Search instance.
            reranker: Optional reranker for second-stage reranking.
            rrf_k: RRF smoothing constant. Higher = more uniform weighting.
            vector_weight: Weight multiplier for vector search RRF scores.
            bm25_weight: Weight multiplier for BM25 RRF scores.
            vector_candidates: Number of candidates to retrieve from vector search.
            bm25_candidates: Number of candidates to retrieve from BM25.
        """
        self.vectorstore = vectorstore
        self.embedding_provider = embedding_provider
        self.bm25 = bm25 if bm25 is not None else BM25Search()
        self.reranker = reranker
        self.rrf_k = rrf_k
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        self.vector_candidates = vector_candidates
        self.bm25_candidates = bm25_candidates

    async def add(self, chunks: list[Chunk]) -> list[str]:
        """Add chunks to both vector store and BM25 index.

        Chunks must have embeddings set. If not, they will be
        embedded using the embedding provider.

        Returns:
            List of stored chunk IDs.
        """
        if not chunks:
            return []

        # Check which chunks need embeddings
        chunks_needing_embeddings = [c for c in chunks if c.embedding is None]

        if chunks_needing_embeddings:
            # Extract texts and embed them
            texts = [c.content for c in chunks_needing_embeddings]
            embeddings = await self.embedding_provider.embed_batch(texts)

            # Assign embeddings to chunks
            for chunk, embedding in zip(chunks_needing_embeddings, embeddings):
                chunk.embedding = embedding

        # Add to vector store
        chunk_ids = await self.vectorstore.add(chunks)

        # Index in BM25
        self.bm25.add_chunks(chunks)

        return chunk_ids

    async def search(
        self,
        query: str,
        limit: int = 5,
        *,
        filter: dict[str, Any] | None = None,
        use_reranker: bool = True,
    ) -> RetrievalResult:
        """Search using hybrid retrieval.

        Pipeline:
            1. Embed query
            2. Vector search (N candidates)
            3. BM25 search (M candidates)
            4. RRF fusion
            5. Optional reranking
            6. Return top-K

        Args:
            query: Search query text.
            limit: Number of final results.
            filter: Optional metadata filter for vector search.
            use_reranker: Whether to apply reranker (if available).

        Returns:
            RetrievalResult with timing metrics.
        """
        start_time = time.perf_counter()

        if not query.strip():
            return RetrievalResult(query=query)

        # Step 1: Embed query
        query_embedding = await self.embedding_provider.embed(query)

        # Step 2: Vector search
        vector_results = await self.vectorstore.search(
            query_embedding=query_embedding,
            limit=self.vector_candidates,
            filter=filter,
        )

        # Step 3: BM25 search
        bm25_results = self.bm25.search(
            query=query,
            limit=self.bm25_candidates,
        )

        # Step 4: RRF fusion
        fused_results = self._rrf_fuse(
            result_lists=[vector_results, bm25_results],
            weights=[self.vector_weight, self.bm25_weight],
            k=self.rrf_k,
        )

        # Step 5: Optional reranking
        if use_reranker and self.reranker is not None and fused_results:
            # Apply reranker to all candidates, then take top-K
            fused_results = await self.reranker.rerank(
                query=query,
                results=fused_results,
                top_n=limit,
            )

        # Step 6: Return top-K
        final_results = fused_results[:limit]
        end_time = time.perf_counter()
        retrieval_time_ms = (end_time - start_time) * 1000

        return RetrievalResult(
            query=query,
            results=final_results,
            retrieval_ms=retrieval_time_ms,
            total_ms=retrieval_time_ms,
        )

    async def delete(self, chunk_ids: list[str]) -> int:
        """Delete chunks from both vector store and BM25 index.

        Args:
            chunk_ids: IDs of chunks to delete.

        Returns:
            Number of chunks deleted.
        """
        if not chunk_ids:
            return 0

        # Delete from vector store
        deleted_count = await self.vectorstore.delete(chunk_ids)

        # Remove from BM25
        self.bm25.remove_chunks(chunk_ids)

        return deleted_count

    async def clear(self) -> None:
        """Clear both vector store and BM25 index."""
        await self.vectorstore.clear()
        self.bm25.index([])

    @staticmethod
    def _rrf_fuse(
        result_lists: list[list[SearchResult]],
        weights: list[float],
        k: int = 60,
    ) -> list[SearchResult]:
        """Fuse multiple result lists using Reciprocal Rank Fusion.

        Args:
            result_lists: Lists of search results from different sources.
            weights: Weight multiplier for each result list.
            k: RRF smoothing constant.

        Returns:
            Fused results sorted by RRF score descending.
        """
        if not result_lists or not weights:
            return []

        if len(result_lists) != len(weights):
            raise ValueError("Number of result lists must match number of weights")

        # Map: chunk_id → (rrf_score, chunk_ref)
        rrf_scores: dict[str, tuple[float, Chunk]] = {}

        # Process each result list with its weight
        for results, weight in zip(result_lists, weights):
            for rank, result in enumerate(results, start=1):
                chunk_id = result.chunk.id
                rrf_contribution = weight * (1.0 / (k + rank))

                if chunk_id in rrf_scores:
                    # Accumulate score, keep first chunk reference
                    current_score, chunk_ref = rrf_scores[chunk_id]
                    rrf_scores[chunk_id] = (current_score + rrf_contribution, chunk_ref)
                else:
                    # First occurrence
                    rrf_scores[chunk_id] = (rrf_contribution, result.chunk)

        # Sort by RRF score descending
        sorted_items = sorted(
            rrf_scores.items(),
            key=lambda item: item[1][0],
            reverse=True,
        )

        # Build final result list with RRF scores
        fused_results = [
            SearchResult(chunk=chunk_ref, score=rrf_score, source="hybrid")
            for chunk_id, (rrf_score, chunk_ref) in sorted_items
        ]

        return fused_results
