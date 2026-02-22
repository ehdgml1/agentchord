"""Document loader interface."""
from __future__ import annotations

from abc import ABC, abstractmethod

from agentchord.rag.types import Document


class DocumentLoader(ABC):
    """Abstract base for document loaders.

    Each loader is responsible for reading documents from
    a specific source type (files, URLs, databases, etc.).
    """

    @abstractmethod
    async def load(self) -> list[Document]:
        """Load documents from the configured source.

        Returns:
            List of loaded documents with metadata.
        """
