"""Tests for RAG type definitions."""
from agentchord.rag.types import Chunk, Document, RAGResponse, RetrievalResult, SearchResult


class TestDocument:
    def test_create_document(self):
        doc = Document(content="Hello world")
        assert doc.content == "Hello world"
        assert doc.id  # auto-generated UUID
        assert doc.metadata == {}
        assert doc.source == ""

    def test_document_with_metadata(self):
        doc = Document(content="test", metadata={"key": "value"}, source="test.txt")
        assert doc.metadata == {"key": "value"}
        assert doc.source == "test.txt"

    def test_document_unique_ids(self):
        d1 = Document(content="a")
        d2 = Document(content="b")
        assert d1.id != d2.id

    def test_document_custom_id(self):
        doc = Document(id="custom-id", content="test")
        assert doc.id == "custom-id"

    def test_document_created_at(self):
        doc = Document(content="test")
        assert doc.created_at is not None


class TestChunk:
    def test_create_chunk(self):
        chunk = Chunk(content="Hello")
        assert chunk.content == "Hello"
        assert chunk.embedding is None
        assert chunk.parent_id is None
        assert chunk.document_id == ""

    def test_chunk_with_embedding(self):
        chunk = Chunk(content="test", embedding=[0.1, 0.2, 0.3])
        assert chunk.embedding == [0.1, 0.2, 0.3]

    def test_chunk_with_parent(self):
        chunk = Chunk(content="child", parent_id="parent-1")
        assert chunk.parent_id == "parent-1"

    def test_chunk_start_end_index(self):
        chunk = Chunk(content="test", start_index=10, end_index=20)
        assert chunk.start_index == 10
        assert chunk.end_index == 20

    def test_chunk_unique_ids(self):
        c1 = Chunk(content="a")
        c2 = Chunk(content="b")
        assert c1.id != c2.id


class TestSearchResult:
    def test_create_search_result(self):
        chunk = Chunk(content="test")
        result = SearchResult(chunk=chunk, score=0.95)
        assert result.score == 0.95
        assert result.source == "vector"

    def test_search_result_custom_source(self):
        chunk = Chunk(content="test")
        result = SearchResult(chunk=chunk, score=0.8, source="bm25")
        assert result.source == "bm25"

    def test_search_result_score_range(self):
        chunk = Chunk(content="test")
        result = SearchResult(chunk=chunk, score=0.0)
        assert result.score == 0.0


class TestRetrievalResult:
    def test_empty_result(self):
        result = RetrievalResult(query="test")
        assert result.results == []
        assert result.contexts == []
        assert result.context_string == ""

    def test_contexts_property(self):
        chunks = [Chunk(content=f"ctx{i}") for i in range(3)]
        results = [SearchResult(chunk=c, score=0.9) for c in chunks]
        rr = RetrievalResult(query="q", results=results)
        assert rr.contexts == ["ctx0", "ctx1", "ctx2"]

    def test_context_string_joins(self):
        chunks = [Chunk(content="a"), Chunk(content="b")]
        results = [SearchResult(chunk=c, score=0.9) for c in chunks]
        rr = RetrievalResult(query="q", results=results)
        assert "---" in rr.context_string
        assert "a" in rr.context_string
        assert "b" in rr.context_string

    def test_timing_fields(self):
        rr = RetrievalResult(query="q", retrieval_ms=10.5, rerank_ms=5.0, total_ms=15.5)
        assert rr.retrieval_ms == 10.5
        assert rr.rerank_ms == 5.0
        assert rr.total_ms == 15.5


class TestRAGResponse:
    def test_create_response(self):
        rr = RetrievalResult(query="q")
        resp = RAGResponse(query="q", answer="ans", retrieval=rr)
        assert resp.answer == "ans"
        assert resp.usage == {}
        assert resp.source_documents == []

    def test_response_with_usage(self):
        rr = RetrievalResult(query="q")
        resp = RAGResponse(
            query="q",
            answer="a",
            retrieval=rr,
            usage={"prompt_tokens": 100, "completion_tokens": 50},
        )
        assert resp.usage["prompt_tokens"] == 100

    def test_response_with_sources(self):
        rr = RetrievalResult(query="q")
        resp = RAGResponse(
            query="q",
            answer="a",
            retrieval=rr,
            source_documents=["doc1", "doc2"],
        )
        assert resp.source_documents == ["doc1", "doc2"]
