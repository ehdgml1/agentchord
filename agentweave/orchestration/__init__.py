"""Multi-Agent Orchestration module for AgentWeave.

Provides structured agent-to-agent communication, team coordination,
and multiple orchestration strategies.
"""

from __future__ import annotations

from agentweave.orchestration.message_bus import MessageBus
from agentweave.orchestration.shared_context import ContextUpdate, SharedContext
from agentweave.orchestration.team import AgentTeam
from agentweave.orchestration.tools import create_context_tools, create_delegation_tools
from agentweave.orchestration.types import (
    AgentMessage,
    AgentOutput,
    MessageType,
    OrchestrationStrategy,
    TeamEvent,
    TeamMember,
    TeamResult,
    TeamRole,
)

__all__ = [
    "AgentMessage",
    "AgentOutput",
    "AgentTeam",
    "ContextUpdate",
    "MessageBus",
    "MessageType",
    "OrchestrationStrategy",
    "SharedContext",
    "TeamEvent",
    "TeamMember",
    "TeamResult",
    "TeamRole",
    "create_context_tools",
    "create_delegation_tools",
]
