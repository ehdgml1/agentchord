"""Tests for PDF document loader."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agentweave.rag.loaders.pdf import PDFLoader


def _make_mock_page(text: str) -> MagicMock:
    """Create a mock pypdf page with extract_text."""
    page = MagicMock()
    page.extract_text.return_value = text
    return page


def _make_mock_reader(pages_text: list[str]) -> MagicMock:
    """Create a mock pypdf PdfReader with pages."""
    reader = MagicMock()
    reader.pages = [_make_mock_page(t) for t in pages_text]
    return reader


class TestPDFLoader:
    """Test PDFLoader with mocked pypdf."""

    async def test_pypdf_import_error(self):
        """Test that missing pypdf raises ImportError with install message."""
        with patch.object(PDFLoader, "_get_reader") as mock_get_reader:
            mock_get_reader.side_effect = ImportError(
                "pypdf is required for PDFLoader. Install with: pip install pypdf"
            )
            with patch.object(Path, "is_file", return_value=True):
                loader = PDFLoader("test.pdf")
                with pytest.raises(ImportError, match="pypdf is required"):
                    await loader.load()

    async def test_file_not_found(self):
        """Test that missing file raises FileNotFoundError."""
        loader = PDFLoader("/nonexistent/file.pdf")
        with pytest.raises(FileNotFoundError, match="File not found"):
            await loader.load()

    async def test_per_page_true_default(self):
        """Test per_page=True creates one document per page with page_number metadata."""
        mock_reader = _make_mock_reader(["Page 1 text", "Page 2 text", "Page 3 text"])

        with patch.object(PDFLoader, "_get_reader", return_value=mock_reader):
            with patch.object(Path, "is_file", return_value=True):
                loader = PDFLoader("test.pdf")
                docs = await loader.load()

        assert len(docs) == 3
        assert docs[0].content == "Page 1 text"
        assert docs[0].metadata["page_number"] == 1
        assert docs[0].metadata["total_pages"] == 3
        assert docs[0].metadata["file_name"] == "test.pdf"
        assert docs[0].metadata["file_type"] == ".pdf"
        assert docs[0].source == "test.pdf"

        assert docs[1].content == "Page 2 text"
        assert docs[1].metadata["page_number"] == 2

        assert docs[2].content == "Page 3 text"
        assert docs[2].metadata["page_number"] == 3

    async def test_per_page_false(self):
        """Test per_page=False combines all pages into one document."""
        mock_reader = _make_mock_reader(["First page", "Second page", "Third page"])

        with patch.object(PDFLoader, "_get_reader", return_value=mock_reader):
            with patch.object(Path, "is_file", return_value=True):
                loader = PDFLoader("combined.pdf", per_page=False)
                docs = await loader.load()

        assert len(docs) == 1
        assert docs[0].content == "First page\n\nSecond page\n\nThird page"
        assert "page_number" not in docs[0].metadata
        assert docs[0].metadata["total_pages"] == 3
        assert docs[0].metadata["file_name"] == "combined.pdf"
        assert docs[0].source == "combined.pdf"

    async def test_skip_empty_pages(self):
        """Test that pages with empty or whitespace-only text are skipped."""
        mock_reader = _make_mock_reader([
            "First page",
            "",  # empty
            "   \n\t  ",  # whitespace only
            "Last page"
        ])

        with patch.object(PDFLoader, "_get_reader", return_value=mock_reader):
            with patch.object(Path, "is_file", return_value=True):
                loader = PDFLoader("sparse.pdf")
                docs = await loader.load()

        assert len(docs) == 2
        assert docs[0].content == "First page"
        assert docs[0].metadata["page_number"] == 1
        assert docs[1].content == "Last page"
        assert docs[1].metadata["page_number"] == 4

    async def test_metadata_fields(self):
        """Test that all expected metadata fields are present."""
        mock_reader = _make_mock_reader(["Content"])

        with patch.object(PDFLoader, "_get_reader", return_value=mock_reader):
            with patch.object(Path, "is_file", return_value=True):
                loader = PDFLoader(Path("/path/to/document.pdf"))
                docs = await loader.load()

        assert len(docs) == 1
        metadata = docs[0].metadata
        assert metadata["file_name"] == "document.pdf"
        assert metadata["file_type"] == ".pdf"
        assert metadata["page_number"] == 1
        assert metadata["total_pages"] == 1

    async def test_source_is_file_path_string(self):
        """Test that source field is the string representation of file path."""
        mock_reader = _make_mock_reader(["Data"])

        with patch.object(PDFLoader, "_get_reader", return_value=mock_reader):
            with patch.object(Path, "is_file", return_value=True):
                loader = PDFLoader(Path("/absolute/path/report.pdf"))
                docs = await loader.load()

        assert docs[0].source == str(Path("/absolute/path/report.pdf"))

    async def test_all_pages_empty(self):
        """Test that PDF with all empty pages returns empty list."""
        mock_reader = _make_mock_reader(["", "   ", "\n\n"])

        with patch.object(PDFLoader, "_get_reader", return_value=mock_reader):
            with patch.object(Path, "is_file", return_value=True):
                loader = PDFLoader("empty.pdf")
                docs = await loader.load()

        assert len(docs) == 0

    async def test_all_pages_empty_per_page_false(self):
        """Test that PDF with all empty pages returns empty list when per_page=False."""
        mock_reader = _make_mock_reader(["", "   ", "\n\n"])

        with patch.object(PDFLoader, "_get_reader", return_value=mock_reader):
            with patch.object(Path, "is_file", return_value=True):
                loader = PDFLoader("empty.pdf", per_page=False)
                docs = await loader.load()

        assert len(docs) == 0

    async def test_extract_text_returns_none(self):
        """Test handling when extract_text returns None."""
        # Some pypdf versions may return None instead of empty string
        mock_reader = _make_mock_reader(["Valid text"])
        mock_reader.pages[0].extract_text.return_value = None

        with patch.object(PDFLoader, "_get_reader", return_value=mock_reader):
            with patch.object(Path, "is_file", return_value=True):
                loader = PDFLoader("test.pdf")
                docs = await loader.load()

        # Should skip the page with None
        assert len(docs) == 0

    async def test_accepts_string_path(self):
        """Test that PDFLoader accepts string path."""
        mock_reader = _make_mock_reader(["Content"])

        with patch.object(PDFLoader, "_get_reader", return_value=mock_reader):
            with patch.object(Path, "is_file", return_value=True):
                loader = PDFLoader("/path/as/string.pdf")
                docs = await loader.load()

        assert len(docs) == 1
        assert docs[0].metadata["file_name"] == "string.pdf"

    async def test_get_reader_imports_pypdf(self):
        """Test that _get_reader imports and uses pypdf.PdfReader."""
        # PdfReader is imported inside _get_reader, so we need to patch pypdf.PdfReader
        with patch("pypdf.PdfReader") as mock_pdf_reader_class:
            loader = PDFLoader("test.pdf")
            # Call the actual _get_reader method
            loader._get_reader()

            # Verify PdfReader was called with file path
            mock_pdf_reader_class.assert_called_once_with("test.pdf")
