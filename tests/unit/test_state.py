"""Unit tests for WorkflowState and WorkflowResult."""

from __future__ import annotations

import pytest

from agentweave.core.state import WorkflowResult, WorkflowState, WorkflowStatus
from agentweave.core.types import AgentResult, Usage


def create_agent_result(
    output: str,
    agent_name: str = "test-agent",
    prompt_tokens: int = 10,
    completion_tokens: int = 20,
    cost: float = 0.001,
    duration_ms: int = 100,
) -> AgentResult:
    """Create an AgentResult for testing."""
    return AgentResult(
        output=output,
        messages=[],
        usage=Usage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
        cost=cost,
        duration_ms=duration_ms,
        metadata={"agent_name": agent_name},
    )


class TestWorkflowState:
    """Tests for WorkflowState immutability and transformations."""

    def test_state_creation(self) -> None:
        """State should be created with input."""
        state = WorkflowState(input="test input")

        assert state.input == "test input"
        assert state.output is None
        assert state.history == []
        assert state.status == WorkflowStatus.PENDING

    def test_with_output_creates_new_state(self) -> None:
        """with_output should return new state, not mutate."""
        original = WorkflowState(input="test")
        new_state = original.with_output("output text")

        assert original.output is None
        assert new_state.output == "output text"
        assert new_state is not original

    def test_with_result_appends_to_history(self) -> None:
        """with_result should append result to history."""
        state = WorkflowState(input="test")
        result = create_agent_result("first output", "agent1")

        new_state = state.with_result(result)

        assert len(new_state.history) == 1
        assert new_state.history[0] is result
        assert new_state.output == "first output"
        assert len(state.history) == 0  # original unchanged

    def test_with_context_adds_data(self) -> None:
        """with_context should add key-value to context."""
        state = WorkflowState(input="test")
        new_state = state.with_context("key1", "value1")

        assert new_state.context["key1"] == "value1"
        assert "key1" not in state.context

    def test_with_status_updates_status(self) -> None:
        """with_status should update workflow status."""
        state = WorkflowState(input="test")
        running = state.with_status(WorkflowStatus.RUNNING)

        assert running.status == WorkflowStatus.RUNNING
        assert state.status == WorkflowStatus.PENDING

    def test_with_error_sets_failed_status(self) -> None:
        """with_error should set FAILED status and error message."""
        state = WorkflowState(input="test")
        failed = state.with_error("Something went wrong")

        assert failed.status == WorkflowStatus.FAILED
        assert failed.error == "Something went wrong"

    def test_last_result_returns_most_recent(self) -> None:
        """last_result should return the most recent AgentResult."""
        state = WorkflowState(input="test")
        result1 = create_agent_result("first", "agent1")
        result2 = create_agent_result("second", "agent2")

        state = state.with_result(result1).with_result(result2)

        assert state.last_result is result2

    def test_last_result_returns_none_when_empty(self) -> None:
        """last_result should return None when no history."""
        state = WorkflowState(input="test")
        assert state.last_result is None

    def test_effective_input_returns_output_when_available(self) -> None:
        """effective_input should return output if set."""
        state = WorkflowState(input="original")
        state = state.with_output("processed")

        assert state.effective_input == "processed"

    def test_effective_input_returns_input_when_no_output(self) -> None:
        """effective_input should return input when no output."""
        state = WorkflowState(input="original")

        assert state.effective_input == "original"


class TestWorkflowResult:
    """Tests for WorkflowResult aggregations."""

    def test_total_cost_sums_all_agents(self) -> None:
        """total_cost should sum costs from all agent results."""
        state = WorkflowState(input="test")
        state = state.with_result(create_agent_result("out1", cost=0.001))
        state = state.with_result(create_agent_result("out2", cost=0.002))
        state = state.with_result(create_agent_result("out3", cost=0.003))

        result = WorkflowResult(
            output="final",
            state=state,
            status=WorkflowStatus.COMPLETED,
        )

        assert result.total_cost == pytest.approx(0.006, rel=1e-6)

    def test_total_tokens_sums_all_agents(self) -> None:
        """total_tokens should sum tokens from all agent results."""
        state = WorkflowState(input="test")
        state = state.with_result(
            create_agent_result("out1", prompt_tokens=10, completion_tokens=20)
        )
        state = state.with_result(
            create_agent_result("out2", prompt_tokens=15, completion_tokens=25)
        )

        result = WorkflowResult(
            output="final",
            state=state,
            status=WorkflowStatus.COMPLETED,
        )

        assert result.total_tokens == 70  # (10+20) + (15+25)

    def test_total_duration_sums_all_agents(self) -> None:
        """total_duration_ms should sum durations from all agents."""
        state = WorkflowState(input="test")
        state = state.with_result(create_agent_result("out1", duration_ms=100))
        state = state.with_result(create_agent_result("out2", duration_ms=200))

        result = WorkflowResult(
            output="final",
            state=state,
            status=WorkflowStatus.COMPLETED,
        )

        assert result.total_duration_ms == 300

    def test_is_success_for_completed(self) -> None:
        """is_success should be True for COMPLETED status."""
        result = WorkflowResult(
            output="done",
            state=WorkflowState(input="test"),
            status=WorkflowStatus.COMPLETED,
        )

        assert result.is_success is True

    def test_is_success_for_failed(self) -> None:
        """is_success should be False for FAILED status."""
        state = WorkflowState(input="test").with_error("Failed")
        result = WorkflowResult(
            output="",
            state=state,
            status=WorkflowStatus.FAILED,
        )

        assert result.is_success is False

    def test_error_returns_state_error(self) -> None:
        """error property should return state's error message."""
        state = WorkflowState(input="test").with_error("Test error")
        result = WorkflowResult(
            output="",
            state=state,
            status=WorkflowStatus.FAILED,
        )

        assert result.error == "Test error"

    def test_usage_aggregates_tokens(self) -> None:
        """usage property should aggregate prompt and completion tokens."""
        state = WorkflowState(input="test")
        state = state.with_result(
            create_agent_result("out1", prompt_tokens=10, completion_tokens=20)
        )
        state = state.with_result(
            create_agent_result("out2", prompt_tokens=30, completion_tokens=40)
        )

        result = WorkflowResult(
            output="final",
            state=state,
            status=WorkflowStatus.COMPLETED,
        )

        assert result.usage.prompt_tokens == 40
        assert result.usage.completion_tokens == 60
        assert result.usage.total_tokens == 100
