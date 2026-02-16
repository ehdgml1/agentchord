"""Integration tests for Workflow execution flows.

Tests sequential, parallel, mixed, and error handling workflows
with multiple agents wired together.
"""

from __future__ import annotations

import pytest

from agentweave.core.agent import Agent
from agentweave.core.workflow import Workflow
from agentweave.core.executor import MergeStrategy
from agentweave.core.state import WorkflowStatus
from agentweave.tracking.cost import CostTracker
from tests.conftest import MockLLMProvider


def make_agent(name: str, response: str) -> Agent:
    """Helper to create a mock agent."""
    return Agent(
        name=name,
        role=f"{name} role",
        llm_provider=MockLLMProvider(response_content=response),
    )


@pytest.mark.integration
class TestSequentialWorkflow:
    """Sequential workflow execution: A -> B -> C."""

    @pytest.mark.asyncio
    async def test_two_agent_chain(self):
        """Two agents in sequence, output passes through."""
        researcher = make_agent("researcher", "Research findings")
        writer = make_agent("writer", "Written article")

        workflow = Workflow(
            agents=[researcher, writer],
            flow="researcher -> writer",
        )

        result = await workflow.run("Write about AI")

        assert result.is_success
        assert result.output == "Written article"
        assert result.status == WorkflowStatus.COMPLETED
        assert len(result.agent_results) == 2

    @pytest.mark.asyncio
    async def test_three_agent_chain(self):
        """Three agents in sequence."""
        a = make_agent("planner", "Plan output")
        b = make_agent("executor", "Execution output")
        c = make_agent("reviewer", "Review output")

        workflow = Workflow(
            agents=[a, b, c],
            flow="planner -> executor -> reviewer",
        )

        result = await workflow.run("Task")

        assert result.is_success
        assert result.output == "Review output"
        assert len(result.agent_results) == 3
        assert result.total_tokens > 0

    @pytest.mark.asyncio
    async def test_default_sequential_order(self):
        """Without flow DSL, agents run in list order."""
        a = make_agent("first", "First output")
        b = make_agent("second", "Second output")

        workflow = Workflow(agents=[a, b])

        result = await workflow.run("Input")

        assert result.is_success
        assert result.output == "Second output"

    @pytest.mark.asyncio
    async def test_state_passes_between_agents(self):
        """Each agent receives previous agent's output."""
        # The second agent's MockLLMProvider receives messages
        # where the user content is the previous agent's output
        a = make_agent("analyzer", "Analyzed data: key insights")
        b = make_agent("summarizer", "Summary of insights")

        workflow = Workflow(
            agents=[a, b],
            flow="analyzer -> summarizer",
        )

        result = await workflow.run("Raw data here")

        assert result.is_success
        # First agent got "Raw data here", second got "Analyzed data: key insights"
        assert len(result.state.history) == 2
        assert result.state.history[0].output == "Analyzed data: key insights"
        assert result.state.history[1].output == "Summary of insights"


@pytest.mark.integration
class TestParallelWorkflow:
    """Parallel workflow execution: [A, B]."""

    @pytest.mark.asyncio
    async def test_parallel_two_agents(self):
        """Two agents run in parallel, outputs merged."""
        analyzer = make_agent("analyzer", "Analysis result")
        summarizer = make_agent("summarizer", "Summary result")

        workflow = Workflow(
            agents=[analyzer, summarizer],
            flow="[analyzer, summarizer]",
        )

        result = await workflow.run("Data to process")

        assert result.is_success
        assert "Analysis result" in result.output
        assert "Summary result" in result.output
        assert len(result.agent_results) == 2

    @pytest.mark.asyncio
    async def test_merge_strategy_first(self):
        """FIRST merge strategy takes first agent's output."""
        a = make_agent("fast", "Fast result")
        b = make_agent("slow", "Slow result")

        workflow = Workflow(
            agents=[a, b],
            flow="[fast, slow]",
            merge_strategy=MergeStrategy.FIRST,
        )

        result = await workflow.run("Input")

        assert result.is_success
        assert result.output == "Fast result"

    @pytest.mark.asyncio
    async def test_merge_strategy_last(self):
        """LAST merge strategy takes last agent's output."""
        a = make_agent("first", "First result")
        b = make_agent("last", "Last result")

        workflow = Workflow(
            agents=[a, b],
            flow="[first, last]",
            merge_strategy=MergeStrategy.LAST,
        )

        result = await workflow.run("Input")

        assert result.is_success
        assert result.output == "Last result"

    @pytest.mark.asyncio
    async def test_merge_strategy_concat(self):
        """CONCAT merge strategy joins without separator."""
        a = make_agent("a", "Hello")
        b = make_agent("b", "World")

        workflow = Workflow(
            agents=[a, b],
            flow="[a, b]",
            merge_strategy=MergeStrategy.CONCAT,
        )

        result = await workflow.run("Input")

        assert result.is_success
        assert result.output == "HelloWorld"


@pytest.mark.integration
class TestMixedWorkflow:
    """Mixed sequential + parallel flows."""

    @pytest.mark.asyncio
    async def test_sequential_then_parallel(self):
        """A -> [B, C]: one agent feeds into parallel agents."""
        a = make_agent("preprocessor", "Preprocessed data")
        b = make_agent("analyzer1", "Analysis 1")
        c = make_agent("analyzer2", "Analysis 2")

        workflow = Workflow(
            agents=[a, b, c],
            flow="preprocessor -> [analyzer1, analyzer2]",
        )

        result = await workflow.run("Raw data")

        assert result.is_success
        assert "Analysis 1" in result.output
        assert "Analysis 2" in result.output
        assert len(result.agent_results) == 3

    @pytest.mark.asyncio
    async def test_parallel_then_sequential(self):
        """[A, B] -> C: parallel agents feed into one agent."""
        a = make_agent("gatherer1", "Data 1")
        b = make_agent("gatherer2", "Data 2")
        c = make_agent("synthesizer", "Synthesized output")

        workflow = Workflow(
            agents=[a, b, c],
            flow="[gatherer1, gatherer2] -> synthesizer",
        )

        result = await workflow.run("Query")

        assert result.is_success
        assert result.output == "Synthesized output"

    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """A -> [B, C] -> D: full mixed pipeline."""
        researcher = make_agent("researcher", "Research data")
        analyst1 = make_agent("analyst1", "Perspective 1")
        analyst2 = make_agent("analyst2", "Perspective 2")
        writer = make_agent("writer", "Final article")

        workflow = Workflow(
            agents=[researcher, analyst1, analyst2, writer],
            flow="researcher -> [analyst1, analyst2] -> writer",
        )

        result = await workflow.run("Write comprehensive report")

        assert result.is_success
        assert result.output == "Final article"
        assert len(result.agent_results) == 4  # 1 + 2 parallel + 1


@pytest.mark.integration
class TestWorkflowErrorHandling:
    """Error handling in workflow execution."""

    @pytest.mark.asyncio
    async def test_agent_failure_produces_failed_result(self):
        """When an agent fails, workflow returns FAILED status."""
        from agentweave.llm.base import BaseLLMProvider
        from agentweave.core.types import LLMResponse, Usage

        class FailingProvider(BaseLLMProvider):
            @property
            def model(self) -> str:
                return "fail-model"
            @property
            def provider_name(self) -> str:
                return "mock"
            @property
            def cost_per_1k_input_tokens(self) -> float:
                return 0.0
            @property
            def cost_per_1k_output_tokens(self) -> float:
                return 0.0
            async def complete(self, messages, **kwargs):
                raise RuntimeError("LLM is down")
            async def stream(self, messages, **kwargs):
                raise RuntimeError("LLM is down")
                yield  # make it a generator

        ok_agent = make_agent("ok", "OK response")
        fail_agent = Agent(
            name="failer",
            role="Will fail",
            llm_provider=FailingProvider(),
        )

        workflow = Workflow(
            agents=[ok_agent, fail_agent],
            flow="ok -> failer",
        )

        result = await workflow.run("Test")

        assert not result.is_success
        assert result.status == WorkflowStatus.FAILED
        assert result.error is not None
        assert "failer" in result.error


@pytest.mark.integration
class TestParallelFailureHandling:
    """Parallel workflow where one agent fails."""

    @pytest.mark.asyncio
    async def test_parallel_one_fails(self):
        """When one parallel agent fails, workflow reports FAILED."""
        from agentweave.llm.base import BaseLLMProvider

        class FailingProvider(BaseLLMProvider):
            @property
            def model(self) -> str:
                return "fail-model"
            @property
            def provider_name(self) -> str:
                return "mock"
            @property
            def cost_per_1k_input_tokens(self) -> float:
                return 0.0
            @property
            def cost_per_1k_output_tokens(self) -> float:
                return 0.0
            async def complete(self, messages, **kwargs):
                raise RuntimeError("Parallel agent crashed")
            async def stream(self, messages, **kwargs):
                raise RuntimeError("Parallel agent crashed")
                yield  # noqa: unreachable

        ok_agent = make_agent("ok", "OK result")
        fail_agent = Agent(
            name="failer",
            role="Will fail",
            llm_provider=FailingProvider(),
        )

        workflow = Workflow(
            agents=[ok_agent, fail_agent],
            flow="[ok, failer]",
        )

        result = await workflow.run("Test")

        assert not result.is_success
        assert result.status == WorkflowStatus.FAILED
        assert result.error is not None
        assert "failer" in result.error


@pytest.mark.integration
class TestWorkflowCostAggregation:
    """Cost and token tracking across workflow."""

    @pytest.mark.asyncio
    async def test_total_cost_across_agents(self):
        """WorkflowResult aggregates costs from all agents."""
        a = make_agent("a", "Output A")
        b = make_agent("b", "Output B")
        c = make_agent("c", "Output C")

        workflow = Workflow(
            agents=[a, b, c],
            flow="a -> b -> c",
        )

        result = await workflow.run("Input")

        assert result.is_success
        assert result.total_cost > 0
        assert result.total_tokens > 0
        assert result.total_duration_ms >= 0
        # Each mock agent returns Usage(10, 5)=15 tokens, 3 agents = 45
        assert result.usage.prompt_tokens == 30  # 10 * 3
        assert result.usage.completion_tokens == 15  # 5 * 3

    @pytest.mark.asyncio
    async def test_parallel_cost_aggregation(self):
        """Parallel execution still aggregates costs."""
        a = make_agent("a", "A")
        b = make_agent("b", "B")

        workflow = Workflow(
            agents=[a, b],
            flow="[a, b]",
        )

        result = await workflow.run("Input")

        assert result.is_success
        assert result.usage.prompt_tokens == 20  # 10 * 2
        assert result.usage.completion_tokens == 10  # 5 * 2
