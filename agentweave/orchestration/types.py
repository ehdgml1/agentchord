"""Multi-Agent Orchestration types for AgentWeave.

Defines the core data models for agent-to-agent communication,
team coordination, and orchestration results.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Type of message exchanged between agents."""

    TASK = "task"
    RESULT = "result"
    QUERY = "query"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    SYSTEM = "system"


class TeamRole(str, Enum):
    """Role of an agent within a team."""

    COORDINATOR = "coordinator"
    WORKER = "worker"
    REVIEWER = "reviewer"
    SPECIALIST = "specialist"


class OrchestrationStrategy(str, Enum):
    """Strategy for multi-agent orchestration."""

    COORDINATOR = "coordinator"
    ROUND_ROBIN = "round_robin"
    DEBATE = "debate"
    MAP_REDUCE = "map_reduce"
    SEQUENTIAL = "sequential"


class AgentMessage(BaseModel):
    """A structured message exchanged between agents.

    Example:
        >>> msg = AgentMessage(
        ...     sender="agent-1",
        ...     recipient="agent-2",
        ...     message_type=MessageType.TASK,
        ...     content="Process this data",
        ... )
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender: str
    recipient: str | None = None
    message_type: MessageType
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    parent_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {"frozen": False}


class TeamMember(BaseModel):
    """A member of an agent team with role and capabilities.

    Example:
        >>> member = TeamMember(
        ...     name="research-agent",
        ...     role=TeamRole.SPECIALIST,
        ...     capabilities=["web_search", "summarization"],
        ... )
    """

    name: str
    role: TeamRole = TeamRole.WORKER
    capabilities: list[str] = Field(default_factory=list)
    agent_config: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": False}


class TeamEvent(BaseModel):
    """An event emitted during team execution for streaming.

    Example:
        >>> event = TeamEvent(
        ...     type="agent_start",
        ...     sender="coordinator",
        ...     recipient="worker-1",
        ...     content="Starting task execution",
        ...     round=1,
        ... )
    """

    type: str
    sender: str | None = None
    recipient: str | None = None
    content: str = ""
    round: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentOutput(BaseModel):
    """Output from a single agent within a team execution.

    Example:
        >>> output = AgentOutput(
        ...     agent_name="research-agent",
        ...     role=TeamRole.SPECIALIST,
        ...     output="Research findings...",
        ...     tokens=1500,
        ...     cost=0.03,
        ... )
    """

    agent_name: str
    role: TeamRole
    output: str
    tokens: int = 0
    cost: float = 0.0
    duration_ms: int = 0


class TeamResult(BaseModel):
    """Result of a multi-agent team execution.

    Example:
        >>> result = TeamResult(
        ...     output="Final synthesized result",
        ...     total_cost=0.15,
        ...     total_tokens=5000,
        ...     rounds=3,
        ...     strategy="coordinator",
        ... )
    """

    output: str
    agent_outputs: dict[str, AgentOutput] = Field(default_factory=dict)
    messages: list[AgentMessage] = Field(default_factory=list)
    total_cost: float = 0.0
    total_tokens: int = 0
    rounds: int = 0
    duration_ms: int = 0
    strategy: str = ""
    team_name: str = ""
