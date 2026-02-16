"""Recursive character text splitter."""
from __future__ import annotations

from collections.abc import Callable

from agentweave.rag.chunking.base import Chunker
from agentweave.rag.types import Chunk, Document

_DEFAULT_SEPARATORS: list[str] = ["\n\n", "\n", ". ", " ", ""]


class RecursiveCharacterChunker(Chunker):
    """Split text recursively using hierarchical separators.

    Tries paragraph breaks first, then sentences, then words.
    Industry standard for general-purpose text chunking.

    Recommended settings:
        General text: chunk_size=500, chunk_overlap=50
        Code: chunk_size=1000, chunk_overlap=100
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: list[str] | None = None,
        length_function: Callable[[str], int] = len,
    ) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._separators = separators or list(_DEFAULT_SEPARATORS)
        self._length_function = length_function

    def chunk(self, document: Document) -> list[Chunk]:
        text = document.content
        if not text.strip():
            return []

        raw_chunks = self._split_text(text, self._separators)
        merged = self._merge_with_overlap(raw_chunks)

        chunks: list[Chunk] = []
        offset = 0
        for content in merged:
            start = text.find(content, max(0, offset - self._chunk_overlap))
            if start == -1:
                # Overlap-merged content may not exist verbatim; use last known offset
                start = offset
            end = start + len(content)
            chunks.append(
                Chunk(
                    content=content,
                    document_id=document.id,
                    metadata={**document.metadata, "source": document.source},
                    start_index=start,
                    end_index=end,
                )
            )
            offset = start + len(content) - self._chunk_overlap

        return chunks

    def _split_text(self, text: str, separators: list[str]) -> list[str]:
        if not separators:
            return [text[i:i + self._chunk_size]
                    for i in range(0, len(text), self._chunk_size)]

        separator = separators[0]
        remaining = separators[1:]

        if separator == "":
            splits = list(text)
        else:
            splits = text.split(separator)

        result: list[str] = []
        for split in splits:
            piece = split.strip()
            if not piece:
                continue
            if self._length_function(piece) <= self._chunk_size:
                result.append(piece)
            elif remaining:
                result.extend(self._split_text(piece, remaining))
            else:
                for i in range(0, len(piece), self._chunk_size):
                    result.append(piece[i:i + self._chunk_size])

        return result

    def _merge_with_overlap(self, pieces: list[str]) -> list[str]:
        if not pieces:
            return []

        merged: list[str] = []
        current = pieces[0]

        for piece in pieces[1:]:
            combined = current + " " + piece
            if self._length_function(combined) <= self._chunk_size:
                current = combined
            else:
                merged.append(current)
                if self._chunk_overlap > 0 and len(current) > self._chunk_overlap:
                    overlap_text = current[-self._chunk_overlap:]
                    current = overlap_text + " " + piece
                    if self._length_function(current) > self._chunk_size:
                        current = piece
                else:
                    current = piece

        if current:
            merged.append(current)

        return merged
