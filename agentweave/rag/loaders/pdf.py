"""PDF document loader."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from agentweave.rag.loaders.base import DocumentLoader
from agentweave.rag.types import Document


class PDFLoader(DocumentLoader):
    """Load a PDF file as one or more Documents.

    Requires: pip install pypdf

    By default, each page becomes a separate document.
    Set per_page=False to combine all pages into one document.

    Example:
        loader = PDFLoader("report.pdf")
        docs = await loader.load()  # one doc per page
    """

    def __init__(
        self,
        file_path: str | Path,
        *,
        per_page: bool = True,
    ) -> None:
        self._path = Path(file_path)
        self._per_page = per_page

    def _get_reader(self) -> Any:
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise ImportError(
                "pypdf is required for PDFLoader. "
                "Install with: pip install pypdf"
            ) from e
        return PdfReader(str(self._path))

    async def load(self) -> list[Document]:
        if not self._path.is_file():
            raise FileNotFoundError(f"File not found: {self._path}")

        reader = self._get_reader()
        documents: list[Document] = []

        if self._per_page:
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if not text.strip():
                    continue
                documents.append(
                    Document(
                        content=text,
                        source=str(self._path),
                        metadata={
                            "file_name": self._path.name,
                            "file_type": ".pdf",
                            "page_number": page_num + 1,
                            "total_pages": len(reader.pages),
                        },
                    )
                )
        else:
            all_text = "\n\n".join(
                page.extract_text() or "" for page in reader.pages
            ).strip()
            if all_text:
                documents.append(
                    Document(
                        content=all_text,
                        source=str(self._path),
                        metadata={
                            "file_name": self._path.name,
                            "file_type": ".pdf",
                            "total_pages": len(reader.pages),
                        },
                    )
                )

        return documents
