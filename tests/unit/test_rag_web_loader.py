"""Tests for RAG web loader."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from agentchord.rag.loaders.web import WebLoader
from agentchord.rag.types import Document


class TestWebLoader:
    """Test suite for WebLoader."""

    @pytest.fixture
    def mock_response(self) -> MagicMock:
        """Create a mock HTTP response."""
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.text = "<html><body><p>Hello World</p></body></html>"
        resp.headers = {"content-type": "text/html"}
        resp.raise_for_status = MagicMock()
        return resp

    async def test_basic_load(self, mock_response):
        """Test basic HTML page loading with text extraction."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            loader = WebLoader(["https://example.com"])
            docs = await loader.load()

            assert len(docs) == 1
            assert docs[0].content == "Hello World"
            assert docs[0].source == "https://example.com"
            assert "<p>" not in docs[0].content
            assert "<html>" not in docs[0].content

    async def test_multiple_urls(self):
        """Test loading multiple URLs returns multiple documents."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()

            # Create two different responses
            resp1 = MagicMock(spec=httpx.Response)
            resp1.status_code = 200
            resp1.text = "<html><body><p>Page One</p></body></html>"
            resp1.headers = {"content-type": "text/html"}
            resp1.raise_for_status = MagicMock()

            resp2 = MagicMock(spec=httpx.Response)
            resp2.status_code = 200
            resp2.text = "<html><body><p>Page Two</p></body></html>"
            resp2.headers = {"content-type": "text/html"}
            resp2.raise_for_status = MagicMock()

            mock_client.get = AsyncMock(side_effect=[resp1, resp2])
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            loader = WebLoader(["https://example.com/1", "https://example.com/2"])
            docs = await loader.load()

            assert len(docs) == 2
            assert docs[0].content == "Page One"
            assert docs[1].content == "Page Two"
            assert docs[0].source == "https://example.com/1"
            assert docs[1].source == "https://example.com/2"

    async def test_empty_html_skipped(self):
        """Test that URLs with empty body are skipped."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()

            # Empty response
            empty_resp = MagicMock(spec=httpx.Response)
            empty_resp.status_code = 200
            empty_resp.text = "<html><body></body></html>"
            empty_resp.headers = {"content-type": "text/html"}
            empty_resp.raise_for_status = MagicMock()

            # Valid response
            valid_resp = MagicMock(spec=httpx.Response)
            valid_resp.status_code = 200
            valid_resp.text = "<html><body><p>Valid content</p></body></html>"
            valid_resp.headers = {"content-type": "text/html"}
            valid_resp.raise_for_status = MagicMock()

            mock_client.get = AsyncMock(side_effect=[empty_resp, valid_resp])
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            loader = WebLoader(["https://example.com/empty", "https://example.com/valid"])
            docs = await loader.load()

            # Only the valid URL should return a document
            assert len(docs) == 1
            assert docs[0].content == "Valid content"

    async def test_html_tags_removed(self):
        """Test that HTML tags are properly stripped from content."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()

            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.text = (
                "<html><head><title>Test</title></head>"
                "<body><h1>Heading</h1><p>Paragraph</p><div>Division</div></body></html>"
            )
            resp.headers = {"content-type": "text/html"}
            resp.raise_for_status = MagicMock()

            mock_client.get = AsyncMock(return_value=resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            loader = WebLoader(["https://example.com"])
            docs = await loader.load()

            assert len(docs) == 1
            content = docs[0].content
            assert "<h1>" not in content
            assert "<p>" not in content
            assert "<div>" not in content
            assert "Heading" in content
            assert "Paragraph" in content
            assert "Division" in content

    async def test_script_style_removed(self):
        """Test that script and style blocks are removed from content."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()

            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.text = (
                "<html><head>"
                "<script>var x = 'should not appear';</script>"
                "<style>body { color: red; }</style>"
                "</head><body><p>Visible text</p></body></html>"
            )
            resp.headers = {"content-type": "text/html"}
            resp.raise_for_status = MagicMock()

            mock_client.get = AsyncMock(return_value=resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            loader = WebLoader(["https://example.com"])
            docs = await loader.load()

            assert len(docs) == 1
            content = docs[0].content
            assert "should not appear" not in content
            assert "color: red" not in content
            assert "Visible text" in content

    async def test_metadata_included(self, mock_response):
        """Test that url, status_code, and content_type are in metadata."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            loader = WebLoader(["https://example.com"])
            docs = await loader.load()

            assert len(docs) == 1
            metadata = docs[0].metadata
            assert metadata["url"] == "https://example.com"
            assert metadata["status_code"] == 200
            assert metadata["content_type"] == "text/html"

    async def test_custom_headers(self):
        """Test that custom headers override defaults."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()

            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.text = "<html><body><p>Content</p></body></html>"
            resp.headers = {"content-type": "text/html"}
            resp.raise_for_status = MagicMock()

            mock_client.get = AsyncMock(return_value=resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            custom_headers = {"User-Agent": "CustomBot/1.0"}
            loader = WebLoader(["https://example.com"], headers=custom_headers)
            await loader.load()

            # Verify AsyncClient was created with custom headers
            MockClient.assert_called_once()
            call_kwargs = MockClient.call_args.kwargs
            assert call_kwargs["headers"] == custom_headers

    async def test_http_error_raised(self):
        """Test that HTTP errors are raised when status is 404."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()

            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 404
            resp.text = "<html><body>Not Found</body></html>"
            resp.headers = {"content-type": "text/html"}
            resp.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError(
                "404 Not Found",
                request=MagicMock(),
                response=resp,
            ))

            mock_client.get = AsyncMock(return_value=resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            loader = WebLoader(["https://example.com/notfound"])
            with pytest.raises(httpx.HTTPStatusError):
                await loader.load()

    def test_extract_text_static_method(self):
        """Test _extract_text static method directly."""
        html = (
            "<html><head><script>alert('test');</script></head>"
            "<body><p>Hello</p><div>World</div></body></html>"
        )
        text = WebLoader._extract_text(html)

        assert "Hello" in text
        assert "World" in text
        assert "alert" not in text
        assert "<p>" not in text
        assert "<div>" not in text

    def test_whitespace_normalization(self):
        """Test that multiple whitespaces are normalized to single space."""
        html = (
            "<html><body>"
            "<p>Multiple   spaces</p>"
            "<p>Newline\n\nchars</p>"
            "<p>Tab\t\tcharacters</p>"
            "</body></html>"
        )
        text = WebLoader._extract_text(html)

        # Should normalize all whitespace to single spaces
        assert "Multiple spaces" in text
        assert "Newline chars" in text
        assert "Tab characters" in text
        # Should not contain multiple consecutive spaces
        assert "  " not in text
        assert "\n" not in text
        assert "\t" not in text
