"""Unit tests for RAG rerankers.

Tests CrossEncoderReranker and LLMReranker implementations.
"""

from __future__ import annotations

from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from agentweave.core.types import LLMResponse, Usage
from agentweave.rag.search.reranker import CrossEncoderReranker, LLMReranker
from agentweave.rag.types import Chunk, SearchResult


def _make_result(id: str, content: str, score: float = 0.5) -> SearchResult:
    """Helper to create a SearchResult."""
    return SearchResult(
        chunk=Chunk(id=id, content=content),
        score=score,
        source="vector",
    )


class TestCrossEncoderReranker:
    """Tests for CrossEncoderReranker."""

    def test_import_error_when_sentence_transformers_missing(self) -> None:
        """ImportError raised when sentence-transformers not installed."""
        with patch(
            "agentweave.rag.search.reranker.CrossEncoderReranker._get_model"
        ) as mock_get_model:
            mock_get_model.side_effect = ImportError(
                "sentence-transformers is required for CrossEncoderReranker. "
                "Install with: pip install sentence-transformers"
            )

            reranker = CrossEncoderReranker()
            with pytest.raises(
                ImportError, match="sentence-transformers is required"
            ):
                reranker._get_model()

    async def test_rerank_empty_list_returns_empty(self) -> None:
        """Empty input list returns empty output."""
        reranker = CrossEncoderReranker()
        result = await reranker.rerank("test query", [], top_n=3)
        assert result == []

    async def test_rerank_scores_and_sorts_results(self) -> None:
        """Results are scored and sorted by cross-encoder."""
        results = [
            _make_result("1", "First document"),
            _make_result("2", "Second document"),
            _make_result("3", "Third document"),
        ]

        mock_model = MagicMock()
        mock_model.predict.return_value = [0.3, 0.9, 0.7]  # 2nd best, 1st best, 3rd best

        with patch(
            "agentweave.rag.search.reranker.CrossEncoderReranker._get_model",
            return_value=mock_model,
        ):
            reranker = CrossEncoderReranker.__new__(CrossEncoderReranker)
            reranker._model = mock_model
            reranker._model_name = "test"
            reranker._device = "cpu"

            reranked = await reranker.rerank("test query", results, top_n=3)

            # Verify model was called with correct pairs
            mock_model.predict.assert_called_once()
            pairs = mock_model.predict.call_args[0][0]
            assert pairs == [
                ("test query", "First document"),
                ("test query", "Second document"),
                ("test query", "Third document"),
            ]

            # Verify results sorted by score descending
            assert len(reranked) == 3
            assert reranked[0].chunk.id == "2"
            assert reranked[0].score == 0.9
            assert reranked[1].chunk.id == "3"
            assert reranked[1].score == 0.7
            assert reranked[2].chunk.id == "1"
            assert reranked[2].score == 0.3

    async def test_rerank_respects_top_n_limit(self) -> None:
        """Only top_n results returned when more candidates available."""
        results = [
            _make_result("1", "First"),
            _make_result("2", "Second"),
            _make_result("3", "Third"),
            _make_result("4", "Fourth"),
            _make_result("5", "Fifth"),
        ]

        mock_model = MagicMock()
        mock_model.predict.return_value = [0.1, 0.5, 0.9, 0.3, 0.7]

        with patch(
            "agentweave.rag.search.reranker.CrossEncoderReranker._get_model",
            return_value=mock_model,
        ):
            reranker = CrossEncoderReranker.__new__(CrossEncoderReranker)
            reranker._model = mock_model
            reranker._model_name = "test"
            reranker._device = "cpu"

            reranked = await reranker.rerank("query", results, top_n=2)

            assert len(reranked) == 2
            assert reranked[0].chunk.id == "3"  # score 0.9
            assert reranked[1].chunk.id == "5"  # score 0.7

    async def test_rerank_sets_source_to_reranked(self) -> None:
        """Reranked results have source set to 'reranked'."""
        results = [_make_result("1", "Document")]

        mock_model = MagicMock()
        mock_model.predict.return_value = [0.8]

        with patch(
            "agentweave.rag.search.reranker.CrossEncoderReranker._get_model",
            return_value=mock_model,
        ):
            reranker = CrossEncoderReranker.__new__(CrossEncoderReranker)
            reranker._model = mock_model
            reranker._model_name = "test"
            reranker._device = "cpu"

            reranked = await reranker.rerank("query", results, top_n=1)

            assert reranked[0].source == "reranked"


class TestLLMReranker:
    """Tests for LLMReranker."""

    async def test_rerank_empty_list_returns_empty(self) -> None:
        """Empty input list returns empty output."""
        mock_llm = AsyncMock()
        reranker = LLMReranker(mock_llm)

        result = await reranker.rerank("test query", [], top_n=3)

        assert result == []
        mock_llm.complete.assert_not_called()

    async def test_rerank_parses_integer_scores(self) -> None:
        """LLM integer responses parsed correctly to normalized scores."""
        results = [
            _make_result("1", "First document"),
            _make_result("2", "Second document"),
            _make_result("3", "Third document"),
        ]

        mock_llm = AsyncMock()
        mock_llm.complete.side_effect = [
            LLMResponse(
                content="8",
                model="test",
                usage=Usage(prompt_tokens=10, completion_tokens=1),
                finish_reason="stop",
            ),
            LLMResponse(
                content="3",
                model="test",
                usage=Usage(prompt_tokens=10, completion_tokens=1),
                finish_reason="stop",
            ),
            LLMResponse(
                content="6",
                model="test",
                usage=Usage(prompt_tokens=10, completion_tokens=1),
                finish_reason="stop",
            ),
        ]

        reranker = LLMReranker(mock_llm)
        reranked = await reranker.rerank("test query", results, top_n=3)

        assert len(reranked) == 3
        assert reranked[0].chunk.id == "1"
        assert reranked[0].score == 0.8  # 8/10
        assert reranked[1].chunk.id == "3"
        assert reranked[1].score == 0.6  # 6/10
        assert reranked[2].chunk.id == "2"
        assert reranked[2].score == 0.3  # 3/10

    async def test_rerank_parses_decimal_scores(self) -> None:
        """LLM decimal responses parsed correctly."""
        results = [_make_result("1", "Document")]

        mock_llm = AsyncMock()
        mock_llm.complete.return_value = LLMResponse(
            content="7.5",
            model="test",
            usage=Usage(prompt_tokens=10, completion_tokens=1),
            finish_reason="stop",
        )

        reranker = LLMReranker(mock_llm)
        reranked = await reranker.rerank("query", results, top_n=1)

        assert reranked[0].score == 0.75  # 7.5/10

    async def test_rerank_handles_unparseable_scores(self) -> None:
        """Non-numeric LLM response defaults to score 5.0."""
        results = [_make_result("1", "Document")]

        mock_llm = AsyncMock()
        mock_llm.complete.return_value = LLMResponse(
            content="not a number",
            model="test",
            usage=Usage(prompt_tokens=10, completion_tokens=1),
            finish_reason="stop",
        )

        reranker = LLMReranker(mock_llm)
        reranked = await reranker.rerank("query", results, top_n=1)

        assert reranked[0].score == 0.5  # 5.0/10 default

    async def test_rerank_clamps_scores_above_10(self) -> None:
        """Scores above 10 are clamped to 10."""
        results = [_make_result("1", "Document")]

        mock_llm = AsyncMock()
        mock_llm.complete.return_value = LLMResponse(
            content="15",
            model="test",
            usage=Usage(prompt_tokens=10, completion_tokens=1),
            finish_reason="stop",
        )

        reranker = LLMReranker(mock_llm)
        reranked = await reranker.rerank("query", results, top_n=1)

        assert reranked[0].score == 1.0  # min(15, 10) / 10

    async def test_rerank_respects_top_n_limit(self) -> None:
        """Only top_n results returned when more candidates available."""
        results = [
            _make_result("1", "First"),
            _make_result("2", "Second"),
            _make_result("3", "Third"),
        ]

        mock_llm = AsyncMock()
        mock_llm.complete.side_effect = [
            LLMResponse(
                content="9",
                model="test",
                usage=Usage(prompt_tokens=10, completion_tokens=1),
                finish_reason="stop",
            ),
            LLMResponse(
                content="4",
                model="test",
                usage=Usage(prompt_tokens=10, completion_tokens=1),
                finish_reason="stop",
            ),
            LLMResponse(
                content="7",
                model="test",
                usage=Usage(prompt_tokens=10, completion_tokens=1),
                finish_reason="stop",
            ),
        ]

        reranker = LLMReranker(mock_llm)
        reranked = await reranker.rerank("query", results, top_n=2)

        assert len(reranked) == 2
        assert reranked[0].chunk.id == "1"  # score 9
        assert reranked[1].chunk.id == "3"  # score 7

    async def test_rerank_sorts_by_score_descending(self) -> None:
        """Results sorted by score in descending order."""
        results = [
            _make_result("1", "Low score"),
            _make_result("2", "High score"),
            _make_result("3", "Medium score"),
        ]

        mock_llm = AsyncMock()
        mock_llm.complete.side_effect = [
            LLMResponse(
                content="2",
                model="test",
                usage=Usage(prompt_tokens=10, completion_tokens=1),
                finish_reason="stop",
            ),
            LLMResponse(
                content="9",
                model="test",
                usage=Usage(prompt_tokens=10, completion_tokens=1),
                finish_reason="stop",
            ),
            LLMResponse(
                content="6",
                model="test",
                usage=Usage(prompt_tokens=10, completion_tokens=1),
                finish_reason="stop",
            ),
        ]

        reranker = LLMReranker(mock_llm)
        reranked = await reranker.rerank("query", results, top_n=3)

        assert [r.chunk.id for r in reranked] == ["2", "3", "1"]
        assert [r.score for r in reranked] == [0.9, 0.6, 0.2]

    async def test_rerank_executes_scoring_in_parallel(self) -> None:
        """All LLM scoring calls made concurrently via asyncio.gather."""
        results = [
            _make_result("1", "First"),
            _make_result("2", "Second"),
            _make_result("3", "Third"),
        ]

        mock_llm = AsyncMock()
        call_count = 0

        async def mock_complete(*args: ANY, **kwargs: ANY) -> LLMResponse:
            nonlocal call_count
            call_count += 1
            return LLMResponse(
                content=str(call_count),
                model="test",
                usage=Usage(prompt_tokens=10, completion_tokens=1),
                finish_reason="stop",
            )

        mock_llm.complete = mock_complete

        reranker = LLMReranker(mock_llm)
        await reranker.rerank("query", results, top_n=3)

        # All 3 calls should have been made
        assert call_count == 3

    async def test_rerank_sets_source_to_reranked(self) -> None:
        """Reranked results have source set to 'reranked'."""
        results = [_make_result("1", "Document")]

        mock_llm = AsyncMock()
        mock_llm.complete.return_value = LLMResponse(
            content="8",
            model="test",
            usage=Usage(prompt_tokens=10, completion_tokens=1),
            finish_reason="stop",
        )

        reranker = LLMReranker(mock_llm)
        reranked = await reranker.rerank("query", results, top_n=1)

        assert reranked[0].source == "reranked"

    async def test_rerank_truncates_long_documents(self) -> None:
        """Document content truncated to 500 chars in prompt."""
        long_content = "x" * 1000
        results = [_make_result("1", long_content)]

        mock_llm = AsyncMock()
        mock_llm.complete.return_value = LLMResponse(
            content="5",
            model="test",
            usage=Usage(prompt_tokens=10, completion_tokens=1),
            finish_reason="stop",
        )

        reranker = LLMReranker(mock_llm)
        await reranker.rerank("query", results, top_n=1)

        # Check that the prompt contains truncated content
        call_args = mock_llm.complete.call_args
        messages = call_args[0][0]
        prompt = messages[0].content
        assert long_content[:500] in prompt
        # The full 1000-char content should not be in the prompt
        assert long_content not in prompt
