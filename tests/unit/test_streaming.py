"""Unit tests for Streaming functionality."""

from __future__ import annotations

import pytest

from agentweave.core.types import StreamChunk, Usage


class TestStreamChunk:
    """Tests for StreamChunk."""

    def test_chunk_creation(self) -> None:
        """Should create chunk with required fields."""
        chunk = StreamChunk(content="Hello", delta="Hello")

        assert chunk.content == "Hello"
        assert chunk.delta == "Hello"
        assert chunk.finish_reason is None
        assert chunk.usage is None

    def test_chunk_with_finish_reason(self) -> None:
        """Should accept finish reason."""
        chunk = StreamChunk(
            content="Complete response",
            delta="",
            finish_reason="stop",
        )

        assert chunk.finish_reason == "stop"

    def test_chunk_with_usage(self) -> None:
        """Should accept usage stats."""
        usage = Usage(prompt_tokens=100, completion_tokens=50)
        chunk = StreamChunk(
            content="Response",
            delta="",
            usage=usage,
        )

        assert chunk.usage is not None
        assert chunk.usage.total_tokens == 150

    def test_incremental_chunks(self) -> None:
        """Should work for incremental streaming."""
        chunks = [
            StreamChunk(content="Hello", delta="Hello"),
            StreamChunk(content="Hello world", delta=" world"),
            StreamChunk(content="Hello world!", delta="!", finish_reason="stop"),
        ]

        assert chunks[0].content == "Hello"
        assert chunks[1].content == "Hello world"
        assert chunks[2].finish_reason == "stop"
