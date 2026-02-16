"""Base strategy for multi-agent orchestration."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agentweave.orchestration.types import TeamResult


class BaseStrategy(ABC):
    """Abstract base for orchestration strategies.

    All strategies receive the team reference at execution time,
    allowing them to access members, message bus, and shared context.
    """

    @abstractmethod
    async def execute(
        self,
        task: str,
        agents: dict[str, Any],  # name -> Agent mapping
        **kwargs: Any,
    ) -> TeamResult:
        """Execute the orchestration strategy.

        Args:
            task: The input task to execute.
            agents: Dictionary mapping agent names to Agent instances.
            **kwargs: Additional context (message_bus, shared_context,
                     coordinator, max_rounds, callbacks, etc.)

        Returns:
            TeamResult with aggregated output and metadata.
        """
        ...
