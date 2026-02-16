"""Reranking for improved retrieval precision.

Two-stage retrieval pattern:
    Stage 1 (Fast): Vector/BM25 search retrieves 25-50 candidates
    Stage 2 (Accurate): Cross-encoder reranks to top-3

Cross-encoders see query and document together, providing
20-35% accuracy improvement over bi-encoder retrieval alone.
"""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any

from agentweave.rag.types import SearchResult


class Reranker(ABC):
    """Abstract base for reranking models."""

    @abstractmethod
    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_n: int = 3,
    ) -> list[SearchResult]:
        """Rerank search results by relevance to query.

        Args:
            query: Original search query.
            results: Candidate results from initial search.
            top_n: Number of top results to return.

        Returns:
            Reranked results with updated scores, sorted descending.
        """


class CrossEncoderReranker(Reranker):
    """Cross-encoder reranker using sentence-transformers.

    Requires: pip install sentence-transformers

    Default model: cross-encoder/ms-marco-MiniLM-L-6-v2 (22MB)
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        device: str = "cpu",
    ) -> None:
        """Initialize cross-encoder reranker.

        Args:
            model_name: HuggingFace model name for cross-encoder.
            device: Device to run model on ('cpu' or 'cuda').
        """
        self._model_name = model_name
        self._device = device
        self._model: Any = None

    def _get_model(self) -> Any:
        """Lazy-load the cross-encoder model."""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as e:
                raise ImportError(
                    "sentence-transformers is required for CrossEncoderReranker. "
                    "Install with: pip install sentence-transformers"
                ) from e
            self._model = CrossEncoder(self._model_name, device=self._device)
        return self._model

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_n: int = 3,
    ) -> list[SearchResult]:
        """Rerank using cross-encoder scoring.

        Args:
            query: Search query.
            results: Candidate results.
            top_n: Number of results to return.

        Returns:
            Top-n results reranked by cross-encoder score.
        """
        if not results:
            return []

        model = self._get_model()
        pairs = [(query, r.chunk.content) for r in results]

        scores: list[float] = await asyncio.to_thread(model.predict, pairs)

        scored = sorted(
            zip(results, scores), key=lambda x: x[1], reverse=True
        )

        return [
            SearchResult(
                chunk=r.chunk,
                score=float(s),
                source="reranked",
            )
            for r, s in scored[:top_n]
        ]


class LLMReranker(Reranker):
    """LLM-based reranker using the agent's own LLM provider.

    More expensive but requires no additional model installation.
    Uses the LLM to judge relevance of each candidate.
    """

    def __init__(self, llm_provider: Any) -> None:
        """Initialize LLM reranker.

        Args:
            llm_provider: A BaseLLMProvider instance for scoring.
        """
        self._llm = llm_provider

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_n: int = 3,
    ) -> list[SearchResult]:
        """Rerank using LLM relevance scoring.

        Each candidate is scored by the LLM on a 0-10 scale.

        Args:
            query: Search query.
            results: Candidate results.
            top_n: Number of results to return.

        Returns:
            Top-n results reranked by LLM relevance score.
        """
        if not results:
            return []

        import re as _re

        from agentweave.core.types import Message, MessageRole

        async def _score_one(result: SearchResult) -> tuple[SearchResult, float]:
            prompt = (
                f"Rate the relevance of this document to the query on a scale of 0 to 10.\n\n"
                f"Query: {query}\n"
                f"Document: {result.chunk.content[:500]}\n\n"
                f"Respond with ONLY a number (0-10)."
            )
            response = await self._llm.complete(
                [Message(role=MessageRole.USER, content=prompt)],
                temperature=0.0,
                max_tokens=10,
            )
            match = _re.search(r"\b(\d+(?:\.\d+)?)\b", response.content)
            score = min(float(match.group(1)), 10.0) if match else 5.0
            return (result, score)

        scored = await asyncio.gather(*[_score_one(r) for r in results])
        scored_list = sorted(scored, key=lambda x: x[1], reverse=True)

        return [
            SearchResult(chunk=r.chunk, score=s / 10.0, source="reranked")
            for r, s in scored_list[:top_n]
        ]
