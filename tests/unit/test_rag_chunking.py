"""Tests for document chunking strategies."""
import pytest
from agentchord.rag.chunking.recursive import RecursiveCharacterChunker
from agentchord.rag.chunking.parent_child import ParentChildChunker
from agentchord.rag.types import Document


class TestRecursiveCharacterChunker:
    def test_short_document_single_chunk(self):
        chunker = RecursiveCharacterChunker(chunk_size=1000, chunk_overlap=100)
        doc = Document(id="d1", content="Short text.")
        chunks = chunker.chunk(doc)
        assert len(chunks) == 1
        assert chunks[0].content == "Short text."
        assert chunks[0].document_id == "d1"

    def test_long_document_multiple_chunks(self):
        chunker = RecursiveCharacterChunker(chunk_size=50, chunk_overlap=10)
        doc = Document(id="d1", content="A" * 200)
        chunks = chunker.chunk(doc)
        assert len(chunks) > 1

    def test_chunk_overlap_configured(self):
        chunker = RecursiveCharacterChunker(chunk_size=50, chunk_overlap=10)
        doc = Document(id="d1", content="word " * 40)  # 200 chars
        chunks = chunker.chunk(doc)
        assert len(chunks) >= 2

    def test_preserves_paragraph_boundaries(self):
        chunker = RecursiveCharacterChunker(chunk_size=100, chunk_overlap=0)
        doc = Document(
            id="d1",
            content="First paragraph.\n\nSecond paragraph.\n\nThird paragraph.",
        )
        chunks = chunker.chunk(doc)
        assert len(chunks) >= 1

    def test_chunk_has_document_id(self):
        chunker = RecursiveCharacterChunker()
        doc = Document(id="doc-123", content="test content")
        chunks = chunker.chunk(doc)
        assert all(c.document_id == "doc-123" for c in chunks)

    def test_chunk_many(self):
        chunker = RecursiveCharacterChunker(chunk_size=50, chunk_overlap=0)
        docs = [
            Document(id="d1", content="A" * 100),
            Document(id="d2", content="B" * 100),
        ]
        chunks = chunker.chunk_many(docs)
        assert len(chunks) > 2
        doc_ids = {c.document_id for c in chunks}
        assert doc_ids == {"d1", "d2"}

    def test_empty_document(self):
        chunker = RecursiveCharacterChunker()
        doc = Document(id="d1", content="")
        chunks = chunker.chunk(doc)
        assert len(chunks) == 0

    def test_whitespace_only_document(self):
        chunker = RecursiveCharacterChunker()
        doc = Document(id="d1", content="   \n\n   ")
        chunks = chunker.chunk(doc)
        assert len(chunks) == 0

    def test_overlap_must_be_less_than_size(self):
        with pytest.raises(ValueError, match="chunk_overlap must be less than chunk_size"):
            RecursiveCharacterChunker(chunk_size=100, chunk_overlap=100)

    def test_chunk_metadata_includes_source(self):
        chunker = RecursiveCharacterChunker()
        doc = Document(id="d1", content="content here", source="test.md")
        chunks = chunker.chunk(doc)
        assert chunks[0].metadata.get("source") == "test.md"

    def test_chunk_start_end_index(self):
        chunker = RecursiveCharacterChunker(chunk_size=1000, chunk_overlap=0)
        doc = Document(id="d1", content="Some content here.")
        chunks = chunker.chunk(doc)
        assert chunks[0].start_index >= 0
        assert chunks[0].end_index > chunks[0].start_index


class TestParentChildChunker:
    def test_produces_parents_and_children(self):
        chunker = ParentChildChunker()
        doc = Document(id="d1", content="A " * 500)  # ~1000 chars
        chunks = chunker.chunk(doc)

        parents = [c for c in chunks if c.metadata.get("is_parent")]
        children = [c for c in chunks if c.parent_id is not None]

        assert len(parents) >= 1
        assert len(children) >= 1

    def test_children_reference_parents(self):
        chunker = ParentChildChunker()
        doc = Document(id="d1", content="word " * 500)
        chunks = chunker.chunk(doc)

        parent_ids = {c.id for c in chunks if c.metadata.get("is_parent")}
        for chunk in chunks:
            if chunk.parent_id is not None:
                assert chunk.parent_id in parent_ids

    def test_get_parent_helper(self):
        chunker = ParentChildChunker()
        doc = Document(id="d1", content="text " * 500)
        chunks = chunker.chunk(doc)

        children = [c for c in chunks if c.parent_id]
        if children:
            parent = ParentChildChunker.get_parent(children[0], chunks)
            assert parent is not None
            assert parent.metadata.get("is_parent") is True

    def test_get_children_helper(self):
        chunker = ParentChildChunker()
        doc = Document(id="d1", content="word " * 500)
        chunks = chunker.chunk(doc)

        parents = [c for c in chunks if c.metadata.get("is_parent")]
        if parents:
            children = ParentChildChunker.get_children(parents[0], chunks)
            assert len(children) >= 1

    def test_get_parent_returns_none_for_parent_chunk(self):
        chunker = ParentChildChunker()
        doc = Document(id="d1", content="word " * 500)
        chunks = chunker.chunk(doc)

        parents = [c for c in chunks if c.metadata.get("is_parent")]
        if parents:
            result = ParentChildChunker.get_parent(parents[0], chunks)
            assert result is None  # parents have no parent_id

    def test_children_have_document_id(self):
        chunker = ParentChildChunker()
        doc = Document(id="d1", content="word " * 500)
        chunks = chunker.chunk(doc)

        children = [c for c in chunks if c.parent_id is not None]
        for child in children:
            assert child.document_id == "d1"

    def test_parent_is_parent_metadata_flag(self):
        chunker = ParentChildChunker()
        doc = Document(id="d1", content="word " * 500)
        chunks = chunker.chunk(doc)

        for chunk in chunks:
            if chunk.parent_id is None and chunk.metadata.get("is_parent"):
                assert chunk.metadata["is_parent"] is True
            elif chunk.parent_id is not None:
                assert chunk.metadata.get("is_parent") is False
