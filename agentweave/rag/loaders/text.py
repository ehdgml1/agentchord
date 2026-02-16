"""Text file document loaders."""
from __future__ import annotations

from pathlib import Path

from agentweave.rag.loaders.base import DocumentLoader
from agentweave.rag.types import Document


class TextLoader(DocumentLoader):
    """Load a single text file as a Document.

    Example:
        loader = TextLoader("data/readme.txt")
        docs = await loader.load()
    """

    def __init__(
        self,
        file_path: str | Path,
        encoding: str = "utf-8",
    ) -> None:
        self._path = Path(file_path)
        self._encoding = encoding

    async def load(self) -> list[Document]:
        if not self._path.is_file():
            raise FileNotFoundError(f"File not found: {self._path}")

        content = self._path.read_text(encoding=self._encoding)
        return [
            Document(
                content=content,
                source=str(self._path),
                metadata={
                    "file_name": self._path.name,
                    "file_type": self._path.suffix,
                    "file_size": self._path.stat().st_size,
                },
            )
        ]
