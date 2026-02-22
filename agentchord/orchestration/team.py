"""Multi-agent team orchestration.

AgentTeam coordinates multiple agents using configurable strategies
for collaborative task execution.
"""
from __future__ import annotations

import asyncio
import time
import warnings
from typing import Any, AsyncIterator

from agentchord.orchestration.message_bus import MessageBus
from agentchord.orchestration.shared_context import SharedContext
from agentchord.orchestration.strategies.base import StrategyContext
from agentchord.orchestration.types import (
    AgentMessage,
    MessageType,
    OrchestrationStrategy,
    TeamEvent,
    TeamMember,
    TeamResult,
    TeamRole,
)
from agentchord.tracking.callbacks import CallbackEvent


class AgentTeam:
    """A team of agents that collaborate using a chosen strategy.

    AgentTeam coordinates multiple agents to work together on complex tasks.
    It supports multiple orchestration strategies (coordinator, round_robin,
    debate, map_reduce) and provides structured communication via MessageBus
    and SharedContext.

    Example:
        >>> from agentchord import Agent, AgentTeam
        >>> researcher = Agent(name="researcher", role="Research expert", model="gpt-4o")
        >>> writer = Agent(name="writer", role="Content writer", model="gpt-4o")
        >>> team = AgentTeam(
        ...     name="content-team",
        ...     members=[researcher, writer],
        ...     strategy="coordinator",
        ... )
        >>> result = team.run_sync("Write a blog post about AI agents")
        >>> print(result.output)
    """

    def __init__(
        self,
        name: str,
        members: list[Any],  # Agent or TeamMember
        coordinator: Any | None = None,  # Optional coordinator Agent
        strategy: str | OrchestrationStrategy = OrchestrationStrategy.COORDINATOR,
        shared_context: SharedContext | None = None,
        message_bus: MessageBus | None = None,
        max_rounds: int = 10,
        callbacks: Any | None = None,  # CallbackManager
        enable_consult: bool = False,
        max_consult_depth: int = 1,
    ) -> None:
        """Initialize an AgentTeam.

        Args:
            name: Unique name for this team.
            members: List of Agent instances or TeamMember descriptors.
            coordinator: Optional dedicated coordinator Agent.
            strategy: Orchestration strategy name or enum value.
            shared_context: Optional shared state for cross-agent communication.
            message_bus: Optional message bus for agent messaging.
            max_rounds: Maximum orchestration rounds.
            callbacks: Optional callback manager for event notifications.
            enable_consult: Whether worker agents can consult peers during execution.
            max_consult_depth: Maximum depth of consult chains.
        """
        self.name = name
        self._coordinator = coordinator
        self._strategy_name = (
            strategy.value if isinstance(strategy, OrchestrationStrategy) else strategy
        )
        self._shared_context = shared_context or SharedContext()
        self._message_bus = message_bus or MessageBus(callbacks=callbacks)
        self._max_rounds = max_rounds
        self._callbacks = callbacks
        self._enable_consult = enable_consult
        self._max_consult_depth = max_consult_depth
        self._closed = False

        # Process members - accept both Agent instances and TeamMember
        self._members: list[TeamMember] = []
        self._agents: dict[str, Any] = {}  # name -> Agent

        for member in members:
            if isinstance(member, TeamMember):
                self._members.append(member)
                # TeamMember is a descriptor; the caller must also provide
                # the actual Agent via coordinator or a separate mechanism.
            elif hasattr(member, "name") and hasattr(member, "run"):
                # It's an Agent instance
                tm = TeamMember(name=member.name, role=TeamRole.WORKER)
                self._members.append(tm)
                self._agents[member.name] = member
                self._message_bus.register(member.name)
            else:
                raise TypeError(f"Expected Agent or TeamMember, got {type(member)}")

        # Register coordinator
        if self._coordinator:
            if self._coordinator.name not in self._agents:
                self._agents[self._coordinator.name] = self._coordinator
                self._message_bus.register(self._coordinator.name)

        # Build strategy instance
        self._strategy = self._resolve_strategy(self._strategy_name)

    def _resolve_strategy(self, name: str) -> Any:
        """Resolve strategy name to strategy instance."""
        from agentchord.orchestration.strategies import (
            CoordinatorStrategy,
            DebateStrategy,
            MapReduceStrategy,
            RoundRobinStrategy,
        )

        if name == "sequential":
            warnings.warn(
                "'sequential' strategy is deprecated, use 'round_robin' instead.",
                DeprecationWarning,
                stacklevel=2,
            )

        strategies = {
            "coordinator": CoordinatorStrategy,
            "round_robin": RoundRobinStrategy,
            "debate": DebateStrategy,
            "map_reduce": MapReduceStrategy,
            "sequential": RoundRobinStrategy,
        }
        cls = strategies.get(name)
        if cls is None:
            raise ValueError(
                f"Unknown strategy '{name}'. "
                f"Available: {', '.join(strategies.keys())}"
            )
        return cls()

    @property
    def members(self) -> list[TeamMember]:
        """List of team members."""
        return list(self._members)

    @property
    def agents(self) -> dict[str, Any]:
        """Dictionary of agent name to Agent instance."""
        return dict(self._agents)

    @property
    def strategy(self) -> str:
        """Current strategy name."""
        return self._strategy_name

    @property
    def shared_context(self) -> SharedContext:
        """Team's shared context."""
        return self._shared_context

    @property
    def message_bus(self) -> MessageBus:
        """Team's message bus."""
        return self._message_bus

    async def run(self, task: str) -> TeamResult:
        """Execute the team on a task.

        Args:
            task: The input task to collaborate on.

        Returns:
            TeamResult with aggregated output and metadata.

        Raises:
            RuntimeError: If the team has been closed.
        """
        if self._closed:
            raise RuntimeError("AgentTeam has been closed")

        start_time = time.time()

        # Emit start event
        if self._callbacks:
            await self._callbacks.emit(
                CallbackEvent.ORCHESTRATION_START,
                team=self.name,
                strategy=self._strategy_name,
                members=[m.name for m in self._members],
            )

        try:
            ctx = StrategyContext(
                coordinator=self._coordinator,
                members=self._members,
                message_bus=self._message_bus,
                shared_context=self._shared_context,
                max_rounds=self._max_rounds,
                callbacks=self._callbacks,
                strategy_name=self._strategy_name,
                enable_consult=self._enable_consult,
                max_consult_depth=self._max_consult_depth,
            )
            result = await self._strategy.execute(
                task=task,
                agents=self._agents,
                ctx=ctx,
            )

            # Ensure team metadata is set
            result.team_name = self.name
            if not result.strategy:
                result.strategy = self._strategy_name
            if not result.duration_ms:
                result.duration_ms = int((time.time() - start_time) * 1000)

            # Emit end event
            if self._callbacks:
                await self._callbacks.emit(
                    CallbackEvent.ORCHESTRATION_END,
                    team=self.name,
                    rounds=result.rounds,
                    total_cost=result.total_cost,
                    total_tokens=result.total_tokens,
                )

            return result

        except Exception as e:
            if self._callbacks:
                await self._callbacks.emit(
                    CallbackEvent.ORCHESTRATION_ERROR,
                    team=self.name,
                    error=str(e),
                )
            raise

    async def stream(self, task: str) -> AsyncIterator[TeamEvent]:
        """Replay team execution events after completion.

        Note: This is a post-hoc replay, not true real-time streaming.
        The full execution completes first via run(), then events are
        yielded from the execution history. For true streaming,
        strategy-level streaming support would be needed.

        Yields TeamEvent instances representing agent communications
        and results from the completed execution.

        Args:
            task: The input task to collaborate on.

        Yields:
            TeamEvent instances tracking execution progress.

        Raises:
            RuntimeError: If the team has been closed.
        """
        if self._closed:
            raise RuntimeError("AgentTeam has been closed")

        yield TeamEvent(
            type="team_start",
            content=f"Starting team '{self.name}' with strategy '{self._strategy_name}'",
        )

        # Run the team and yield events from the result
        result = await self.run(task)

        # Yield message events from history
        for msg in result.messages:
            yield TeamEvent(
                type="agent_message",
                sender=msg.sender,
                recipient=msg.recipient,
                content=msg.content[:500],
                metadata={"message_type": msg.message_type.value},
            )

        # Yield agent output events
        for name, output in result.agent_outputs.items():
            role_value = (
                output.role.value
                if hasattr(output.role, "value")
                else str(output.role)
            )
            yield TeamEvent(
                type="agent_result",
                sender=output.agent_name,
                content=output.output[:500],
                metadata={
                    "role": role_value,
                    "tokens": output.tokens,
                    "cost": output.cost,
                },
            )

        # Final result
        yield TeamEvent(
            type="team_complete",
            content=result.output,
            round=result.rounds,
            metadata={
                "total_cost": result.total_cost,
                "total_tokens": result.total_tokens,
                "duration_ms": result.duration_ms,
            },
        )

    def run_sync(self, task: str) -> TeamResult:
        """Synchronous wrapper for run().

        Convenience method for non-async contexts.

        Args:
            task: The input task to collaborate on.

        Returns:
            TeamResult with aggregated output and metadata.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, self.run(task)).result()
        return asyncio.run(self.run(task))

    async def close(self) -> None:
        """Close the team and release resources.

        Propagates close() to all child agents to flush memory stores
        and disconnect MCP clients. Errors from individual agents are
        suppressed to ensure all agents get closed.

        Safe to call multiple times (idempotent).
        """
        if self._closed:
            return
        self._closed = True

        # Close all child agents (suppress individual errors)
        for agent_name, agent in self._agents.items():
            if hasattr(agent, "close"):
                try:
                    await agent.close()
                except Exception:
                    pass  # Ensure remaining agents still get closed

        self._message_bus.clear()

    async def __aenter__(self) -> AgentTeam:
        """Enter async context."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Exit async context - close the team."""
        await self.close()

    def __repr__(self) -> str:
        return (
            f"AgentTeam(name={self.name!r}, "
            f"members={len(self._members)}, "
            f"strategy={self._strategy_name!r})"
        )
