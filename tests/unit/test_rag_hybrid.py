"""Tests for hybrid search and RRF fusion."""
import pytest
from agentchord.rag.search.hybrid import HybridSearch
from agentchord.rag.search.bm25 import BM25Search
from agentchord.rag.types import Chunk, SearchResult
from agentchord.rag.vectorstore.in_memory import InMemoryVectorStore


class TestRRFFusion:
    """Test the static RRF fusion algorithm."""

    def test_single_list(self):
        chunks = [Chunk(id=f"c{i}", content=f"text{i}") for i in range(3)]
        results = [SearchResult(chunk=c, score=1.0 - i * 0.1) for i, c in enumerate(chunks)]
        fused = HybridSearch._rrf_fuse([results], [1.0], k=60)
        assert len(fused) == 3
        assert fused[0].chunk.id == "c0"

    def test_two_lists_merge(self):
        c1 = Chunk(id="a", content="a")
        c2 = Chunk(id="b", content="b")
        c3 = Chunk(id="c", content="c")

        list1 = [
            SearchResult(chunk=c1, score=1.0),
            SearchResult(chunk=c2, score=0.8),
        ]
        list2 = [
            SearchResult(chunk=c2, score=1.0),  # b appears in both
            SearchResult(chunk=c3, score=0.8),
        ]

        fused = HybridSearch._rrf_fuse([list1, list2], [1.0, 1.0], k=60)
        # "b" should rank highest (appears in both lists)
        assert fused[0].chunk.id == "b"

    def test_weights_affect_ranking(self):
        c1 = Chunk(id="x", content="x")
        c2 = Chunk(id="y", content="y")

        list1 = [SearchResult(chunk=c1, score=1.0)]  # only in list1
        list2 = [SearchResult(chunk=c2, score=1.0)]  # only in list2

        # With equal weights, both have same score
        fused_equal = HybridSearch._rrf_fuse([list1, list2], [1.0, 1.0])
        scores = {r.chunk.id: r.score for r in fused_equal}
        assert scores["x"] == pytest.approx(scores["y"])

        # With higher weight on list1, x should rank higher
        fused_weighted = HybridSearch._rrf_fuse([list1, list2], [2.0, 1.0])
        scores = {r.chunk.id: r.score for r in fused_weighted}
        assert scores["x"] > scores["y"]

    def test_empty_lists(self):
        fused = HybridSearch._rrf_fuse([], [])
        assert fused == []

    def test_mismatched_weights_raises(self):
        with pytest.raises(ValueError):
            HybridSearch._rrf_fuse([[]], [1.0, 2.0])

    def test_fused_source_is_hybrid(self):
        chunk = Chunk(id="a", content="a")
        results = [SearchResult(chunk=chunk, score=1.0)]
        fused = HybridSearch._rrf_fuse([results], [1.0])
        assert fused[0].source == "hybrid"

    def test_rrf_scores_decrease_with_rank(self):
        chunks = [Chunk(id=f"c{i}", content=f"t{i}") for i in range(5)]
        results = [SearchResult(chunk=c, score=1.0 - i * 0.1) for i, c in enumerate(chunks)]
        fused = HybridSearch._rrf_fuse([results], [1.0], k=60)
        for i in range(len(fused) - 1):
            assert fused[i].score >= fused[i + 1].score

    def test_empty_result_lists(self):
        fused = HybridSearch._rrf_fuse([[], []], [1.0, 1.0])
        assert fused == []


class TestHybridSearch:
    """Test HybridSearch integration."""

    @pytest.fixture
    def hybrid(self, mock_embedding_provider):
        return HybridSearch(
            vectorstore=InMemoryVectorStore(),
            embedding_provider=mock_embedding_provider,
            bm25=BM25Search(),
        )

    async def test_add_and_search(self, hybrid):
        chunks = [
            Chunk(id="c1", content="AgentChord multi-agent framework"),
            Chunk(id="c2", content="Python programming language"),
        ]
        ids = await hybrid.add(chunks)
        assert len(ids) == 2

        result = await hybrid.search("AgentChord framework")
        assert len(result.results) > 0
        assert result.query == "AgentChord framework"

    async def test_search_empty_query(self, hybrid):
        result = await hybrid.search("   ")
        assert result.results == []

    async def test_add_empty_list(self, hybrid):
        ids = await hybrid.add([])
        assert ids == []

    async def test_delete(self, hybrid):
        chunks = [
            Chunk(id="c1", content="test content here"),
        ]
        await hybrid.add(chunks)
        deleted = await hybrid.delete(["c1"])
        assert deleted == 1

    async def test_delete_empty_list(self, hybrid):
        deleted = await hybrid.delete([])
        assert deleted == 0

    async def test_clear(self, hybrid):
        chunks = [Chunk(id="c1", content="test content for clearing")]
        await hybrid.add(chunks)
        await hybrid.clear()
        result = await hybrid.search("test content")
        assert result.results == []

    async def test_search_has_timing(self, hybrid):
        chunks = [Chunk(id="c1", content="timing test data")]
        await hybrid.add(chunks)
        result = await hybrid.search("timing")
        assert result.retrieval_ms > 0
        assert result.total_ms > 0

    async def test_chunks_with_precomputed_embeddings(self, hybrid):
        chunks = [
            Chunk(id="c1", content="pre-embedded", embedding=[0.5, 0.5, 0.5, 0.5]),
        ]
        ids = await hybrid.add(chunks)
        assert ids == ["c1"]

    async def test_search_limit(self, hybrid):
        chunks = [
            Chunk(id=f"c{i}", content=f"document number {i} about testing")
            for i in range(10)
        ]
        await hybrid.add(chunks)
        result = await hybrid.search("document testing", limit=3)
        assert len(result.results) <= 3
