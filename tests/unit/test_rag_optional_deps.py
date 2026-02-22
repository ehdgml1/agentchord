"""Tests for RAG optional-dependency implementations.

Covers OpenAIEmbeddings, OllamaEmbeddings, SentenceTransformerEmbeddings,
and ChromaVectorStore using mocks to avoid requiring actual optional packages.

Complements existing tests in:
- test_rag_pdf_loader.py (PDFLoader already fully covered)
- test_rag_web_loader.py (WebLoader already covered; adds regex fallback test)
- test_rag_reranker.py (CrossEncoder/LLMReranker already fully covered)
- test_rag_vectorstore.py (InMemory/FAISS covered; adds ChromaDB)
"""

from __future__ import annotations

import asyncio
import sys
from types import ModuleType
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentchord.rag.types import Chunk, SearchResult


# ---------------------------------------------------------------------------
# OpenAIEmbeddings
# ---------------------------------------------------------------------------


class TestOpenAIEmbeddings:
    """Tests for OpenAIEmbeddings with mocked openai.AsyncOpenAI."""

    def _make_provider(
        self,
        mock_client: Any,
        model: str = "text-embedding-3-small",
        api_key: str | None = "test-key",
        dimensions: int | None = None,
    ):
        """Create an OpenAIEmbeddings instance with a pre-injected mock client."""
        from agentchord.rag.embeddings.openai import OpenAIEmbeddings

        provider = OpenAIEmbeddings(
            model=model, api_key=api_key, dimensions=dimensions
        )
        provider._client = mock_client
        return provider

    def _mock_embedding_response(
        self, embeddings: list[list[float]]
    ) -> MagicMock:
        """Create a mock OpenAI embedding response."""
        items = []
        for emb in embeddings:
            item = MagicMock()
            item.embedding = emb
            items.append(item)
        response = MagicMock()
        response.data = items
        return response

    async def test_embed_single_text(self):
        """embed() calls client.embeddings.create with correct params."""
        expected = [0.1, 0.2, 0.3]
        mock_client = AsyncMock()
        mock_client.embeddings.create = AsyncMock(
            return_value=self._mock_embedding_response([expected])
        )
        provider = self._make_provider(mock_client)

        result = await provider.embed("hello world")

        assert result == expected
        mock_client.embeddings.create.assert_awaited_once()
        call_kwargs = mock_client.embeddings.create.call_args.kwargs
        assert call_kwargs["model"] == "text-embedding-3-small"
        assert call_kwargs["input"] == ["hello world"]
        assert call_kwargs["dimensions"] == 1536

    async def test_embed_batch_multiple_texts(self):
        """embed_batch() embeds multiple texts in one call when under batch_size."""
        embeddings = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        mock_client = AsyncMock()
        mock_client.embeddings.create = AsyncMock(
            return_value=self._mock_embedding_response(embeddings)
        )
        provider = self._make_provider(mock_client)

        result = await provider.embed_batch(["a", "b", "c"])

        assert result == embeddings
        mock_client.embeddings.create.assert_awaited_once()
        call_kwargs = mock_client.embeddings.create.call_args.kwargs
        assert call_kwargs["input"] == ["a", "b", "c"]

    async def test_embed_batch_empty_list(self):
        """embed_batch() with empty list returns empty without API call."""
        mock_client = AsyncMock()
        provider = self._make_provider(mock_client)

        result = await provider.embed_batch([])

        assert result == []
        mock_client.embeddings.create.assert_not_awaited()

    async def test_embed_batch_chunks_at_2048(self):
        """embed_batch() splits texts into chunks of 2048 for API batching."""
        batch_size = 2048
        total_texts = 3000
        texts = [f"text_{i}" for i in range(total_texts)]
        single_emb = [0.1]

        call_count = 0

        async def mock_create(**kwargs: Any) -> MagicMock:
            nonlocal call_count
            call_count += 1
            n = len(kwargs["input"])
            return self._mock_embedding_response([[0.1]] * n)

        mock_client = AsyncMock()
        mock_client.embeddings.create = AsyncMock(side_effect=mock_create)
        provider = self._make_provider(mock_client)

        result = await provider.embed_batch(texts)

        assert len(result) == total_texts
        # 3000 texts / 2048 batch_size = 2 batches (2048 + 952)
        assert call_count == 2

    async def test_dimensions_property(self):
        """dimensions returns configured value or model default."""
        from agentchord.rag.embeddings.openai import OpenAIEmbeddings

        # Default for text-embedding-3-small
        p1 = OpenAIEmbeddings(model="text-embedding-3-small")
        assert p1.dimensions == 1536

        # Default for text-embedding-3-large
        p2 = OpenAIEmbeddings(model="text-embedding-3-large")
        assert p2.dimensions == 3072

        # Custom override
        p3 = OpenAIEmbeddings(model="text-embedding-3-small", dimensions=512)
        assert p3.dimensions == 512

        # Unknown model fallback
        p4 = OpenAIEmbeddings(model="unknown-model")
        assert p4.dimensions == 1536

    async def test_model_name_property(self):
        """model_name returns the configured model string."""
        from agentchord.rag.embeddings.openai import OpenAIEmbeddings

        p = OpenAIEmbeddings(model="text-embedding-ada-002")
        assert p.model_name == "text-embedding-ada-002"

    async def test_import_error_when_openai_not_installed(self):
        """ImportError raised with helpful message when openai package missing."""
        from agentchord.rag.embeddings.openai import OpenAIEmbeddings

        provider = OpenAIEmbeddings()
        provider._client = None  # Force lazy init

        with patch.dict(sys.modules, {"openai": None}):
            with pytest.raises(ImportError, match="openai is required"):
                provider._get_client()

    async def test_no_dimensions_kwarg_for_ada_002(self):
        """Non-embedding-3 models do not send dimensions parameter."""
        mock_client = AsyncMock()
        mock_client.embeddings.create = AsyncMock(
            return_value=self._mock_embedding_response([[0.1]])
        )
        provider = self._make_provider(mock_client, model="text-embedding-ada-002")

        await provider.embed("test")

        call_kwargs = mock_client.embeddings.create.call_args.kwargs
        assert "dimensions" not in call_kwargs

    async def test_api_key_passed_to_client(self):
        """api_key is forwarded to AsyncOpenAI constructor."""
        mock_openai_module = MagicMock()
        mock_async_client_class = MagicMock()
        mock_openai_module.AsyncOpenAI = mock_async_client_class

        with patch.dict(sys.modules, {"openai": mock_openai_module}):
            from agentchord.rag.embeddings.openai import OpenAIEmbeddings

            provider = OpenAIEmbeddings(api_key="sk-test-123")
            provider._client = None
            provider._get_client()

            mock_async_client_class.assert_called_once_with(api_key="sk-test-123")


# ---------------------------------------------------------------------------
# OllamaEmbeddings
# ---------------------------------------------------------------------------


class TestOllamaEmbeddings:
    """Tests for OllamaEmbeddings with mocked httpx.AsyncClient."""

    def _mock_response(self, embedding: list[float]) -> MagicMock:
        """Create a mock httpx response with embedding data."""
        resp = MagicMock()
        resp.json.return_value = {"embedding": embedding}
        resp.raise_for_status = MagicMock()
        return resp

    async def test_embed_single_text(self):
        """embed() sends POST to /api/embeddings with correct payload."""
        from agentchord.rag.embeddings.ollama import OllamaEmbeddings

        expected = [0.1, 0.2, 0.3]

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=self._mock_response(expected))
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            provider = OllamaEmbeddings(model="nomic-embed-text")
            result = await provider.embed("hello")

        assert result == expected
        mock_client.post.assert_awaited_once_with(
            "http://localhost:11434/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": "hello"},
            timeout=30.0,
        )

    async def test_embed_batch_parallel_calls(self):
        """embed_batch() sends one HTTP request per text concurrently."""
        from agentchord.rag.embeddings.ollama import OllamaEmbeddings

        embeddings = [[0.1], [0.2], [0.3]]
        call_order: list[str] = []

        async def mock_post(url: str, json: dict, timeout: float) -> MagicMock:
            text = json["prompt"]
            call_order.append(text)
            idx = ["a", "b", "c"].index(text)
            return self._mock_response(embeddings[idx])

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=mock_post)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            provider = OllamaEmbeddings()
            result = await provider.embed_batch(["a", "b", "c"])

        assert result == embeddings
        assert len(call_order) == 3

    async def test_embed_batch_empty_list(self):
        """embed_batch() with empty list returns empty without HTTP calls."""
        from agentchord.rag.embeddings.ollama import OllamaEmbeddings

        provider = OllamaEmbeddings()
        result = await provider.embed_batch([])
        assert result == []

    async def test_dimensions_property(self):
        """dimensions returns configured value."""
        from agentchord.rag.embeddings.ollama import OllamaEmbeddings

        p = OllamaEmbeddings(dimensions=1024)
        assert p.dimensions == 1024

        p_default = OllamaEmbeddings()
        assert p_default.dimensions == 768

    async def test_model_name_property(self):
        """model_name returns configured model."""
        from agentchord.rag.embeddings.ollama import OllamaEmbeddings

        p = OllamaEmbeddings(model="mxbai-embed-large")
        assert p.model_name == "mxbai-embed-large"

    async def test_custom_base_url(self):
        """Custom base_url with trailing slash is normalized."""
        from agentchord.rag.embeddings.ollama import OllamaEmbeddings

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=self._mock_response([0.1]))
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            provider = OllamaEmbeddings(base_url="http://my-server:11434/")
            await provider.embed("test")

        mock_client.post.assert_awaited_once()
        call_url = mock_client.post.call_args[0][0]
        assert call_url == "http://my-server:11434/api/embeddings"

    async def test_http_error_propagated(self):
        """HTTP errors from Ollama are propagated to caller."""
        import httpx

        from agentchord.rag.embeddings.ollama import OllamaEmbeddings

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            error_resp = MagicMock()
            error_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "500 Internal Server Error",
                request=MagicMock(),
                response=error_resp,
            )
            mock_client.post = AsyncMock(return_value=error_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            provider = OllamaEmbeddings()
            with pytest.raises(httpx.HTTPStatusError):
                await provider.embed("test")


# ---------------------------------------------------------------------------
# SentenceTransformerEmbeddings
# ---------------------------------------------------------------------------


class TestSentenceTransformerEmbeddings:
    """Tests for SentenceTransformerEmbeddings with mocked sentence_transformers."""

    def _make_provider(self, mock_model: Any, model_name: str = "all-MiniLM-L6-v2"):
        """Create provider with pre-injected mock model."""
        from agentchord.rag.embeddings.sentence_transformer import (
            SentenceTransformerEmbeddings,
        )

        provider = SentenceTransformerEmbeddings(model=model_name)
        provider._model = mock_model
        return provider

    def _make_numpy_like(self, data: list[list[float]]) -> list[MagicMock]:
        """Create mock objects that behave like numpy arrays with .tolist()."""
        result = []
        for row in data:
            mock_arr = MagicMock()
            mock_arr.tolist.return_value = row
            result.append(mock_arr)
        return result

    async def test_embed_single_text(self):
        """embed() encodes single text with normalize_embeddings=True."""
        expected = [0.1, 0.2, 0.3]
        mock_model = MagicMock()
        mock_model.encode.return_value = self._make_numpy_like([expected])

        provider = self._make_provider(mock_model)
        result = await provider.embed("hello")

        assert result == expected
        mock_model.encode.assert_called_once_with(
            ["hello"], normalize_embeddings=True
        )

    async def test_embed_batch_multiple_texts(self):
        """embed_batch() encodes all texts in a single call."""
        expected = [[0.1, 0.2], [0.3, 0.4]]
        mock_model = MagicMock()
        mock_model.encode.return_value = self._make_numpy_like(expected)

        provider = self._make_provider(mock_model)
        result = await provider.embed_batch(["a", "b"])

        assert result == expected
        mock_model.encode.assert_called_once_with(
            ["a", "b"], normalize_embeddings=True
        )

    async def test_embed_batch_empty_list(self):
        """embed_batch() with empty list returns empty without model call."""
        mock_model = MagicMock()
        provider = self._make_provider(mock_model)

        result = await provider.embed_batch([])

        assert result == []
        mock_model.encode.assert_not_called()

    async def test_dimensions_property(self):
        """dimensions returns known model dimension or default 384."""
        from agentchord.rag.embeddings.sentence_transformer import (
            SentenceTransformerEmbeddings,
        )

        assert SentenceTransformerEmbeddings(model="all-MiniLM-L6-v2").dimensions == 384
        assert SentenceTransformerEmbeddings(model="all-mpnet-base-v2").dimensions == 768
        assert SentenceTransformerEmbeddings(model="BAAI/bge-m3").dimensions == 1024
        assert SentenceTransformerEmbeddings(model="unknown-model").dimensions == 384

    async def test_model_name_property(self):
        """model_name returns configured model string."""
        from agentchord.rag.embeddings.sentence_transformer import (
            SentenceTransformerEmbeddings,
        )

        p = SentenceTransformerEmbeddings(model="all-mpnet-base-v2")
        assert p.model_name == "all-mpnet-base-v2"

    async def test_import_error_when_not_installed(self):
        """ImportError raised with helpful message when sentence-transformers missing."""
        from agentchord.rag.embeddings.sentence_transformer import (
            SentenceTransformerEmbeddings,
        )

        provider = SentenceTransformerEmbeddings()
        provider._model = None

        with patch.dict(sys.modules, {"sentence_transformers": None}):
            with pytest.raises(ImportError, match="sentence-transformers is required"):
                provider._get_model()

    async def test_device_passed_to_model(self):
        """device parameter forwarded to SentenceTransformer constructor."""
        mock_st_module = MagicMock()
        mock_model_class = MagicMock()
        mock_st_module.SentenceTransformer = mock_model_class

        with patch.dict(sys.modules, {"sentence_transformers": mock_st_module}):
            from agentchord.rag.embeddings.sentence_transformer import (
                SentenceTransformerEmbeddings,
            )

            provider = SentenceTransformerEmbeddings(
                model="all-MiniLM-L6-v2", device="cuda"
            )
            provider._model = None
            provider._get_model()

            mock_model_class.assert_called_once_with(
                "all-MiniLM-L6-v2", device="cuda"
            )


# ---------------------------------------------------------------------------
# ChromaVectorStore
# ---------------------------------------------------------------------------


class TestChromaVectorStore:
    """Tests for ChromaVectorStore with mocked chromadb."""

    def _make_mock_chromadb(self) -> tuple[MagicMock, MagicMock, MagicMock]:
        """Create mock chromadb module, client, and collection.

        Returns:
            (mock_module, mock_client, mock_collection) tuple.
        """
        mock_collection = MagicMock()
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        mock_module = MagicMock()
        mock_module.Client.return_value = mock_client
        mock_module.PersistentClient.return_value = mock_client

        return mock_module, mock_client, mock_collection

    def _make_store(
        self,
        mock_collection: MagicMock,
        collection_name: str = "test",
    ):
        """Create a ChromaVectorStore with pre-injected collection."""
        from agentchord.rag.vectorstore.chroma import ChromaVectorStore

        store = ChromaVectorStore(collection_name=collection_name)
        store._collection = mock_collection
        store._client = MagicMock()
        return store

    def _make_chunks(self) -> list[Chunk]:
        """Create test chunks with embeddings and metadata."""
        return [
            Chunk(
                id="c1",
                content="hello world",
                embedding=[0.1, 0.2, 0.3],
                document_id="doc1",
                start_index=0,
                end_index=11,
                metadata={"topic": "greeting"},
            ),
            Chunk(
                id="c2",
                content="goodbye world",
                embedding=[0.4, 0.5, 0.6],
                document_id="doc1",
                start_index=12,
                end_index=25,
                parent_id="parent1",
                metadata={"topic": "farewell"},
            ),
        ]

    async def test_add_upserts_with_correct_structure(self):
        """add() calls collection.upsert with ids, embeddings, documents, metadatas."""
        _, _, mock_collection = self._make_mock_chromadb()
        store = self._make_store(mock_collection)
        chunks = self._make_chunks()

        ids = await store.add(chunks)

        assert ids == ["c1", "c2"]
        mock_collection.upsert.assert_called_once()
        call_kwargs = mock_collection.upsert.call_args.kwargs
        assert call_kwargs["ids"] == ["c1", "c2"]
        assert call_kwargs["embeddings"] == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        assert call_kwargs["documents"] == ["hello world", "goodbye world"]

    async def test_add_stores_internal_metadata(self):
        """add() stores _document_id, _start_index, _end_index, _parent_id in metadata."""
        _, _, mock_collection = self._make_mock_chromadb()
        store = self._make_store(mock_collection)
        chunks = self._make_chunks()

        await store.add(chunks)

        call_kwargs = mock_collection.upsert.call_args.kwargs
        meta1 = call_kwargs["metadatas"][0]
        assert meta1["_document_id"] == "doc1"
        assert meta1["_start_index"] == 0
        assert meta1["_end_index"] == 11
        assert meta1["_parent_id"] == ""
        assert meta1["topic"] == "greeting"

        meta2 = call_kwargs["metadatas"][1]
        assert meta2["_parent_id"] == "parent1"

    async def test_add_empty_list(self):
        """add() with empty list returns empty without calling upsert."""
        _, _, mock_collection = self._make_mock_chromadb()
        store = self._make_store(mock_collection)

        ids = await store.add([])

        assert ids == []
        mock_collection.upsert.assert_not_called()

    async def test_add_raises_on_missing_embedding(self):
        """add() raises ValueError if a chunk has no embedding."""
        _, _, mock_collection = self._make_mock_chromadb()
        store = self._make_store(mock_collection)
        chunk = Chunk(id="no-emb", content="test")

        with pytest.raises(ValueError, match="no embedding"):
            await store.add([chunk])

    async def test_search_converts_distances_to_scores(self):
        """search() converts Chroma distances to 1-distance scores."""
        _, _, mock_collection = self._make_mock_chromadb()
        mock_collection.query.return_value = {
            "ids": [["c1", "c2"]],
            "distances": [[0.2, 0.8]],
            "documents": [["hello", "world"]],
            "metadatas": [[
                {"_document_id": "doc1", "_start_index": 0, "_end_index": 5, "_parent_id": "", "topic": "a"},
                {"_document_id": "doc2", "_start_index": 0, "_end_index": 5, "_parent_id": "p1", "topic": "b"},
            ]],
        }
        store = self._make_store(mock_collection)

        results = await store.search([0.1, 0.2, 0.3], limit=5)

        assert len(results) == 2
        assert results[0].score == pytest.approx(0.8)
        assert results[1].score == pytest.approx(0.2)
        assert results[0].chunk.id == "c1"
        assert results[0].chunk.content == "hello"
        assert results[0].source == "vector"

    async def test_search_strips_internal_metadata(self):
        """search() excludes _prefixed keys from returned chunk metadata."""
        _, _, mock_collection = self._make_mock_chromadb()
        mock_collection.query.return_value = {
            "ids": [["c1"]],
            "distances": [[0.1]],
            "documents": [["hello"]],
            "metadatas": [[{
                "_document_id": "doc1",
                "_start_index": 0,
                "_end_index": 5,
                "_parent_id": "",
                "topic": "test",
                "author": "alice",
            }]],
        }
        store = self._make_store(mock_collection)

        results = await store.search([0.1], limit=1)

        chunk = results[0].chunk
        assert "topic" in chunk.metadata
        assert "author" in chunk.metadata
        assert "_document_id" not in chunk.metadata
        assert "_start_index" not in chunk.metadata
        assert chunk.document_id == "doc1"
        assert chunk.start_index == 0

    async def test_search_with_filter(self):
        """search() passes filter as 'where' to collection.query."""
        _, _, mock_collection = self._make_mock_chromadb()
        mock_collection.query.return_value = {
            "ids": [[]], "distances": [[]], "documents": [[]], "metadatas": [[]]
        }
        store = self._make_store(mock_collection)

        await store.search([0.1], limit=5, filter={"topic": "test"})

        call_kwargs = mock_collection.query.call_args.kwargs
        assert call_kwargs["where"] == {"topic": "test"}

    async def test_search_empty_result(self):
        """search() returns empty list when no results found."""
        _, _, mock_collection = self._make_mock_chromadb()
        mock_collection.query.return_value = {
            "ids": [[]], "distances": [[]], "documents": [[]], "metadatas": [[]]
        }
        store = self._make_store(mock_collection)

        results = await store.search([0.1], limit=5)
        assert results == []

    async def test_search_clamps_negative_scores(self):
        """search() clamps scores to minimum 0.0 when distance > 1.0."""
        _, _, mock_collection = self._make_mock_chromadb()
        mock_collection.query.return_value = {
            "ids": [["c1"]],
            "distances": [[1.5]],  # distance > 1 -> score would be negative
            "documents": [["text"]],
            "metadatas": [[{"_document_id": "", "_start_index": 0, "_end_index": 0, "_parent_id": ""}]],
        }
        store = self._make_store(mock_collection)

        results = await store.search([0.1], limit=1)
        assert results[0].score == 0.0

    async def test_search_reconstructs_parent_id(self):
        """search() sets parent_id to None when stored as empty string."""
        _, _, mock_collection = self._make_mock_chromadb()
        mock_collection.query.return_value = {
            "ids": [["c1", "c2"]],
            "distances": [[0.1, 0.2]],
            "documents": [["a", "b"]],
            "metadatas": [[
                {"_document_id": "", "_start_index": 0, "_end_index": 0, "_parent_id": ""},
                {"_document_id": "", "_start_index": 0, "_end_index": 0, "_parent_id": "p1"},
            ]],
        }
        store = self._make_store(mock_collection)

        results = await store.search([0.1], limit=2)
        assert results[0].chunk.parent_id is None
        assert results[1].chunk.parent_id == "p1"

    async def test_delete(self):
        """delete() calls collection.delete and returns count."""
        _, _, mock_collection = self._make_mock_chromadb()
        store = self._make_store(mock_collection)

        deleted = await store.delete(["c1", "c2"])

        assert deleted == 2
        mock_collection.delete.assert_called_once_with(ids=["c1", "c2"])

    async def test_clear_recreates_collection(self):
        """clear() deletes collection and recreates it."""
        from agentchord.rag.vectorstore.chroma import ChromaVectorStore

        mock_module, mock_client, mock_collection = self._make_mock_chromadb()

        store = ChromaVectorStore(collection_name="test-col")
        store._client = mock_client
        store._collection = mock_collection

        await store.clear()

        mock_client.delete_collection.assert_called_once_with("test-col")
        assert store._collection is not None  # Recreated via _get_collection()

    async def test_count(self):
        """count() returns collection.count() value."""
        _, _, mock_collection = self._make_mock_chromadb()
        mock_collection.count.return_value = 42
        store = self._make_store(mock_collection)

        result = await store.count()
        assert result == 42

    async def test_get_existing_chunk(self):
        """get() retrieves a chunk by ID with metadata correctly parsed."""
        _, _, mock_collection = self._make_mock_chromadb()
        mock_collection.get.return_value = {
            "ids": ["c1"],
            "documents": ["hello world"],
            "metadatas": [{
                "_document_id": "doc1",
                "_start_index": 0,
                "_end_index": 11,
                "_parent_id": "parent1",
                "topic": "greeting",
            }],
        }
        store = self._make_store(mock_collection)

        chunk = await store.get("c1")

        assert chunk is not None
        assert chunk.id == "c1"
        assert chunk.content == "hello world"
        assert chunk.document_id == "doc1"
        assert chunk.start_index == 0
        assert chunk.end_index == 11
        assert chunk.parent_id == "parent1"
        assert chunk.metadata == {"topic": "greeting"}
        assert "_document_id" not in chunk.metadata

    async def test_get_nonexistent_returns_none(self):
        """get() returns None when chunk ID not found."""
        _, _, mock_collection = self._make_mock_chromadb()
        mock_collection.get.return_value = {
            "ids": [],
            "documents": [],
            "metadatas": [],
        }
        store = self._make_store(mock_collection)

        chunk = await store.get("nonexistent")
        assert chunk is None

    async def test_import_error_when_chromadb_not_installed(self):
        """ImportError raised with helpful message when chromadb missing."""
        from agentchord.rag.vectorstore.chroma import ChromaVectorStore

        store = ChromaVectorStore()
        store._collection = None
        store._client = None

        with patch.dict(sys.modules, {"chromadb": None}):
            with pytest.raises(ImportError, match="chromadb is required"):
                store._get_collection()

    async def test_ephemeral_client_used_without_persist_directory(self):
        """Without persist_directory, chromadb.Client() is used."""
        mock_module, mock_client, mock_collection = self._make_mock_chromadb()

        with patch.dict(sys.modules, {"chromadb": mock_module}):
            from agentchord.rag.vectorstore.chroma import ChromaVectorStore

            store = ChromaVectorStore(collection_name="test")
            store._collection = None
            store._client = None
            store._get_collection()

            mock_module.Client.assert_called_once()
            mock_module.PersistentClient.assert_not_called()

    async def test_persistent_client_used_with_persist_directory(self):
        """With persist_directory, chromadb.PersistentClient() is used."""
        mock_module, mock_client, mock_collection = self._make_mock_chromadb()

        with patch.dict(sys.modules, {"chromadb": mock_module}):
            from agentchord.rag.vectorstore.chroma import ChromaVectorStore

            store = ChromaVectorStore(
                collection_name="test", persist_directory="/tmp/chroma"
            )
            store._collection = None
            store._client = None
            store._get_collection()

            mock_module.PersistentClient.assert_called_once_with(path="/tmp/chroma")
            mock_module.Client.assert_not_called()


# ---------------------------------------------------------------------------
# WebLoader - regex fallback path (complement to existing tests)
# ---------------------------------------------------------------------------


class TestWebLoaderRegexFallback:
    """Test WebLoader._extract_text regex fallback when bs4 is not available.

    Existing tests in test_rag_web_loader.py test bs4 path.
    This class tests the regex-based fallback specifically.
    """

    def test_regex_fallback_extracts_text(self):
        """When bs4 is unavailable, regex extracts text from HTML."""
        from agentchord.rag.loaders.web import WebLoader

        html = "<html><body><p>Hello</p><div>World</div></body></html>"

        with patch.dict(sys.modules, {"bs4": None}):
            text = WebLoader._extract_text(html)

        assert "Hello" in text
        assert "World" in text
        assert "<p>" not in text

    def test_regex_fallback_removes_script_tags(self):
        """Regex fallback strips script blocks entirely."""
        from agentchord.rag.loaders.web import WebLoader

        html = (
            "<html><head><script>alert('xss');</script></head>"
            "<body><p>Safe content</p></body></html>"
        )

        with patch.dict(sys.modules, {"bs4": None}):
            text = WebLoader._extract_text(html)

        assert "alert" not in text
        assert "Safe content" in text

    def test_regex_fallback_removes_style_tags(self):
        """Regex fallback strips style blocks entirely."""
        from agentchord.rag.loaders.web import WebLoader

        html = (
            "<html><head><style>.red { color: red; }</style></head>"
            "<body><p>Styled content</p></body></html>"
        )

        with patch.dict(sys.modules, {"bs4": None}):
            text = WebLoader._extract_text(html)

        assert "color: red" not in text
        assert "Styled content" in text

    def test_regex_fallback_normalizes_whitespace(self):
        """Regex fallback collapses multiple whitespace to single space."""
        from agentchord.rag.loaders.web import WebLoader

        html = "<html><body><p>Word1</p>   <p>Word2</p>\n\n<p>Word3</p></body></html>"

        with patch.dict(sys.modules, {"bs4": None}):
            text = WebLoader._extract_text(html)

        assert "  " not in text
        assert "Word1" in text
        assert "Word2" in text
        assert "Word3" in text
