"""OpenAI embedding provider."""
from __future__ import annotations

from typing import Any

from agentchord.rag.embeddings.base import EmbeddingProvider

_DIMENSIONS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


class OpenAIEmbeddings(EmbeddingProvider):
    """OpenAI text-embedding-3 provider.

    Requires: pip install openai
    Supports dimension reduction via the dimensions parameter.
    """

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: str | None = None,
        dimensions: int | None = None,
    ) -> None:
        self._model = model
        self._api_key = api_key
        self._dimensions = dimensions or _DIMENSIONS.get(model, 1536)
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as e:
                raise ImportError(
                    "openai is required for OpenAIEmbeddings. "
                    "Install with: pip install openai"
                ) from e
            kwargs: dict[str, Any] = {}
            if self._api_key:
                kwargs["api_key"] = self._api_key
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, text: str) -> list[float]:
        client = self._get_client()
        kwargs: dict[str, Any] = {"model": self._model, "input": [text]}
        if self._model.startswith("text-embedding-3"):
            kwargs["dimensions"] = self._dimensions
        response = await client.embeddings.create(**kwargs)
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        client = self._get_client()
        all_embeddings: list[list[float]] = []
        batch_size = 2048
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            kwargs: dict[str, Any] = {"model": self._model, "input": batch}
            if self._model.startswith("text-embedding-3"):
                kwargs["dimensions"] = self._dimensions
            response = await client.embeddings.create(**kwargs)
            all_embeddings.extend([item.embedding for item in response.data])
        return all_embeddings
