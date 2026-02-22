"""Multi-Agent Orchestration module for AgentChord.

Provides structured agent-to-agent communication, team coordination,
and multiple orchestration strategies.
"""

from __future__ import annotations

from agentchord.orchestration.message_bus import MessageBus
from agentchord.orchestration.shared_context import ContextUpdate, SharedContext
from agentchord.orchestration.strategies.base import StrategyContext
from agentchord.orchestration.team import AgentTeam
from agentchord.orchestration.tools import (
    create_consult_tools,
    create_context_tools,
    create_delegation_tools,
)
from agentchord.orchestration.types import (
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
    "StrategyContext",
    "TeamEvent",
    "TeamMember",
    "TeamResult",
    "TeamRole",
    "create_consult_tools",
    "create_context_tools",
    "create_delegation_tools",
]
