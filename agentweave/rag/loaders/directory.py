"""Directory document loader.

Recursively loads text files from a directory using glob patterns.
Delegates individual file loading to TextLoader.
"""
from __future__ import annotations

import glob as _glob
from pathlib import Path

from agentweave.rag.loaders.base import DocumentLoader
from agentweave.rag.loaders.text import TextLoader
from agentweave.rag.types import Document


class DirectoryLoader(DocumentLoader):
    """Load documents from a directory matching glob patterns.

    Recursively scans directories for matching files and loads
    each as a Document using TextLoader.

    Example:
        loader = DirectoryLoader("docs/", glob="**/*.md")
        docs = await loader.load()
    """

    def __init__(
        self,
        directory: str | Path,
        *,
        glob: str = "**/*.txt",
        encoding: str = "utf-8",
    ) -> None:
        self._directory = Path(directory)
        self._glob = glob
        self._encoding = encoding

    async def load(self) -> list[Document]:
        if not self._directory.is_dir():
            raise FileNotFoundError(f"Directory not found: {self._directory}")

        documents: list[Document] = []
        pattern = str(self._directory / self._glob)
        for filepath in sorted(_glob.glob(pattern, recursive=True)):
            path = Path(filepath)
            if not path.is_file():
                continue
            loader = TextLoader(str(path), encoding=self._encoding)
            docs = await loader.load()
            documents.extend(docs)

        return documents
