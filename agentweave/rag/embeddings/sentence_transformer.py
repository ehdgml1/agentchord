"""Sentence-transformers local embedding provider."""
from __future__ import annotations

import asyncio
from typing import Any

from agentweave.rag.embeddings.base import EmbeddingProvider

_MODEL_DIMENSIONS: dict[str, int] = {
    "all-MiniLM-L6-v2": 384,
    "all-mpnet-base-v2": 768,
    "BAAI/bge-m3": 1024,
    "BAAI/bge-small-en-v1.5": 384,
    "BAAI/bge-base-en-v1.5": 768,
}


class SentenceTransformerEmbeddings(EmbeddingProvider):
    """Local embedding via sentence-transformers.

    Requires: pip install sentence-transformers
    Runs entirely locally with no API calls.
    """

    def __init__(
        self,
        model: str = "all-MiniLM-L6-v2",
        device: str = "cpu",
    ) -> None:
        self._model_name_str = model
        self._device = device
        self._dimensions = _MODEL_DIMENSIONS.get(model, 384)
        self._model: Any = None

    def _get_model(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as e:
                raise ImportError(
                    "sentence-transformers is required. "
                    "Install with: pip install sentence-transformers"
                ) from e
            self._model = SentenceTransformer(
                self._model_name_str, device=self._device
            )
        return self._model

    @property
    def model_name(self) -> str:
        return self._model_name_str

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, text: str) -> list[float]:
        model = self._get_model()
        embedding = await asyncio.to_thread(
            model.encode, [text], normalize_embeddings=True
        )
        return embedding[0].tolist()

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._get_model()
        embeddings = await asyncio.to_thread(
            model.encode, texts, normalize_embeddings=True
        )
        return [e.tolist() for e in embeddings]
