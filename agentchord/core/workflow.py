"""Workflow orchestration for multi-agent systems.

This module provides the Workflow class for orchestrating multiple agents
with support for sequential and parallel execution patterns.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, TYPE_CHECKING

from agentchord.core.executor import (
    BaseExecutor,
    CompositeExecutor,
    MergeStrategy,
    ParallelExecutor,
    SequentialExecutor,
    SingleAgentExecutor,
)
from agentchord.core.state import WorkflowResult, WorkflowState, WorkflowStatus
from agentchord.errors.exceptions import (
    AgentNotFoundInFlowError,
    EmptyWorkflowError,
    InvalidFlowError,
)

if TYPE_CHECKING:
    from agentchord.core.agent import Agent


class FlowParser:
    """Parses flow DSL strings into executable steps.

    Supported syntax:
        - Sequential: "A -> B -> C"
        - Parallel: "[A, B]"
        - Mixed: "A -> [B, C] -> D"

    Example:
        >>> parser = FlowParser()
        >>> steps = parser.parse("researcher -> [analyzer, summarizer] -> writer")
    """

    ARROW_PATTERN = re.compile(r"\s*->\s*")
    PARALLEL_PATTERN = re.compile(r"\[([^\]]+)\]")

    def parse(
        self,
        flow: str,
        available_agents: list[str],
        merge_strategy: MergeStrategy = MergeStrategy.CONCAT_NEWLINE,
    ) -> list[BaseExecutor]:
        """Parse flow DSL into executor steps.

        Args:
            flow: Flow DSL string (e.g., "A -> B -> C").
            available_agents: List of valid agent names.
            merge_strategy: Strategy for merging parallel outputs.

        Returns:
            List of executor instances.

        Raises:
            InvalidFlowError: If flow syntax is invalid.
            AgentNotFoundInFlowError: If agent name not in available_agents.
        """
        if not flow or not flow.strip():
            raise InvalidFlowError(flow, "Flow string cannot be empty")

        parts = self.ARROW_PATTERN.split(flow.strip())
        steps: list[BaseExecutor] = []

        for part in parts:
            part = part.strip()
            if not part:
                continue

            executor = self._parse_part(part, available_agents, merge_strategy)
            steps.append(executor)

        if not steps:
            raise InvalidFlowError(flow, "No valid steps found")

        return steps

    def _parse_part(
        self,
        part: str,
        available_agents: list[str],
        merge_strategy: MergeStrategy,
    ) -> BaseExecutor:
        """Parse a single part of the flow."""
        parallel_match = self.PARALLEL_PATTERN.match(part)

        if parallel_match:
            return self._parse_parallel(
                parallel_match.group(1),
                available_agents,
                merge_strategy,
            )

        return self._parse_single(part, available_agents)

    def _parse_parallel(
        self,
        content: str,
        available_agents: list[str],
        merge_strategy: MergeStrategy,
    ) -> ParallelExecutor:
        """Parse parallel execution block [A, B, C]."""
        agent_names = [name.strip() for name in content.split(",")]
        agent_names = [name for name in agent_names if name]

        for name in agent_names:
            if name not in available_agents:
                raise AgentNotFoundInFlowError(name, available_agents)

        return ParallelExecutor(agent_names, merge_strategy)

    def _parse_single(
        self,
        agent_name: str,
        available_agents: list[str],
    ) -> SingleAgentExecutor:
        """Parse single agent name."""
        agent_name = agent_name.strip()

        if agent_name not in available_agents:
            raise AgentNotFoundInFlowError(agent_name, available_agents)

        return SingleAgentExecutor(agent_name)


class Workflow:
    """Orchestrates multiple agents in a defined execution flow.

    Supports sequential and parallel execution patterns using a simple DSL.

    Example:
        >>> researcher = Agent(name="researcher", role="Research expert")
        >>> writer = Agent(name="writer", role="Content writer")
        >>>
        >>> workflow = Workflow(
        ...     agents=[researcher, writer],
        ...     flow="researcher -> writer",
        ... )
        >>> result = workflow.run_sync("Write about AI trends")
        >>> print(result.output)
    """

    def __init__(
        self,
        agents: list["Agent"],
        flow: str | None = None,
        merge_strategy: MergeStrategy = MergeStrategy.CONCAT_NEWLINE,
    ) -> None:
        """Initialize workflow with agents and optional flow.

        Args:
            agents: List of Agent instances.
            flow: Flow DSL string. If None, agents run sequentially in order.
            merge_strategy: Strategy for merging parallel execution outputs.
        """
        self._agents: dict[str, "Agent"] = {a.name: a for a in agents}
        self._merge_strategy = merge_strategy
        self._executor: BaseExecutor | None = None

        if flow:
            self._set_flow(flow)
        elif agents:
            self._set_sequential_flow([a.name for a in agents])

    def _set_flow(self, flow: str) -> None:
        """Parse and set the execution flow."""
        parser = FlowParser()
        available = list(self._agents.keys())
        steps = parser.parse(flow, available, self._merge_strategy)
        self._executor = CompositeExecutor(steps)

    def _set_sequential_flow(self, agent_names: list[str]) -> None:
        """Set a simple sequential flow."""
        self._executor = SequentialExecutor(agent_names)

    @property
    def agents(self) -> dict[str, "Agent"]:
        """Get dictionary of agents by name."""
        return self._agents

    @property
    def agent_names(self) -> list[str]:
        """Get list of agent names."""
        return list(self._agents.keys())

    async def run(self, input: str) -> WorkflowResult:
        """Execute the workflow asynchronously.

        Args:
            input: Input text to process.

        Returns:
            WorkflowResult containing output and execution details.

        Raises:
            EmptyWorkflowError: If no agents are defined.
            WorkflowExecutionError: If execution fails.
        """
        if not self._agents:
            raise EmptyWorkflowError()

        if self._executor is None:
            raise EmptyWorkflowError()

        state = WorkflowState(input=input)

        try:
            state = await self._executor.execute(self._agents, state)
            state = state.with_status(WorkflowStatus.COMPLETED)
        except Exception as e:
            state = state.with_error(str(e))
            return WorkflowResult(
                output=state.output or "",
                state=state,
                status=WorkflowStatus.FAILED,
            )

        return WorkflowResult(
            output=state.output or "",
            state=state,
            status=WorkflowStatus.COMPLETED,
        )

    def run_sync(self, input: str) -> WorkflowResult:
        """Execute the workflow synchronously.

        Convenience method for non-async contexts.

        Args:
            input: Input text to process.

        Returns:
            WorkflowResult containing output and execution details.
        """
        return asyncio.run(self.run(input))

    def add_agent(self, agent: "Agent") -> "Workflow":
        """Add an agent to the workflow.

        Args:
            agent: Agent instance to add.

        Returns:
            Self for method chaining.
        """
        self._agents[agent.name] = agent
        return self

    def set_flow(self, flow: str) -> "Workflow":
        """Set or update the execution flow.

        Args:
            flow: Flow DSL string.

        Returns:
            Self for method chaining.
        """
        self._set_flow(flow)
        return self

    async def __aenter__(self) -> Workflow:
        """Enter async context - prepare all agents."""
        for agent in self._agents.values():
            await agent.__aenter__()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context - cleanup all agents."""
        for agent in self._agents.values():
            try:
                await agent.__aexit__(exc_type, exc_val, exc_tb)
            except Exception:
                pass  # Don't mask original exception, cleanup all agents

    async def close(self) -> None:
        """Explicitly cleanup all workflow agents."""
        await self.__aexit__(None, None, None)

    def __repr__(self) -> str:
        agent_count = len(self._agents)
        return f"Workflow(agents={agent_count})"
