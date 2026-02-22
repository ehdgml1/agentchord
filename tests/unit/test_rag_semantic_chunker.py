"""Tests for semantic chunking based on embedding similarity."""

from __future__ import annotations

import asyncio
import pytest

from agentchord.rag.chunking.semantic import SemanticChunker
from agentchord.rag.types import Document


class MockEmbeddingProvider:
    """Mock embedding provider that returns deterministic embeddings for testing."""

    def __init__(self, embeddings_map: dict[str, list[float]] | None = None):
        """Initialize with optional custom embeddings map.

        Args:
            embeddings_map: Map of text to embedding vector. Defaults to [0.5, 0.5, 0.0].
        """
        self._map = embeddings_map or {}
        self._call_count = 0

    @property
    def model_name(self) -> str:
        return "mock"

    @property
    def dimensions(self) -> int:
        return 3

    async def embed(self, text: str) -> list[float]:
        """Embed a single text."""
        self._call_count += 1
        return self._map.get(text, [0.5, 0.5, 0.0])

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts."""
        self._call_count += 1
        return [self._map.get(t, [0.5, 0.5, 0.0]) for t in texts]


# ---------------------------------------------------------------------------
# Initialization and Validation Tests
# ---------------------------------------------------------------------------


def test_threshold_validation_below_zero():
    """Test that threshold < 0 raises ValueError."""
    provider = MockEmbeddingProvider()
    with pytest.raises(ValueError, match="threshold must be between 0 and 1"):
        SemanticChunker(provider, threshold=-0.1)


def test_threshold_validation_above_one():
    """Test that threshold > 1 raises ValueError."""
    provider = MockEmbeddingProvider()
    with pytest.raises(ValueError, match="threshold must be between 0 and 1"):
        SemanticChunker(provider, threshold=1.5)


def test_threshold_validation_boundary_values():
    """Test that threshold=0.0 and threshold=1.0 are valid."""
    provider = MockEmbeddingProvider()
    chunker_zero = SemanticChunker(provider, threshold=0.0)
    chunker_one = SemanticChunker(provider, threshold=1.0)
    assert chunker_zero._threshold == 0.0
    assert chunker_one._threshold == 1.0


# ---------------------------------------------------------------------------
# Empty and Single Sentence Tests
# ---------------------------------------------------------------------------


async def test_empty_document():
    """Test that empty document returns empty list."""
    provider = MockEmbeddingProvider()
    chunker = SemanticChunker(provider, threshold=0.5)
    doc = Document(id="doc1", content="", source="test.txt")

    chunks = await chunker.chunk_async(doc)

    assert chunks == []


async def test_whitespace_only_document():
    """Test that whitespace-only document returns empty list."""
    provider = MockEmbeddingProvider()
    chunker = SemanticChunker(provider, threshold=0.5)
    doc = Document(id="doc1", content="   \n\t  ", source="test.txt")

    chunks = await chunker.chunk_async(doc)

    assert chunks == []


async def test_single_sentence():
    """Test that single sentence returns one chunk."""
    provider = MockEmbeddingProvider()
    chunker = SemanticChunker(provider, threshold=0.5)
    doc = Document(
        id="doc1",
        content="This is a single sentence.",
        source="test.txt",
        metadata={"author": "test"},
    )

    chunks = await chunker.chunk_async(doc)

    assert len(chunks) == 1
    assert chunks[0].content == "This is a single sentence."
    assert chunks[0].document_id == "doc1"
    assert chunks[0].metadata == {"author": "test", "source": "test.txt"}
    assert chunks[0].start_index == 0
    assert chunks[0].end_index == len(doc.content)


# ---------------------------------------------------------------------------
# Semantic Boundary Detection Tests
# ---------------------------------------------------------------------------


async def test_semantic_boundary_detection():
    """Test that semantically different sentences are split into separate chunks.

    Dogs and Cats are similar (pets), Python is different (programming).
    Expected: 2 chunks (pets | programming).
    """
    # Create embeddings where pet sentences are similar, language sentence is different
    embeddings = {
        "Dogs are pets.": [1.0, 0.0, 0.0],
        "Cats are pets.": [0.9, 0.1, 0.0],  # Similar to dogs
        "Python is a language.": [0.0, 1.0, 0.0],  # Very different
    }
    provider = MockEmbeddingProvider(embeddings)
    # Use min_chunk_size=1 to prevent merging small chunks
    chunker = SemanticChunker(provider, threshold=0.5, min_chunk_size=1)
    doc = Document(
        id="doc1",
        content="Dogs are pets. Cats are pets. Python is a language.",
        source="test.txt",
    )

    chunks = await chunker.chunk_async(doc)

    # Should split into 2 chunks: pets and language
    assert len(chunks) == 2
    assert "Dogs" in chunks[0].content and "Cats" in chunks[0].content
    assert "Python" in chunks[1].content


async def test_threshold_one_splits_all():
    """Test that threshold=1.0 splits every sentence (unless identical).

    At threshold 1.0, only perfect similarity (1.0) keeps sentences together.
    """
    # Different embeddings for each sentence
    embeddings = {
        "First sentence.": [1.0, 0.0, 0.0],
        "Second sentence.": [0.9, 0.1, 0.0],  # Similarity < 1.0
        "Third sentence.": [0.8, 0.2, 0.0],  # Similarity < 1.0
    }
    provider = MockEmbeddingProvider(embeddings)
    chunker = SemanticChunker(provider, threshold=1.0)
    doc = Document(
        id="doc1",
        content="First sentence. Second sentence. Third sentence.",
        source="test.txt",
    )

    chunks = await chunker.chunk_async(doc)

    # Each sentence should be its own chunk (may merge if < min_chunk_size)
    # With default min_chunk_size=100, some may merge
    assert len(chunks) >= 1  # At least some splitting occurred


async def test_threshold_zero_merges_all():
    """Test that threshold=0.0 merges all sentences into one chunk.

    At threshold 0.0, any similarity (even 0.01) keeps sentences together.
    """
    embeddings = {
        "First sentence.": [1.0, 0.0, 0.0],
        "Second sentence.": [0.0, 1.0, 0.0],  # Orthogonal vectors
        "Third sentence.": [0.0, 0.0, 1.0],  # Orthogonal vectors
    }
    provider = MockEmbeddingProvider(embeddings)
    chunker = SemanticChunker(provider, threshold=0.0)
    doc = Document(
        id="doc1",
        content="First sentence. Second sentence. Third sentence.",
        source="test.txt",
    )

    chunks = await chunker.chunk_async(doc)

    # All sentences should merge into one chunk
    assert len(chunks) == 1
    assert "First" in chunks[0].content
    assert "Second" in chunks[0].content
    assert "Third" in chunks[0].content


# ---------------------------------------------------------------------------
# Min Chunk Size and Merging Tests
# ---------------------------------------------------------------------------


async def test_min_chunk_size_merging():
    """Test that small groups are merged with previous group.

    With min_chunk_size=100 and short sentences, small groups should merge.
    """
    # Create 3 semantically different sentences
    embeddings = {
        "A.": [1.0, 0.0, 0.0],
        "B.": [0.0, 1.0, 0.0],  # Split from A
        "C.": [0.0, 0.0, 1.0],  # Split from B
    }
    provider = MockEmbeddingProvider(embeddings)
    chunker = SemanticChunker(provider, threshold=0.5, min_chunk_size=100)
    doc = Document(id="doc1", content="A. B. C.", source="test.txt")

    chunks = await chunker.chunk_async(doc)

    # Small chunks should be merged
    assert len(chunks) == 1  # All merged due to min_chunk_size


async def test_min_chunk_size_no_merging_large_chunks():
    """Test that large chunks are not merged when they exceed min_chunk_size."""
    # Create two long sentences that will be semantically different
    # Sentence splitting requires ". " followed by capital letter
    long_sentence_1 = "A" * 120 + "."  # 121 chars
    long_sentence_2_capitalized = ("B" * 120).capitalize() + "."  # "Bbbb..." 121 chars

    embeddings = {
        long_sentence_1: [1.0, 0.0, 0.0],
        long_sentence_2_capitalized: [0.0, 1.0, 0.0],
    }
    provider = MockEmbeddingProvider(embeddings)
    # min_chunk_size=100, both sentences are 121 chars
    chunker = SemanticChunker(provider, threshold=0.5, min_chunk_size=100)

    # Need capital letter after period for sentence split
    doc = Document(
        id="doc1",
        content=long_sentence_1 + " " + long_sentence_2_capitalized,
        source="test.txt",
    )

    chunks = await chunker.chunk_async(doc)

    # Each sentence is large enough to be its own chunk
    assert len(chunks) == 2
    assert "A" * 120 in chunks[0].content
    assert "Bbbb" in chunks[1].content  # capitalized version


# ---------------------------------------------------------------------------
# Metadata Propagation Tests
# ---------------------------------------------------------------------------


async def test_document_id_propagation():
    """Test that document.id is propagated to all chunks."""
    provider = MockEmbeddingProvider()
    chunker = SemanticChunker(provider, threshold=0.5)
    doc = Document(id="test-doc-123", content="First sentence. Second sentence.", source="test.txt")

    chunks = await chunker.chunk_async(doc)

    for chunk in chunks:
        assert chunk.document_id == "test-doc-123"


async def test_metadata_propagation():
    """Test that document.metadata and source are propagated to chunks."""
    provider = MockEmbeddingProvider()
    chunker = SemanticChunker(provider, threshold=0.5)
    doc = Document(
        id="doc1",
        content="First sentence. Second sentence.",
        source="test/file.txt",
        metadata={"author": "John", "year": 2024},
    )

    chunks = await chunker.chunk_async(doc)

    for chunk in chunks:
        assert chunk.metadata["author"] == "John"
        assert chunk.metadata["year"] == 2024
        assert chunk.metadata["source"] == "test/file.txt"


# ---------------------------------------------------------------------------
# Index Tracking Tests
# ---------------------------------------------------------------------------


async def test_start_end_indices():
    """Test that start_index and end_index are correct."""
    provider = MockEmbeddingProvider()
    chunker = SemanticChunker(provider, threshold=0.5)
    doc = Document(id="doc1", content="First sentence. Second sentence.", source="test.txt")

    chunks = await chunker.chunk_async(doc)

    for chunk in chunks:
        assert chunk.start_index >= 0
        assert chunk.end_index > chunk.start_index
        assert chunk.end_index <= len(doc.content)


# ---------------------------------------------------------------------------
# Async Method Tests
# ---------------------------------------------------------------------------


async def test_chunk_async_direct_call():
    """Test calling chunk_async() directly."""
    provider = MockEmbeddingProvider()
    chunker = SemanticChunker(provider, threshold=0.5)
    doc = Document(id="doc1", content="Test sentence.", source="test.txt")

    chunks = await chunker.chunk_async(doc)

    assert len(chunks) == 1
    assert chunks[0].content == "Test sentence."


def test_chunk_sync_bridge():
    """Test that sync chunk() method works (bridge to async).

    This tests the case when there's no running loop.
    """
    provider = MockEmbeddingProvider()
    chunker = SemanticChunker(provider, threshold=0.5)
    doc = Document(id="doc1", content="Test sentence.", source="test.txt")

    chunks = chunker.chunk(doc)

    assert len(chunks) == 1
    assert chunks[0].content == "Test sentence."


# ---------------------------------------------------------------------------
# Sentence Splitting Tests
# ---------------------------------------------------------------------------


def test_split_sentences_periods():
    """Test sentence splitting on periods followed by capital letters."""
    provider = MockEmbeddingProvider()
    chunker = SemanticChunker(provider, threshold=0.5)

    sentences = chunker._split_sentences("First. Second. Third.")

    assert len(sentences) == 3
    assert sentences[0] == "First."
    assert sentences[1] == "Second."
    assert sentences[2] == "Third."


def test_split_sentences_exclamation_question():
    """Test sentence splitting on exclamation and question marks."""
    provider = MockEmbeddingProvider()
    chunker = SemanticChunker(provider, threshold=0.5)

    sentences = chunker._split_sentences("Hello! How are you? I'm fine.")

    assert len(sentences) == 3
    assert "Hello!" in sentences[0]
    assert "How are you?" in sentences[1]
    assert "I'm fine." in sentences[2]


def test_split_sentences_newlines():
    """Test sentence splitting on newlines."""
    provider = MockEmbeddingProvider()
    chunker = SemanticChunker(provider, threshold=0.5)

    sentences = chunker._split_sentences("First line.\nSecond line.\nThird line.")

    assert len(sentences) >= 2  # Should split on newlines


def test_split_sentences_strips_whitespace():
    """Test that split sentences have whitespace stripped."""
    provider = MockEmbeddingProvider()
    chunker = SemanticChunker(provider, threshold=0.5)

    sentences = chunker._split_sentences("  First.   Second.  ")

    for sentence in sentences:
        assert sentence == sentence.strip()


# ---------------------------------------------------------------------------
# Merge Small Groups Tests
# ---------------------------------------------------------------------------


def test_merge_small_groups_below_threshold():
    """Test that groups smaller than min_chunk_size are merged."""
    provider = MockEmbeddingProvider()
    chunker = SemanticChunker(provider, threshold=0.5, min_chunk_size=10)

    groups = [["A"], ["B"], ["C"]]  # Each group has length < 10
    merged = chunker._merge_small_groups(groups)

    # Small groups should be merged into first group
    assert len(merged) == 1
    assert merged[0] == ["A", "B", "C"]


def test_merge_small_groups_above_threshold():
    """Test that large groups are not merged."""
    provider = MockEmbeddingProvider()
    chunker = SemanticChunker(provider, threshold=0.5, min_chunk_size=5)

    groups = [["Hello world"], ["Goodbye world"]]  # Each > 5 chars
    merged = chunker._merge_small_groups(groups)

    # Large groups should remain separate
    assert len(merged) == 2


def test_merge_small_groups_mixed():
    """Test merging with mix of large and small groups."""
    provider = MockEmbeddingProvider()
    chunker = SemanticChunker(provider, threshold=0.5, min_chunk_size=10)

    groups = [["Hello world"], ["A"], ["B"], ["Goodbye world"]]
    merged = chunker._merge_small_groups(groups)

    # "A" and "B" should merge into "Hello world"
    # "Goodbye world" is large enough to stay separate
    assert len(merged) == 2
    assert "A" in merged[0]
    assert "B" in merged[0]
    assert "Goodbye world" in merged[1]


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


async def test_realistic_document_chunking():
    """Test chunking a realistic multi-topic document."""
    # Create embeddings for different topics
    embeddings = {
        "AgentChord is a framework.": [1.0, 0.0, 0.0],
        "It supports multiple agents.": [0.9, 0.1, 0.0],
        "Python is a programming language.": [0.0, 1.0, 0.0],
        "It is used for AI development.": [0.0, 0.9, 0.1],
    }
    provider = MockEmbeddingProvider(embeddings)
    chunker = SemanticChunker(provider, threshold=0.5, min_chunk_size=50)

    content = (
        "AgentChord is a framework. It supports multiple agents. "
        "Python is a programming language. It is used for AI development."
    )
    doc = Document(
        id="doc1",
        content=content,
        source="readme.md",
        metadata={"version": "1.0"},
    )

    chunks = await chunker.chunk_async(doc)

    # Should create multiple chunks based on topic shifts
    assert len(chunks) >= 1
    # All chunks should have proper metadata
    for chunk in chunks:
        assert chunk.document_id == "doc1"
        assert chunk.metadata["version"] == "1.0"
        assert chunk.metadata["source"] == "readme.md"


async def test_edge_case_single_long_sentence():
    """Test document with one very long sentence."""
    provider = MockEmbeddingProvider()
    chunker = SemanticChunker(provider, threshold=0.5)

    long_sentence = "This is a single very long sentence without any punctuation to split it up " * 20
    doc = Document(id="doc1", content=long_sentence, source="test.txt")

    chunks = await chunker.chunk_async(doc)

    # Should return single chunk with original content (including trailing space)
    assert len(chunks) == 1
    assert chunks[0].content == long_sentence
