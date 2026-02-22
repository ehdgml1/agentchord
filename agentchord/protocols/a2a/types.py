"""A2A type definitions.

This module defines data structures for A2A protocol integration.
Based on Google's Agent2Agent Protocol specification.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class A2ATaskStatus(str, Enum):
    """Status of an A2A task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentSkill(BaseModel):
    """A skill/capability that an agent can perform.

    Example:
        >>> skill = AgentSkill(
        ...     name="code_review",
        ...     description="Review code for bugs and improvements",
        ...     input_schema={"type": "object", "properties": {...}},
        ... )
    """

    name: str = Field(..., description="Skill name")
    description: str = Field("", description="Skill description")
    input_schema: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema for skill input",
    )
    output_schema: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema for skill output",
    )


class AgentCard(BaseModel):
    """A2A Agent Card - metadata describing an agent.

    The Agent Card is the primary way agents advertise their capabilities
    to other agents in the A2A ecosystem.

    Example:
        >>> card = AgentCard(
        ...     name="research-agent",
        ...     description="웹 검색 및 정보 수집 전문 Agent",
        ...     capabilities=["web_search", "summarization"],
        ... )
    """

    name: str = Field(..., description="Agent name")
    description: str = Field("", description="Agent description")
    version: str = Field("1.0.0", description="Agent version")
    url: str | None = Field(None, description="Agent endpoint URL")

    # Capabilities
    capabilities: list[str] = Field(
        default_factory=list,
        description="List of capability identifiers",
    )
    skills: list[AgentSkill] = Field(
        default_factory=list,
        description="Detailed skill definitions",
    )

    # I/O modes
    input_modes: list[str] = Field(
        default_factory=lambda: ["text"],
        description="Supported input modes (e.g., 'text', 'image', 'audio')",
    )
    output_modes: list[str] = Field(
        default_factory=lambda: ["text"],
        description="Supported output modes",
    )

    # Metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional agent metadata",
    )


class A2AMessage(BaseModel):
    """A message in an A2A conversation.

    Example:
        >>> msg = A2AMessage(role="user", content="Analyze this code")
    """

    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Message timestamp",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional message metadata",
    )


class A2ATask(BaseModel):
    """An A2A task - a unit of work sent to an agent.

    Tasks are the primary way to interact with A2A agents.
    Each task has an input, produces an output, and tracks status.

    Example:
        >>> task = A2ATask(input="Summarize this document")
        >>> print(task.id)  # Auto-generated UUID
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique task identifier",
    )
    input: str = Field(..., description="Task input/prompt")
    output: str | None = Field(None, description="Task output/result")
    status: A2ATaskStatus = Field(
        default=A2ATaskStatus.PENDING,
        description="Current task status",
    )

    # Timing
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Task creation timestamp",
    )
    started_at: datetime | None = Field(None, description="Task start timestamp")
    completed_at: datetime | None = Field(None, description="Task completion timestamp")

    # Error handling
    error: str | None = Field(None, description="Error message if failed")

    # Conversation context
    messages: list[A2AMessage] = Field(
        default_factory=list,
        description="Conversation history for this task",
    )

    # Metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional task metadata",
    )

    def mark_running(self) -> A2ATask:
        """Mark task as running."""
        return self.model_copy(
            update={
                "status": A2ATaskStatus.RUNNING,
                "started_at": datetime.utcnow(),
            }
        )

    def mark_completed(self, output: str) -> A2ATask:
        """Mark task as completed with output."""
        return self.model_copy(
            update={
                "status": A2ATaskStatus.COMPLETED,
                "output": output,
                "completed_at": datetime.utcnow(),
            }
        )

    def mark_failed(self, error: str) -> A2ATask:
        """Mark task as failed with error."""
        return self.model_copy(
            update={
                "status": A2ATaskStatus.FAILED,
                "error": error,
                "completed_at": datetime.utcnow(),
            }
        )

    @property
    def is_terminal(self) -> bool:
        """Check if task is in a terminal state."""
        return self.status in (
            A2ATaskStatus.COMPLETED,
            A2ATaskStatus.FAILED,
            A2ATaskStatus.CANCELLED,
        )

    @property
    def duration_ms(self) -> int | None:
        """Calculate task duration in milliseconds."""
        if not self.started_at:
            return None
        end = self.completed_at or datetime.utcnow()
        return int((end - self.started_at).total_seconds() * 1000)
