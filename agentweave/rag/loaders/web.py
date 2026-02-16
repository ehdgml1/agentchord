"""Web page document loader."""
from __future__ import annotations

import re
from typing import Any

from agentweave.rag.loaders.base import DocumentLoader
from agentweave.rag.types import Document


class WebLoader(DocumentLoader):
    """Load web pages as Documents.

    Uses httpx (core dependency) for HTTP requests.
    Strips HTML tags to extract plain text.

    Example:
        loader = WebLoader(["https://example.com"])
        docs = await loader.load()
    """

    def __init__(
        self,
        urls: list[str],
        *,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._urls = urls
        self._timeout = timeout
        self._headers = headers or {
            "User-Agent": "AgentWeave-WebLoader/0.1",
        }

    async def load(self) -> list[Document]:
        import httpx

        documents: list[Document] = []

        async with httpx.AsyncClient(
            timeout=self._timeout,
            headers=self._headers,
            follow_redirects=True,
        ) as client:
            for url in self._urls:
                response = await client.get(url)
                response.raise_for_status()

                text = self._extract_text(response.text)
                if not text.strip():
                    continue

                documents.append(
                    Document(
                        content=text,
                        source=url,
                        metadata={
                            "url": url,
                            "status_code": response.status_code,
                            "content_type": response.headers.get("content-type", ""),
                        },
                    )
                )

        return documents

    @staticmethod
    def _extract_text(html: str) -> str:
        """Extract readable text from HTML.

        Uses beautifulsoup4 when available for robust parsing,
        falls back to regex-based extraction otherwise.
        """
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style"]):
                tag.decompose()
            text = soup.get_text(separator=" ")
            return re.sub(r"\s+", " ", text).strip()
        except ImportError:
            pass

        # Regex fallback
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()
