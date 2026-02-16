"""BM25 sparse search implementation.

Pure Python implementation of Okapi BM25 algorithm for keyword-based
document ranking. Complements dense vector search for hybrid retrieval.

BM25 Scoring Formula:
    score(D, Q) = Σ IDF(qi) * (f(qi, D) * (k1 + 1)) / (f(qi, D) + k1 * (1 - b + b * |D| / avgdl))

Where:
    IDF(qi) = ln((N - n(qi) + 0.5) / (n(qi) + 0.5) + 1)
    f(qi, D) = term frequency of qi in document D
    |D| = document length in tokens
    avgdl = average document length across corpus
    k1 = term frequency saturation parameter (default: 1.5)
    b = document length normalization parameter (default: 0.75)
"""
from __future__ import annotations

import math
import re
from collections import Counter

from agentweave.rag.types import Chunk, SearchResult

_DEFAULT_STOP_WORDS: frozenset[str] = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "and", "but", "or", "nor", "not", "so", "yet",
    "it", "its", "this", "that", "these", "those", "i", "me", "my",
    "we", "our", "you", "your", "he", "she", "him", "her", "they", "them",
})


class BM25Search:
    """Okapi BM25 sparse keyword search.

    Provides term-frequency based document ranking that complements
    dense vector search for exact keyword matching.

    Example:
        bm25 = BM25Search()
        bm25.index(chunks)
        results = bm25.search("error handling", limit=10)
    """

    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        stop_words: frozenset[str] | None = None,
    ) -> None:
        """Initialize BM25 search.

        Args:
            k1: Term frequency saturation. Higher values increase
                the effect of term frequency. Default 1.5.
            b: Document length normalization. 0 = no normalization,
                1 = full normalization. Default 0.75.
            stop_words: Words to exclude from indexing and search.
        """
        self._k1 = k1
        self._b = b
        self._stop_words = stop_words if stop_words is not None else _DEFAULT_STOP_WORDS

        self._chunks: dict[str, Chunk] = {}
        self._doc_freqs: dict[str, int] = {}
        self._doc_lens: dict[str, int] = {}
        self._term_freqs: dict[str, Counter[str]] = {}
        self._avg_dl: float = 0.0
        self._n_docs: int = 0

    def index(self, chunks: list[Chunk]) -> None:
        """Build BM25 index from chunks.

        Replaces any existing index.

        Args:
            chunks: Chunks to index.
        """
        self._chunks.clear()
        self._term_freqs.clear()
        self._doc_lens.clear()
        self._doc_freqs.clear()

        for chunk in chunks:
            tokens = self._tokenize(chunk.content)
            self._chunks[chunk.id] = chunk
            self._term_freqs[chunk.id] = Counter(tokens)
            self._doc_lens[chunk.id] = len(tokens)

        self._n_docs = len(self._chunks)
        total_len = sum(self._doc_lens.values())
        self._avg_dl = total_len / self._n_docs if self._n_docs > 0 else 0.0

        for tf in self._term_freqs.values():
            for term in tf:
                self._doc_freqs[term] = self._doc_freqs.get(term, 0) + 1

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search indexed chunks using BM25 scoring.

        Args:
            query: Search query text.
            limit: Maximum number of results.

        Returns:
            SearchResults sorted by BM25 score descending,
            with scores normalized to 0-1 range.
        """
        if not self._chunks:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores: list[tuple[str, float]] = []
        for chunk_id in self._chunks:
            score = self._score_document(chunk_id, query_tokens)
            if score > 0:
                scores.append((chunk_id, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        top = scores[:limit]

        if not top:
            return []

        max_score = top[0][1]
        return [
            SearchResult(
                chunk=self._chunks[chunk_id],
                score=score / max_score,
                source="bm25",
            )
            for chunk_id, score in top
        ]

    def add_chunks(self, chunks: list[Chunk]) -> None:
        """Add chunks to existing index by rebuilding.

        Warning: This rebuilds the entire index (O(N) where N = total chunks).
        For bulk ingestion, prefer calling index() once with all chunks
        rather than calling add_chunks() incrementally.

        Args:
            chunks: New chunks to add.
        """
        all_chunks = list(self._chunks.values()) + chunks
        self.index(all_chunks)

    def remove_chunks(self, chunk_ids: list[str]) -> int:
        """Remove chunks and rebuild index.

        Warning: This rebuilds the entire index after removal.
        For removing many chunks, prefer collecting all IDs first
        and calling remove_chunks() once.

        Args:
            chunk_ids: IDs to remove.

        Returns:
            Number of chunks removed.
        """
        ids_to_remove = set(chunk_ids)
        remaining = [c for c in self._chunks.values() if c.id not in ids_to_remove]
        removed = len(self._chunks) - len(remaining)
        self.index(remaining)
        return removed

    @property
    def indexed_count(self) -> int:
        """Number of indexed chunks."""
        return self._n_docs

    def _score_document(self, chunk_id: str, query_tokens: list[str]) -> float:
        """Compute BM25 score for a single document."""
        score = 0.0
        doc_len = self._doc_lens[chunk_id]
        tf_map = self._term_freqs[chunk_id]

        for term in query_tokens:
            n = self._doc_freqs.get(term, 0)
            if n == 0:
                continue

            idf = math.log((self._n_docs - n + 0.5) / (n + 0.5) + 1.0)
            tf = tf_map.get(term, 0)
            numerator = tf * (self._k1 + 1.0)
            denominator = tf + self._k1 * (
                1.0 - self._b + self._b * doc_len / self._avg_dl
            )
            score += idf * numerator / denominator

        return score

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into lowercase words, removing stop words."""
        tokens = re.findall(r"\b\w+\b", text.lower())
        return [t for t in tokens if t not in self._stop_words and len(t) > 1]
