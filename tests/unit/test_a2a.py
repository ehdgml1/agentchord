"""Unit tests for A2A types and client."""

from __future__ import annotations

from datetime import datetime

import pytest

from agentweave.protocols.a2a.types import (
    AgentCard,
    AgentSkill,
    A2AMessage,
    A2ATask,
    A2ATaskStatus,
)


class TestAgentCard:
    """Tests for AgentCard."""

    def test_card_creation_minimal(self) -> None:
        """Card should be created with minimal fields."""
        card = AgentCard(name="test-agent")

        assert card.name == "test-agent"
        assert card.description == ""
        assert card.version == "1.0.0"
        assert card.input_modes == ["text"]
        assert card.output_modes == ["text"]

    def test_card_creation_full(self) -> None:
        """Card should accept all fields."""
        card = AgentCard(
            name="research-agent",
            description="웹 검색 및 정보 수집 전문 Agent",
            version="2.0.0",
            url="http://localhost:8080",
            capabilities=["web_search", "summarization"],
            input_modes=["text", "image"],
            output_modes=["text", "json"],
        )

        assert card.name == "research-agent"
        assert "웹 검색" in card.description
        assert card.version == "2.0.0"
        assert "web_search" in card.capabilities

    def test_card_with_skills(self) -> None:
        """Card should support detailed skills."""
        skill = AgentSkill(
            name="code_review",
            description="Review code for bugs",
            input_schema={"type": "object"},
        )
        card = AgentCard(
            name="dev-agent",
            skills=[skill],
        )

        assert len(card.skills) == 1
        assert card.skills[0].name == "code_review"


class TestA2ATask:
    """Tests for A2ATask."""

    def test_task_creation(self) -> None:
        """Task should be created with input."""
        task = A2ATask(input="Summarize this document")

        assert task.input == "Summarize this document"
        assert task.output is None
        assert task.status == A2ATaskStatus.PENDING
        assert task.id is not None  # Auto-generated UUID

    def test_task_mark_running(self) -> None:
        """mark_running should update status and timestamp."""
        task = A2ATask(input="test")
        running = task.mark_running()

        assert running.status == A2ATaskStatus.RUNNING
        assert running.started_at is not None
        assert task.status == A2ATaskStatus.PENDING  # Original unchanged

    def test_task_mark_completed(self) -> None:
        """mark_completed should update status and output."""
        task = A2ATask(input="test").mark_running()
        completed = task.mark_completed("Result here")

        assert completed.status == A2ATaskStatus.COMPLETED
        assert completed.output == "Result here"
        assert completed.completed_at is not None

    def test_task_mark_failed(self) -> None:
        """mark_failed should update status and error."""
        task = A2ATask(input="test").mark_running()
        failed = task.mark_failed("Something went wrong")

        assert failed.status == A2ATaskStatus.FAILED
        assert failed.error == "Something went wrong"
        assert failed.completed_at is not None

    def test_task_is_terminal(self) -> None:
        """is_terminal should return True for terminal states."""
        pending = A2ATask(input="test")
        running = pending.mark_running()
        completed = running.mark_completed("done")
        failed = running.mark_failed("error")

        assert pending.is_terminal is False
        assert running.is_terminal is False
        assert completed.is_terminal is True
        assert failed.is_terminal is True

    def test_task_duration_ms(self) -> None:
        """duration_ms should calculate elapsed time."""
        task = A2ATask(input="test").mark_running()

        # Duration should be non-negative
        assert task.duration_ms is not None
        assert task.duration_ms >= 0

    def test_task_duration_none_when_not_started(self) -> None:
        """duration_ms should return None if not started."""
        task = A2ATask(input="test")
        assert task.duration_ms is None


class TestA2AMessage:
    """Tests for A2AMessage."""

    def test_message_creation(self) -> None:
        """Message should be created with role and content."""
        msg = A2AMessage(role="user", content="Hello")

        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp is not None

    def test_message_with_metadata(self) -> None:
        """Message should support metadata."""
        msg = A2AMessage(
            role="assistant",
            content="Hi there",
            metadata={"model": "gpt-4"},
        )

        assert msg.metadata["model"] == "gpt-4"


class TestA2ATaskImmutability:
    """Tests for A2ATask immutability."""

    def test_mark_methods_return_new_instance(self) -> None:
        """Mark methods should return new instances."""
        original = A2ATask(input="test")
        running = original.mark_running()
        completed = running.mark_completed("done")

        assert original is not running
        assert running is not completed

    def test_original_task_unchanged(self) -> None:
        """Original task should not be modified."""
        original = A2ATask(input="test")
        original_id = original.id
        original_status = original.status

        _ = original.mark_running().mark_completed("done")

        assert original.id == original_id
        assert original.status == original_status
