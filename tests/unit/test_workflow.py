"""Unit tests for Workflow class and flow parsing."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest

from agentweave import Agent
from agentweave.core.executor import MergeStrategy, ParallelExecutor, SingleAgentExecutor
from agentweave.core.state import WorkflowStatus
from agentweave.core.types import LLMResponse, Message, StreamChunk, Usage
from agentweave.core.workflow import FlowParser, Workflow
from agentweave.errors.exceptions import (
    AgentNotFoundInFlowError,
    EmptyWorkflowError,
    InvalidFlowError,
)
from agentweave.llm.base import BaseLLMProvider


class SequenceProvider(BaseLLMProvider):
    """Provider that returns sequential responses for testing workflows."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = iter(responses)
        self._default = "Default response"

    async def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        content = next(self._responses, self._default)
        return LLMResponse(
            content=content,
            model="test-model",
            usage=Usage(prompt_tokens=10, completion_tokens=len(content)),
            finish_reason="stop",
        )

    async def stream(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """Stream implementation for testing."""
        content = next(self._responses, self._default)
        yield StreamChunk(
            content=content,
            delta=content,
            finish_reason="stop",
            usage=Usage(prompt_tokens=10, completion_tokens=len(content)),
        )

    @property
    def model(self) -> str:
        return "test-model"

    @property
    def provider_name(self) -> str:
        return "test"

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return 0.001

    @property
    def cost_per_1k_output_tokens(self) -> float:
        return 0.002


class TestFlowParser:
    """Tests for FlowParser DSL parsing."""

    def test_parse_single_agent(self) -> None:
        """Single agent name should create SingleAgentExecutor."""
        parser = FlowParser()
        steps = parser.parse("researcher", ["researcher"])

        assert len(steps) == 1
        assert isinstance(steps[0], SingleAgentExecutor)
        assert steps[0].agent_name == "researcher"

    def test_parse_sequential_flow(self) -> None:
        """Arrow-separated names should create sequential steps."""
        parser = FlowParser()
        steps = parser.parse(
            "researcher -> writer -> reviewer",
            ["researcher", "writer", "reviewer"],
        )

        assert len(steps) == 3
        assert all(isinstance(s, SingleAgentExecutor) for s in steps)

    def test_parse_parallel_block(self) -> None:
        """Bracket notation should create ParallelExecutor."""
        parser = FlowParser()
        steps = parser.parse("[analyzer, summarizer]", ["analyzer", "summarizer"])

        assert len(steps) == 1
        assert isinstance(steps[0], ParallelExecutor)
        assert steps[0].agent_names == ["analyzer", "summarizer"]

    def test_parse_mixed_flow(self) -> None:
        """Mixed sequential and parallel should work together."""
        parser = FlowParser()
        agents = ["researcher", "analyzer", "summarizer", "writer"]
        steps = parser.parse("researcher -> [analyzer, summarizer] -> writer", agents)

        assert len(steps) == 3
        assert isinstance(steps[0], SingleAgentExecutor)
        assert isinstance(steps[1], ParallelExecutor)
        assert isinstance(steps[2], SingleAgentExecutor)

    def test_parse_invalid_agent_raises_error(self) -> None:
        """Unknown agent name should raise AgentNotFoundInFlowError."""
        parser = FlowParser()

        with pytest.raises(AgentNotFoundInFlowError) as exc:
            parser.parse("unknown_agent", ["researcher"])

        assert exc.value.agent_name == "unknown_agent"
        assert "researcher" in exc.value.available

    def test_parse_empty_flow_raises_error(self) -> None:
        """Empty flow string should raise InvalidFlowError."""
        parser = FlowParser()

        with pytest.raises(InvalidFlowError):
            parser.parse("", ["researcher"])

    def test_parse_with_whitespace(self) -> None:
        """Parser should handle extra whitespace."""
        parser = FlowParser()
        steps = parser.parse(
            "  researcher  ->  writer  ",
            ["researcher", "writer"],
        )

        assert len(steps) == 2


class TestWorkflowCreation:
    """Tests for Workflow initialization."""

    def test_workflow_with_agents_no_flow(self) -> None:
        """Workflow without flow should use sequential order."""
        provider = SequenceProvider(["r1", "r2"])
        agents = [
            Agent(name="a1", role="Role 1", llm_provider=provider),
            Agent(name="a2", role="Role 2", llm_provider=provider),
        ]

        workflow = Workflow(agents=agents)

        assert workflow.agent_names == ["a1", "a2"]

    def test_workflow_with_flow_string(self) -> None:
        """Workflow with flow should parse and use it."""
        provider = SequenceProvider(["r1", "r2"])
        agents = [
            Agent(name="writer", role="Writer", llm_provider=provider),
            Agent(name="reviewer", role="Reviewer", llm_provider=provider),
        ]

        workflow = Workflow(agents=agents, flow="writer -> reviewer")

        assert workflow.agent_names == ["writer", "reviewer"]

    def test_add_agent_method(self) -> None:
        """add_agent should add to workflow and return self."""
        provider = SequenceProvider(["r1"])
        agent = Agent(name="new_agent", role="New", llm_provider=provider)

        workflow = Workflow(agents=[])
        result = workflow.add_agent(agent)

        assert "new_agent" in workflow.agents
        assert result is workflow  # method chaining

    def test_set_flow_method(self) -> None:
        """set_flow should update execution flow."""
        provider = SequenceProvider(["r1", "r2"])
        agents = [
            Agent(name="a", role="A", llm_provider=provider),
            Agent(name="b", role="B", llm_provider=provider),
        ]

        workflow = Workflow(agents=agents)
        result = workflow.set_flow("b -> a")

        assert result is workflow  # method chaining


class TestWorkflowExecution:
    """Tests for Workflow.run() execution."""

    @pytest.mark.asyncio
    async def test_run_sequential_workflow(self) -> None:
        """Sequential workflow should pass output to next agent."""
        provider = SequenceProvider(["Research done", "Article written"])
        agents = [
            Agent(name="researcher", role="Research", llm_provider=provider),
            Agent(name="writer", role="Write", llm_provider=provider),
        ]

        workflow = Workflow(agents=agents, flow="researcher -> writer")
        result = await workflow.run("Write about AI")

        assert result.is_success
        assert result.output == "Article written"
        assert len(result.agent_results) == 2

    @pytest.mark.asyncio
    async def test_run_parallel_workflow(self) -> None:
        """Parallel workflow should run agents concurrently."""
        provider = SequenceProvider(["Analysis A", "Analysis B"])
        agents = [
            Agent(name="analyzer1", role="Analyze", llm_provider=provider),
            Agent(name="analyzer2", role="Analyze", llm_provider=provider),
        ]

        workflow = Workflow(
            agents=agents,
            flow="[analyzer1, analyzer2]",
            merge_strategy=MergeStrategy.CONCAT_NEWLINE,
        )
        result = await workflow.run("Analyze data")

        assert result.is_success
        assert "Analysis A" in result.output
        assert "Analysis B" in result.output

    @pytest.mark.asyncio
    async def test_run_mixed_workflow(self) -> None:
        """Mixed workflow should handle sequential and parallel."""
        provider = SequenceProvider(["Research", "Analysis A", "Analysis B", "Final"])
        agents = [
            Agent(name="researcher", role="Research", llm_provider=provider),
            Agent(name="analyzer1", role="Analyze", llm_provider=provider),
            Agent(name="analyzer2", role="Analyze", llm_provider=provider),
            Agent(name="writer", role="Write", llm_provider=provider),
        ]

        workflow = Workflow(
            agents=agents,
            flow="researcher -> [analyzer1, analyzer2] -> writer",
        )
        result = await workflow.run("Create report")

        assert result.is_success
        assert result.output == "Final"
        assert len(result.agent_results) == 4

    @pytest.mark.asyncio
    async def test_run_empty_workflow_raises_error(self) -> None:
        """Running workflow with no agents should raise error."""
        workflow = Workflow(agents=[])

        with pytest.raises(EmptyWorkflowError):
            await workflow.run("test")

    def test_run_sync_works(self) -> None:
        """run_sync should work in non-async context."""
        provider = SequenceProvider(["Done"])
        agent = Agent(name="worker", role="Work", llm_provider=provider)

        workflow = Workflow(agents=[agent])
        result = workflow.run_sync("Do work")

        assert result.is_success
        assert result.output == "Done"

    @pytest.mark.asyncio
    async def test_workflow_tracks_cost(self) -> None:
        """Workflow should track total cost across agents."""
        provider = SequenceProvider(["R1", "R2"])
        agents = [
            Agent(name="a1", role="A1", llm_provider=provider),
            Agent(name="a2", role="A2", llm_provider=provider),
        ]

        workflow = Workflow(agents=agents)
        result = await workflow.run("test")

        assert result.total_cost > 0
        assert result.total_tokens > 0

    @pytest.mark.asyncio
    async def test_workflow_preserves_state_history(self) -> None:
        """Workflow should preserve all intermediate states."""
        provider = SequenceProvider(["Step 1", "Step 2", "Step 3"])
        agents = [
            Agent(name=f"agent{i}", role=f"Role {i}", llm_provider=provider)
            for i in range(3)
        ]

        workflow = Workflow(agents=agents)
        result = await workflow.run("start")

        assert len(result.state.history) == 3
        assert result.state.history[0].output == "Step 1"
        assert result.state.history[1].output == "Step 2"
        assert result.state.history[2].output == "Step 3"


class TestWorkflowRepr:
    """Tests for Workflow string representation."""

    def test_repr_shows_agent_count(self) -> None:
        """repr should show number of agents."""
        provider = SequenceProvider([])
        agents = [
            Agent(name=f"a{i}", role=f"R{i}", llm_provider=provider)
            for i in range(3)
        ]

        workflow = Workflow(agents=agents)

        assert "3" in repr(workflow)
