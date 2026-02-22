"""Tests for vector store implementations."""
import pytest
from agentchord.rag.types import Chunk, SearchResult
from agentchord.rag.vectorstore.in_memory import InMemoryVectorStore

# Check if faiss is available for FAISS tests
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False


class TestInMemoryVectorStore:
    @pytest.fixture
    def store(self):
        return InMemoryVectorStore()

    @pytest.fixture
    def chunks_with_embeddings(self):
        return [
            Chunk(id="c1", content="hello", embedding=[1.0, 0.0, 0.0]),
            Chunk(id="c2", content="world", embedding=[0.0, 1.0, 0.0]),
            Chunk(id="c3", content="test", embedding=[0.0, 0.0, 1.0]),
        ]

    async def test_add_and_count(self, store, chunks_with_embeddings):
        ids = await store.add(chunks_with_embeddings)
        assert ids == ["c1", "c2", "c3"]
        assert await store.count() == 3

    async def test_add_without_embedding_raises(self, store):
        with pytest.raises(ValueError, match="no embedding"):
            await store.add([Chunk(id="x", content="no embedding")])

    async def test_search_returns_sorted(self, store, chunks_with_embeddings):
        await store.add(chunks_with_embeddings)
        results = await store.search([1.0, 0.0, 0.0], limit=3)
        assert len(results) == 3
        assert results[0].chunk.id == "c1"
        assert results[0].score == pytest.approx(1.0, abs=0.01)

    async def test_search_with_limit(self, store, chunks_with_embeddings):
        await store.add(chunks_with_embeddings)
        results = await store.search([1.0, 0.0, 0.0], limit=1)
        assert len(results) == 1

    async def test_search_with_filter(self, store):
        chunks = [
            Chunk(id="a", content="x", embedding=[1.0, 0.0], metadata={"type": "doc"}),
            Chunk(id="b", content="y", embedding=[0.0, 1.0], metadata={"type": "code"}),
        ]
        await store.add(chunks)
        results = await store.search([1.0, 0.0], filter={"type": "code"})
        assert len(results) == 1
        assert results[0].chunk.id == "b"

    async def test_delete(self, store, chunks_with_embeddings):
        await store.add(chunks_with_embeddings)
        deleted = await store.delete(["c1", "c2"])
        assert deleted == 2
        assert await store.count() == 1

    async def test_delete_nonexistent(self, store):
        deleted = await store.delete(["nonexistent"])
        assert deleted == 0

    async def test_clear(self, store, chunks_with_embeddings):
        await store.add(chunks_with_embeddings)
        await store.clear()
        assert await store.count() == 0

    async def test_get(self, store, chunks_with_embeddings):
        await store.add(chunks_with_embeddings)
        chunk = await store.get("c1")
        assert chunk is not None
        assert chunk.content == "hello"

    async def test_get_nonexistent(self, store):
        chunk = await store.get("nonexistent")
        assert chunk is None

    async def test_empty_search(self, store):
        results = await store.search([1.0, 0.0, 0.0])
        assert results == []

    async def test_search_source_is_vector(self, store, chunks_with_embeddings):
        await store.add(chunks_with_embeddings)
        results = await store.search([1.0, 0.0, 0.0], limit=1)
        assert results[0].source == "vector"

    async def test_filter_no_match(self, store):
        chunks = [
            Chunk(id="a", content="x", embedding=[1.0, 0.0], metadata={"type": "doc"}),
        ]
        await store.add(chunks)
        results = await store.search([1.0, 0.0], filter={"type": "nonexistent"})
        assert results == []

    async def test_add_duplicate_id_overwrites(self, store):
        c1 = Chunk(id="dup", content="first", embedding=[1.0, 0.0])
        c2 = Chunk(id="dup", content="second", embedding=[0.0, 1.0])
        await store.add([c1])
        await store.add([c2])
        assert await store.count() == 1
        chunk = await store.get("dup")
        assert chunk.content == "second"

    async def test_dimension_mismatch_raises(self, store):
        """M4: Different dimension embeddings raise ValueError."""
        c1 = Chunk(id="a", content="x", embedding=[1.0, 0.0, 0.0])  # 3D
        await store.add([c1])
        c2 = Chunk(id="b", content="y", embedding=[1.0, 0.0])  # 2D
        with pytest.raises(ValueError, match="dimension mismatch"):
            await store.add([c2])

    async def test_clear_resets_dimensions(self, store):
        """M4: clear() allows new dimensions after reset."""
        c1 = Chunk(id="a", content="x", embedding=[1.0, 0.0, 0.0])  # 3D
        await store.add([c1])
        await store.clear()
        c2 = Chunk(id="b", content="y", embedding=[1.0, 0.0])  # 2D - should work after clear
        ids = await store.add([c2])
        assert ids == ["b"]

    async def test_first_add_sets_dimensions(self, store):
        """M4: First add sets dimension constraint."""
        assert store._dimensions is None
        c1 = Chunk(id="a", content="x", embedding=[1.0, 0.0, 0.0])
        await store.add([c1])
        assert store._dimensions == 3


@pytest.mark.skipif(not FAISS_AVAILABLE, reason="faiss-cpu not installed")
class TestFAISSVectorStore:
    """FAISS vector store tests - requires faiss-cpu installation."""

    @pytest.fixture
    def store(self):
        from agentchord.rag.vectorstore.faiss import FAISSVectorStore
        return FAISSVectorStore(dimensions=3)

    @pytest.fixture
    def chunks_3d(self):
        return [
            Chunk(id="c1", content="hello", embedding=[1.0, 0.0, 0.0]),
            Chunk(id="c2", content="world", embedding=[0.0, 1.0, 0.0]),
            Chunk(id="c3", content="test", embedding=[0.0, 0.0, 1.0]),
        ]

    async def test_add_and_count(self, store, chunks_3d):
        """Basic add and count operations."""
        ids = await store.add(chunks_3d)
        assert ids == ["c1", "c2", "c3"]
        assert await store.count() == 3

    async def test_search_returns_sorted(self, store, chunks_3d):
        """Search returns results sorted by similarity score."""
        await store.add(chunks_3d)
        results = await store.search([1.0, 0.0, 0.0], limit=3)
        assert len(results) == 3
        # First result should be c1 with highest score
        assert results[0].chunk.id == "c1"
        assert results[0].score > results[1].score

    async def test_delete_soft_delete(self, store, chunks_3d):
        """H1: Delete performs soft-delete, excluded from search."""
        await store.add(chunks_3d)
        deleted = await store.delete(["c1"])
        assert deleted == 1
        # c1 should not appear in search results
        results = await store.search([1.0, 0.0, 0.0], limit=3)
        assert len(results) == 2
        assert all(r.chunk.id != "c1" for r in results)
        # Count should reflect soft-delete
        assert await store.count() == 2

    async def test_delete_nonexistent(self, store):
        """Delete nonexistent ID returns 0."""
        deleted = await store.delete(["nonexistent"])
        assert deleted == 0

    async def test_clear_resets_all(self, store, chunks_3d):
        """Clear removes all chunks."""
        await store.add(chunks_3d)
        await store.clear()
        assert await store.count() == 0
        results = await store.search([1.0, 0.0, 0.0], limit=3)
        assert results == []

    async def test_get_after_delete(self, store, chunks_3d):
        """Get after delete returns None."""
        await store.add(chunks_3d)
        await store.delete(["c1"])
        chunk = await store.get("c1")
        assert chunk is None

    async def test_dimension_mismatch(self, store):
        """M4: Adding different dimension embeddings raises ValueError."""
        from agentchord.rag.vectorstore.faiss import FAISSVectorStore
        store_3d = FAISSVectorStore(dimensions=3)
        c1 = Chunk(id="a", content="x", embedding=[1.0, 0.0, 0.0])  # 3D
        await store_3d.add([c1])
        c2 = Chunk(id="b", content="y", embedding=[1.0, 0.0])  # 2D
        with pytest.raises(ValueError, match="dimension mismatch"):
            await store_3d.add([c2])

    async def test_unsupported_index_type(self):
        """H2: Unsupported index_type raises ValueError."""
        from agentchord.rag.vectorstore.faiss import FAISSVectorStore
        with pytest.raises(ValueError, match="Unsupported index_type"):
            FAISSVectorStore(dimensions=3, index_type="hnsw")
