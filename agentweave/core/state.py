"""Workflow state management.

This module provides immutable state classes for workflow execution.
States are designed to be passed between agents without mutation.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from agentweave.core.types import AgentResult, Usage


class WorkflowStatus(str, Enum):
    """Status of a workflow execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowState(BaseModel):
    """Immutable state passed between workflow steps.

    Each agent receives the current state and returns a new state
    with updated values. This ensures traceability and debugging.

    Example:
        >>> state = WorkflowState(input="Analyze this text")
        >>> new_state = state.with_output("Analysis complete")
        >>> print(new_state.output)
        "Analysis complete"
    """

    input: str = Field(..., description="Original input to the workflow")
    output: str | None = Field(None, description="Current output (updated by agents)")
    history: list[AgentResult] = Field(
        default_factory=list,
        description="History of all agent executions",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Shared context data between agents",
    )
    current_agent: str | None = Field(
        None,
        description="Name of the currently executing agent",
    )
    status: WorkflowStatus = Field(
        default=WorkflowStatus.PENDING,
        description="Current workflow status",
    )
    error: str | None = Field(None, description="Error message if failed")

    def with_output(self, output: str) -> WorkflowState:
        """Create new state with updated output."""
        return self.model_copy(update={"output": output})

    def with_result(self, result: AgentResult) -> WorkflowState:
        """Create new state with agent result appended to history."""
        return self.model_copy(
            update={
                "history": [*self.history, result],
                "output": result.output,
                "current_agent": result.metadata.get("agent_name"),
            }
        )

    def with_context(self, key: str, value: Any) -> WorkflowState:
        """Create new state with updated context."""
        return self.model_copy(
            update={"context": {**self.context, key: value}}
        )

    def with_status(self, status: WorkflowStatus) -> WorkflowState:
        """Create new state with updated status."""
        return self.model_copy(update={"status": status})

    def with_error(self, error: str) -> WorkflowState:
        """Create new state marked as failed with error message."""
        return self.model_copy(
            update={
                "status": WorkflowStatus.FAILED,
                "error": error,
            }
        )

    @property
    def last_result(self) -> AgentResult | None:
        """Get the most recent agent result."""
        return self.history[-1] if self.history else None

    @property
    def effective_input(self) -> str:
        """Get the input for the next agent (output or original input)."""
        return self.output if self.output is not None else self.input


class WorkflowResult(BaseModel):
    """Final result of a workflow execution.

    Contains the output, execution statistics, and full state history.

    Example:
        >>> result = workflow.run_sync("Analyze and summarize")
        >>> print(f"Output: {result.output}")
        >>> print(f"Total cost: ${result.total_cost:.4f}")
    """

    output: str = Field(..., description="Final output from the workflow")
    state: WorkflowState = Field(..., description="Final workflow state")
    status: WorkflowStatus = Field(..., description="Final status")

    @property
    def total_cost(self) -> float:
        """Calculate total cost across all agents."""
        return sum(r.cost for r in self.state.history)

    @property
    def total_tokens(self) -> int:
        """Calculate total tokens used across all agents."""
        return sum(r.usage.total_tokens for r in self.state.history)

    @property
    def total_duration_ms(self) -> int:
        """Calculate total execution time in milliseconds."""
        return sum(r.duration_ms for r in self.state.history)

    @property
    def agent_results(self) -> list[AgentResult]:
        """Get all agent execution results."""
        return self.state.history

    @property
    def usage(self) -> Usage:
        """Aggregate token usage across all agents."""
        prompt = sum(r.usage.prompt_tokens for r in self.state.history)
        completion = sum(r.usage.completion_tokens for r in self.state.history)
        return Usage(prompt_tokens=prompt, completion_tokens=completion)

    @property
    def is_success(self) -> bool:
        """Check if workflow completed successfully."""
        return self.status == WorkflowStatus.COMPLETED

    @property
    def error(self) -> str | None:
        """Get error message if workflow failed."""
        return self.state.error
