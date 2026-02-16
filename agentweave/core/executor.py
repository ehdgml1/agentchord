"""Workflow execution engines.

This module provides different execution strategies for running agents:
- SequentialExecutor: Runs agents one after another
- ParallelExecutor: Runs agents concurrently
- CompositeExecutor: Combines multiple execution steps
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING

from agentweave.core.state import WorkflowState, WorkflowStatus
from agentweave.errors.exceptions import WorkflowExecutionError

if TYPE_CHECKING:
    from agentweave.core.agent import Agent


class MergeStrategy(str, Enum):
    """Strategy for merging parallel execution results."""

    CONCAT = "concat"
    CONCAT_NEWLINE = "concat_newline"
    FIRST = "first"
    LAST = "last"


class BaseExecutor(ABC):
    """Abstract base class for workflow executors.

    Executors define how agents are run within a workflow.
    """

    @abstractmethod
    async def execute(
        self,
        agents: dict[str, "Agent"],
        state: WorkflowState,
    ) -> WorkflowState:
        """Execute agents and return updated state.

        Args:
            agents: Dictionary mapping agent names to Agent instances.
            state: Current workflow state.

        Returns:
            Updated workflow state after execution.
        """
        ...


class SequentialExecutor(BaseExecutor):
    """Executes agents sequentially in specified order.

    Each agent receives the output of the previous agent as input.

    Example:
        >>> executor = SequentialExecutor(["researcher", "writer"])
        >>> state = await executor.execute(agents, initial_state)
    """

    def __init__(self, agent_names: list[str]) -> None:
        """Initialize with ordered list of agent names.

        Args:
            agent_names: Names of agents to execute in order.
        """
        self.agent_names = agent_names

    async def execute(
        self,
        agents: dict[str, "Agent"],
        state: WorkflowState,
    ) -> WorkflowState:
        """Execute agents sequentially."""
        state = state.with_status(WorkflowStatus.RUNNING)

        for idx, agent_name in enumerate(self.agent_names):
            agent = agents[agent_name]
            state = state.model_copy(update={"current_agent": agent_name})

            try:
                result = await agent.run(state.effective_input)
                state = state.with_result(result)
            except Exception as e:
                raise WorkflowExecutionError(
                    f"Agent '{agent_name}' failed: {e}",
                    failed_agent=agent_name,
                    step_index=idx,
                ) from e

        return state


class ParallelExecutor(BaseExecutor):
    """Executes multiple agents concurrently.

    All agents receive the same input and results are merged.

    Example:
        >>> executor = ParallelExecutor(
        ...     ["analyzer", "summarizer"],
        ...     merge_strategy=MergeStrategy.CONCAT_NEWLINE,
        ... )
        >>> state = await executor.execute(agents, state)
    """

    SEPARATOR_MAP = {
        MergeStrategy.CONCAT: "",
        MergeStrategy.CONCAT_NEWLINE: "\n\n",
    }

    def __init__(
        self,
        agent_names: list[str],
        merge_strategy: MergeStrategy = MergeStrategy.CONCAT_NEWLINE,
    ) -> None:
        """Initialize with list of agents to run in parallel.

        Args:
            agent_names: Names of agents to execute concurrently.
            merge_strategy: How to merge results from parallel agents.
        """
        self.agent_names = agent_names
        self.merge_strategy = merge_strategy

    async def execute(
        self,
        agents: dict[str, "Agent"],
        state: WorkflowState,
    ) -> WorkflowState:
        """Execute agents in parallel and merge results."""
        state = state.with_status(WorkflowStatus.RUNNING)
        input_text = state.effective_input

        tasks = [agents[name].run(input_text) for name in self.agent_names]

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            raise WorkflowExecutionError(
                f"Parallel execution failed: {e}",
                failed_agent=None,
            ) from e

        successful_results = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                raise WorkflowExecutionError(
                    f"Agent '{self.agent_names[idx]}' failed: {result}",
                    failed_agent=self.agent_names[idx],
                ) from result
            successful_results.append(result)
            state = state.with_result(result)

        merged_output = self._merge_outputs(successful_results)
        state = state.with_output(merged_output)

        return state

    def _merge_outputs(self, results: list) -> str:
        """Merge outputs based on strategy."""
        if self.merge_strategy == MergeStrategy.FIRST:
            return results[0].output if results else ""

        if self.merge_strategy == MergeStrategy.LAST:
            return results[-1].output if results else ""

        separator = self.SEPARATOR_MAP.get(self.merge_strategy, "\n\n")
        return separator.join(r.output for r in results)


class CompositeExecutor(BaseExecutor):
    """Combines multiple executors into a single execution flow.

    Allows mixing sequential and parallel execution steps.

    Example:
        >>> composite = CompositeExecutor([
        ...     SequentialExecutor(["researcher"]),
        ...     ParallelExecutor(["analyzer", "summarizer"]),
        ...     SequentialExecutor(["writer"]),
        ... ])
        >>> state = await composite.execute(agents, state)
    """

    def __init__(self, steps: list[BaseExecutor]) -> None:
        """Initialize with list of executors to run in sequence.

        Args:
            steps: List of executors to run one after another.
        """
        self.steps = steps

    async def execute(
        self,
        agents: dict[str, "Agent"],
        state: WorkflowState,
    ) -> WorkflowState:
        """Execute all steps in order."""
        for step in self.steps:
            state = await step.execute(agents, state)
        return state


class SingleAgentExecutor(BaseExecutor):
    """Executes a single agent.

    Convenience class for simple workflows.
    """

    def __init__(self, agent_name: str) -> None:
        """Initialize with agent name.

        Args:
            agent_name: Name of the agent to execute.
        """
        self.agent_name = agent_name

    async def execute(
        self,
        agents: dict[str, "Agent"],
        state: WorkflowState,
    ) -> WorkflowState:
        """Execute the single agent."""
        state = state.with_status(WorkflowStatus.RUNNING)
        agent = agents[self.agent_name]

        try:
            result = await agent.run(state.effective_input)
            state = state.with_result(result)
        except Exception as e:
            raise WorkflowExecutionError(
                f"Agent '{self.agent_name}' failed: {e}",
                failed_agent=self.agent_name,
            ) from e

        return state
