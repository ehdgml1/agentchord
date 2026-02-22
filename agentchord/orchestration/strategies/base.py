"""Base strategy for multi-agent orchestration."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agentchord.orchestration.message_bus import MessageBus
    from agentchord.orchestration.shared_context import SharedContext
    from agentchord.orchestration.types import TeamMember, TeamResult


@dataclass
class StrategyContext:
    """Typed context passed to all strategies by AgentTeam.

    Replaces the previous **kwargs pattern to enforce a clear contract
    between AgentTeam.run() and strategy implementations.
    """

    coordinator: Any | None = None
    """Optional dedicated coordinator Agent instance."""

    members: list[TeamMember] = field(default_factory=list)
    """Team member descriptors with name, role, and capabilities."""

    message_bus: MessageBus | None = None
    """Message bus for inter-agent communication."""

    shared_context: SharedContext | None = None
    """Shared key-value store for cross-agent state."""

    max_rounds: int | None = None
    """Maximum number of orchestration rounds.

    When None, each strategy applies its own default:
    - coordinator: 10
    - round_robin: 1
    - debate: 3
    - map_reduce: N/A (always 2: map + reduce)
    """

    callbacks: Any | None = None
    """Optional CallbackManager for event notifications."""

    strategy_name: str = ""
    """Name of the executing strategy (for metadata)."""

    enable_consult: bool = False
    """Whether worker agents can consult peers during execution."""

    max_consult_depth: int = 1
    """Maximum depth of consult chains (1 = worker can consult, but consulted agent cannot consult further)."""


class BaseStrategy(ABC):
    """Abstract base for orchestration strategies.

    All strategies receive the team reference at execution time,
    allowing them to access members, message bus, and shared context.
    """

    @abstractmethod
    async def execute(
        self,
        task: str,
        agents: dict[str, Any],
        ctx: StrategyContext,
    ) -> TeamResult:
        """Execute the orchestration strategy.

        Args:
            task: The input task to execute.
            agents: Dictionary mapping agent names to Agent instances.
            ctx: Typed strategy context with message_bus, shared_context,
                 coordinator, max_rounds, callbacks, etc.

        Returns:
            TeamResult with aggregated output and metadata.
        """
        ...
