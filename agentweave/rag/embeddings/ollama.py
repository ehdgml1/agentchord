"""Ollama local embedding provider."""
from __future__ import annotations

import asyncio
from typing import Any

import httpx

from agentweave.rag.embeddings.base import EmbeddingProvider


class OllamaEmbeddings(EmbeddingProvider):
    """Ollama local embedding provider using httpx.

    Uses the /api/embeddings endpoint for local embedding models.
    No API key required.
    """

    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
        dimensions: int = 768,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._dimensions = dimensions

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, text: str) -> list[float]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/api/embeddings",
                json={"model": self._model, "prompt": text},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        sem = asyncio.Semaphore(10)

        async def _embed_one(client: httpx.AsyncClient, text: str) -> list[float]:
            async with sem:
                response = await client.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": self._model, "prompt": text},
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()["embedding"]

        async with httpx.AsyncClient() as client:
            return list(await asyncio.gather(
                *[_embed_one(client, text) for text in texts]
            ))
