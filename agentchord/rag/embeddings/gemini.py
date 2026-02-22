"""Gemini embedding provider."""
from __future__ import annotations

import httpx

from agentchord.rag.embeddings.base import EmbeddingProvider

_DIMENSIONS: dict[str, int] = {
    "gemini-embedding-001": 3072,
}


class GeminiEmbeddings(EmbeddingProvider):
    """Gemini text-embedding provider using httpx.

    Uses the Google Generative AI embedContent API.
    Requires a Gemini API key (get from https://makersuite.google.com/app/apikey).
    """

    def __init__(
        self,
        model: str = "gemini-embedding-001",
        api_key: str | None = None,
        dimensions: int | None = None,
    ) -> None:
        self._model = model
        self._api_key = api_key
        self._dimensions = dimensions or _DIMENSIONS.get(model, 3072)

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, text: str) -> list[float]:
        if not self._api_key:
            raise ValueError("api_key is required for GeminiEmbeddings")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:embedContent",
                params={"key": self._api_key},
                json={
                    "model": f"models/{self._model}",
                    "content": {"parts": [{"text": text}]},
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["embedding"]["values"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self._api_key:
            raise ValueError("api_key is required for GeminiEmbeddings")

        all_embeddings: list[list[float]] = []
        batch_size = 100

        async with httpx.AsyncClient() as client:
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                requests = [
                    {
                        "model": f"models/{self._model}",
                        "content": {"parts": [{"text": text}]},
                    }
                    for text in batch
                ]
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:batchEmbedContents",
                    params={"key": self._api_key},
                    json={"requests": requests},
                    timeout=60.0,
                )
                response.raise_for_status()
                data = response.json()
                all_embeddings.extend(
                    [embedding["values"] for embedding in data["embeddings"]]
                )

        return all_embeddings
