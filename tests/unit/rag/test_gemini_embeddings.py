"""Tests for GeminiEmbeddings provider.

Tests the Gemini embedding provider implementation using mocked httpx.AsyncClient
to avoid requiring actual API credentials or network calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from agentchord.rag.embeddings.gemini import GeminiEmbeddings


class TestGeminiEmbeddings:
    """Tests for GeminiEmbeddings with mocked httpx.AsyncClient."""

    def _mock_response(self, values: list[float]) -> MagicMock:
        """Create a mock httpx response with embedding data."""
        resp = MagicMock()
        resp.json.return_value = {"embedding": {"values": values}}
        resp.raise_for_status = MagicMock()
        return resp

    def _mock_batch_response(self, embeddings: list[list[float]]) -> MagicMock:
        """Create a mock httpx response for batch embedContent."""
        resp = MagicMock()
        resp.json.return_value = {
            "embeddings": [{"values": emb} for emb in embeddings]
        }
        resp.raise_for_status = MagicMock()
        return resp

    async def test_constructor_with_defaults(self):
        """Constructor uses default model and dimensions."""
        provider = GeminiEmbeddings(api_key="test-key")

        assert provider.model_name == "gemini-embedding-001"
        assert provider.dimensions == 3072
        assert provider._api_key == "test-key"

    async def test_constructor_with_custom_parameters(self):
        """Constructor accepts custom model, api_key, and dimensions."""
        provider = GeminiEmbeddings(
            model="gemini-embedding-001", api_key="custom-key", dimensions=1024
        )

        assert provider.model_name == "gemini-embedding-001"
        assert provider.dimensions == 1024
        assert provider._api_key == "custom-key"

    async def test_embed_single_text(self):
        """embed() sends POST to embedContent endpoint with correct payload."""
        expected = [0.1, 0.2, 0.3]

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=self._mock_response(expected))
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            provider = GeminiEmbeddings(
                model="gemini-embedding-001", api_key="test-key"
            )
            result = await provider.embed("hello world")

        assert result == expected
        mock_client.post.assert_awaited_once()
        call_args = mock_client.post.call_args
        assert (
            call_args[0][0]
            == "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent"
        )
        assert call_args.kwargs["params"] == {"key": "test-key"}
        assert call_args.kwargs["json"] == {
            "model": "models/gemini-embedding-001",
            "content": {"parts": [{"text": "hello world"}]},
        }
        assert call_args.kwargs["timeout"] == 30.0

    async def test_embed_with_different_model(self):
        """embed() uses custom model name in URL and request body."""
        expected = [0.5, 0.6]

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=self._mock_response(expected))
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            provider = GeminiEmbeddings(model="gemini-embedding-001", api_key="test-key")
            result = await provider.embed("test text")

        assert result == expected
        call_url = mock_client.post.call_args[0][0]
        assert "gemini-embedding-001:embedContent" in call_url
        call_json = mock_client.post.call_args.kwargs["json"]
        assert call_json["model"] == "models/gemini-embedding-001"

    async def test_embed_batch_single_item(self):
        """embed_batch() with single item uses batchEmbedContents endpoint."""
        expected = [[0.1, 0.2, 0.3]]

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(
                return_value=self._mock_batch_response(expected)
            )
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            provider = GeminiEmbeddings(api_key="test-key")
            result = await provider.embed_batch(["single text"])

        assert result == expected
        mock_client.post.assert_awaited_once()

    async def test_embed_batch_multiple_items(self):
        """embed_batch() sends multiple texts to batchEmbedContents endpoint."""
        embeddings = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(
                return_value=self._mock_batch_response(embeddings)
            )
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            provider = GeminiEmbeddings(api_key="test-key")
            result = await provider.embed_batch(["text a", "text b", "text c"])

        assert result == embeddings
        mock_client.post.assert_awaited_once()
        call_args = mock_client.post.call_args
        assert "batchEmbedContents" in call_args[0][0]
        call_json = call_args.kwargs["json"]
        assert len(call_json["requests"]) == 3
        assert call_json["requests"][0]["content"]["parts"][0]["text"] == "text a"
        assert call_json["requests"][1]["content"]["parts"][0]["text"] == "text b"
        assert call_json["requests"][2]["content"]["parts"][0]["text"] == "text c"

    async def test_embed_batch_large_batch_splits_into_100_chunks(self):
        """embed_batch() splits batches larger than 100 items into multiple requests."""
        total_texts = 250
        texts = [f"text_{i}" for i in range(total_texts)]
        single_emb = [0.1, 0.2]

        call_count = 0
        batch_sizes = []

        async def mock_post(url: str, **kwargs) -> MagicMock:
            nonlocal call_count
            call_count += 1
            n = len(kwargs["json"]["requests"])
            batch_sizes.append(n)
            return self._mock_batch_response([single_emb] * n)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=mock_post)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            provider = GeminiEmbeddings(api_key="test-key")
            result = await provider.embed_batch(texts)

        assert len(result) == total_texts
        # 250 texts / 100 batch_size = 3 batches (100 + 100 + 50)
        assert call_count == 3
        assert batch_sizes == [100, 100, 50]

    async def test_embed_error_handling_non_200(self):
        """embed() propagates HTTP errors when API returns non-200."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            error_resp = MagicMock()
            error_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "400 Bad Request", request=MagicMock(), response=error_resp
            )
            mock_client.post = AsyncMock(return_value=error_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            provider = GeminiEmbeddings(api_key="test-key")
            with pytest.raises(httpx.HTTPStatusError):
                await provider.embed("test")

    async def test_embed_error_handling_network_error(self):
        """embed() propagates network errors from httpx."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection failed")
            )
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            provider = GeminiEmbeddings(api_key="test-key")
            with pytest.raises(httpx.ConnectError):
                await provider.embed("test")

    async def test_embed_batch_error_handling(self):
        """embed_batch() propagates HTTP errors from API."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            error_resp = MagicMock()
            error_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "500 Internal Server Error", request=MagicMock(), response=error_resp
            )
            mock_client.post = AsyncMock(return_value=error_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            provider = GeminiEmbeddings(api_key="test-key")
            with pytest.raises(httpx.HTTPStatusError):
                await provider.embed_batch(["text1", "text2"])

    async def test_embed_url_construction_with_model_name(self):
        """embed() constructs correct URL with model name."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(
                return_value=self._mock_response([0.1, 0.2])
            )
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            provider = GeminiEmbeddings(model="custom-model-v2", api_key="test-key")
            await provider.embed("test")

        call_url = mock_client.post.call_args[0][0]
        assert call_url.startswith(
            "https://generativelanguage.googleapis.com/v1beta/models/"
        )
        assert "custom-model-v2:embedContent" in call_url

    async def test_embed_api_key_in_url_params(self):
        """embed() includes API key in query parameters."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(
                return_value=self._mock_response([0.1, 0.2])
            )
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            provider = GeminiEmbeddings(api_key="my-secret-key-123")
            await provider.embed("test")

        call_params = mock_client.post.call_args.kwargs["params"]
        assert call_params == {"key": "my-secret-key-123"}

    async def test_embed_batch_request_body_format(self):
        """embed_batch() sends requests array with correct structure."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(
                return_value=self._mock_batch_response([[0.1], [0.2]])
            )
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            provider = GeminiEmbeddings(model="test-model", api_key="test-key")
            await provider.embed_batch(["text1", "text2"])

        call_json = mock_client.post.call_args.kwargs["json"]
        assert "requests" in call_json
        assert len(call_json["requests"]) == 2
        assert call_json["requests"][0] == {
            "model": "models/test-model",
            "content": {"parts": [{"text": "text1"}]},
        }
        assert call_json["requests"][1] == {
            "model": "models/test-model",
            "content": {"parts": [{"text": "text2"}]},
        }

    async def test_dimensions_property_returns_correct_value(self):
        """dimensions property returns configured dimension size."""
        # Default dimension for gemini-embedding-001
        p1 = GeminiEmbeddings(model="gemini-embedding-001")
        assert p1.dimensions == 3072

        # Custom override
        p2 = GeminiEmbeddings(model="gemini-embedding-001", dimensions=512)
        assert p2.dimensions == 512

        # Unknown model fallback to 3072
        p3 = GeminiEmbeddings(model="unknown-model")
        assert p3.dimensions == 3072

    async def test_model_name_property_returns_correct_value(self):
        """model_name property returns configured model string."""
        p1 = GeminiEmbeddings(model="gemini-embedding-001")
        assert p1.model_name == "gemini-embedding-001"

        p2 = GeminiEmbeddings(model="custom-model")
        assert p2.model_name == "custom-model"

    async def test_embed_batch_empty_list(self):
        """embed_batch() with empty list returns empty without API call."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            provider = GeminiEmbeddings(api_key="test-key")
            result = await provider.embed_batch([])

        assert result == []
        mock_client.post.assert_not_awaited()

    async def test_embed_requires_api_key(self):
        """embed() raises ValueError when api_key is None."""
        provider = GeminiEmbeddings(api_key=None)

        with pytest.raises(ValueError, match="api_key is required"):
            await provider.embed("test")

    async def test_embed_batch_requires_api_key(self):
        """embed_batch() raises ValueError when api_key is None."""
        provider = GeminiEmbeddings(api_key=None)

        with pytest.raises(ValueError, match="api_key is required"):
            await provider.embed_batch(["test1", "test2"])
