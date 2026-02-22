"""Agent performance benchmarks.

These benchmarks measure framework overhead using ultra-fast mock providers.
Thresholds are generous to account for CI environment variability.
"""

from __future__ import annotations

import time
from typing import Any

import pytest

from agentchord.core.agent import Agent
from agentchord.memory.conversation import ConversationMemory
from agentchord.memory.base import MemoryEntry
from agentchord.tracking.cost import CostTracker


class TestAgentBenchmarks:
    """Agent execution performance benchmarks."""

    @pytest.mark.asyncio
    async def test_agent_run_latency(self, bench_agent: Agent) -> None:
        """Measure single agent.run() latency.

        Tests the framework overhead for a single agent execution.
        Target: < 10ms average, < 20ms p99 with mock provider.
        """
        times: list[float] = []
        for _ in range(100):
            start = time.perf_counter()
            await bench_agent.run("Test input")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_ms = sum(times) / len(times)
        p99_ms = sorted(times)[98]

        # Agent.run() overhead should be < 10ms average with mock provider
        assert avg_ms < 10, f"Average latency {avg_ms:.2f}ms exceeds 10ms threshold"
        assert p99_ms < 20, f"P99 latency {p99_ms:.2f}ms exceeds 20ms threshold"

    @pytest.mark.asyncio
    async def test_agent_run_with_memory(self, bench_provider: Any) -> None:
        """Agent with memory should not add significant overhead.

        Tests that ConversationMemory integration doesn't degrade performance.
        Target: < 15ms average with memory enabled.
        """
        memory = ConversationMemory()
        agent = Agent(
            name="mem-bench",
            role="Bench",
            llm_provider=bench_provider,
            memory=memory,
        )

        times: list[float] = []
        for _ in range(100):
            start = time.perf_counter()
            await agent.run("Test input")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_ms = sum(times) / len(times)
        assert avg_ms < 15, f"Average latency with memory {avg_ms:.2f}ms exceeds 15ms"

    @pytest.mark.asyncio
    async def test_agent_run_with_cost_tracker(self, bench_provider: Any) -> None:
        """Agent with cost tracker overhead.

        Tests that CostTracker integration doesn't degrade performance.
        Target: < 15ms average with cost tracking enabled.
        """
        tracker = CostTracker()
        agent = Agent(
            name="cost-bench",
            role="Bench",
            llm_provider=bench_provider,
            cost_tracker=tracker,
        )

        times: list[float] = []
        for _ in range(50):
            start = time.perf_counter()
            await agent.run("Test input")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_ms = sum(times) / len(times)
        assert (
            avg_ms < 15
        ), f"Average latency with cost tracker {avg_ms:.2f}ms exceeds 15ms"

    @pytest.mark.asyncio
    async def test_agent_run_throughput(self, bench_agent: Agent) -> None:
        """Measure agent execution throughput.

        Tests how many agent executions can be completed per second.
        Target: > 50 executions/second.
        """
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            await bench_agent.run("Test input")
        elapsed = time.perf_counter() - start

        throughput = iterations / elapsed
        assert throughput > 50, f"Throughput {throughput:.2f} ops/sec < 50 ops/sec"

    @pytest.mark.asyncio
    async def test_agent_streaming_latency(self, bench_agent: Agent) -> None:
        """Measure agent.stream() latency.

        Tests streaming execution overhead.
        Target: < 10ms average for streaming calls.
        """
        times: list[float] = []
        for _ in range(50):
            start = time.perf_counter()
            async for _ in bench_agent.stream("Test input"):
                pass
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_ms = sum(times) / len(times)
        assert (
            avg_ms < 10
        ), f"Average streaming latency {avg_ms:.2f}ms exceeds 10ms threshold"


class TestMemoryBenchmarks:
    """Memory operation benchmarks."""

    def test_conversation_memory_add_1000(self) -> None:
        """Add 1000 entries to ConversationMemory.

        Tests memory entry insertion performance.
        Target: < 100ms for 1000 entries.
        """
        memory = ConversationMemory(max_entries=2000)

        start = time.perf_counter()
        for i in range(1000):
            memory.add(MemoryEntry(content=f"Message {i}", role="user"))
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100, f"Adding 1000 entries took {elapsed_ms:.2f}ms"
        assert len(memory) == 1000

    def test_conversation_memory_search_performance(self) -> None:
        """Search in a large ConversationMemory.

        Tests search performance with 5000 entries.
        Target: < 500ms for 100 searches.
        """
        memory = ConversationMemory(max_entries=5000)
        for i in range(5000):
            memory.add(MemoryEntry(content=f"Message about topic {i % 100}", role="user"))

        start = time.perf_counter()
        for _ in range(100):
            memory.search("topic 42", limit=5)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 500, f"100 searches took {elapsed_ms:.2f}ms"

    def test_conversation_memory_get_recent(self) -> None:
        """Retrieve recent entries from ConversationMemory.

        Tests recent entry retrieval performance.
        Target: < 50ms for 100 get_recent calls.
        """
        memory = ConversationMemory(max_entries=2000)
        for i in range(1000):
            memory.add(MemoryEntry(content=f"Message {i}", role="user"))

        start = time.perf_counter()
        for _ in range(100):
            _ = memory.get_recent(limit=10)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 50, f"100 get_recent() calls took {elapsed_ms:.2f}ms"

    def test_semantic_memory_search_performance(self) -> None:
        """Semantic memory vector search.

        Tests vector similarity search performance.
        Target: < 2000ms for 50 semantic searches on 500 entries.
        """
        from agentchord.memory.semantic import SemanticMemory

        # Simple deterministic embedding function
        def embed(text: str) -> list[float]:
            # Convert characters to normalized floats
            return [float(ord(c) % 10) / 10 for c in text[:50].ljust(50)]

        memory = SemanticMemory(embedding_func=embed)
        for i in range(500):
            memory.add(MemoryEntry(content=f"Document about topic {i}"))

        start = time.perf_counter()
        for _ in range(50):
            memory.search("topic 42", limit=5)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 2000, f"50 semantic searches took {elapsed_ms:.2f}ms"

    def test_semantic_memory_add_performance(self) -> None:
        """Semantic memory insertion performance.

        Tests embedding and insertion overhead.
        Target: < 500ms for 200 entries.
        """
        from agentchord.memory.semantic import SemanticMemory

        def embed(text: str) -> list[float]:
            return [float(ord(c) % 10) / 10 for c in text[:50].ljust(50)]

        memory = SemanticMemory(embedding_func=embed)

        start = time.perf_counter()
        for i in range(200):
            memory.add(MemoryEntry(content=f"Document {i}"))
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 500, f"Adding 200 entries took {elapsed_ms:.2f}ms"

    def test_working_memory_operations(self) -> None:
        """Working memory set/get cycle.

        Tests key-value operations performance.
        Target: < 100ms for 1000 set + 1000 get operations.
        """
        from agentchord.memory.working import WorkingMemory

        memory = WorkingMemory(max_items=1000)

        start = time.perf_counter()
        for i in range(1000):
            memory.set(f"key_{i}", f"value_{i}")
        for i in range(1000):
            memory.get_value(f"key_{i}")
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100, f"1000 set + 1000 get took {elapsed_ms:.2f}ms"

    def test_working_memory_increment(self) -> None:
        """Working memory increment performance.

        Tests atomic increment operations.
        Target: < 50ms for 1000 increments.
        """
        from agentchord.memory.working import WorkingMemory

        memory = WorkingMemory()

        # Initialize counters first
        for i in range(10):
            memory.set(f"counter_{i}", 0)

        start = time.perf_counter()
        for i in range(1000):
            memory.increment(f"counter_{i % 10}")
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 50, f"1000 increments took {elapsed_ms:.2f}ms"


class TestWorkflowBenchmarks:
    """Workflow execution benchmarks."""

    @pytest.mark.asyncio
    async def test_sequential_workflow_3_agents(self, bench_provider: Any) -> None:
        """Sequential workflow with 3 agents.

        Tests sequential workflow execution overhead.
        Target: < 50ms average for 3-agent sequential flow.
        """
        from agentchord.core.workflow import Workflow

        agents = [
            Agent(name=f"agent_{i}", role=f"Agent {i}", llm_provider=bench_provider)
            for i in range(3)
        ]
        workflow = Workflow(agents=agents, flow="agent_0 -> agent_1 -> agent_2")

        times: list[float] = []
        for _ in range(20):
            start = time.perf_counter()
            await workflow.run("Test")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_ms = sum(times) / len(times)
        assert avg_ms < 50, f"3-agent workflow avg {avg_ms:.2f}ms exceeds 50ms"

    @pytest.mark.asyncio
    async def test_parallel_workflow_5_agents(self, bench_provider: Any) -> None:
        """Parallel workflow with 5 agents.

        Tests parallel workflow execution with asyncio concurrency.
        Target: < 50ms average (should be similar to single agent due to asyncio).
        """
        from agentchord.core.workflow import Workflow

        agents = [
            Agent(name=f"p_{i}", role=f"Parallel {i}", llm_provider=bench_provider)
            for i in range(5)
        ]
        workflow = Workflow(
            agents=agents,
            flow="[p_0, p_1, p_2, p_3, p_4]",
        )

        times: list[float] = []
        for _ in range(20):
            start = time.perf_counter()
            await workflow.run("Test")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_ms = sum(times) / len(times)
        # Parallel should be similar to single agent due to asyncio
        assert avg_ms < 50, f"5-agent parallel workflow avg {avg_ms:.2f}ms exceeds 50ms"

    @pytest.mark.asyncio
    async def test_complex_workflow_10_agents(self, bench_provider: Any) -> None:
        """Complex workflow with 10 agents (mixed sequential and parallel).

        Tests workflow orchestration overhead with complex topology.
        Target: < 100ms average for 10-agent mixed flow.
        """
        from agentchord.core.workflow import Workflow

        agents = [
            Agent(name=f"node_{i}", role=f"Node {i}", llm_provider=bench_provider)
            for i in range(10)
        ]
        # Sequential batch -> parallel batch -> sequential finish
        workflow = Workflow(
            agents=agents,
            flow="node_0 -> node_1 -> [node_2, node_3, node_4, node_5] -> node_6 -> [node_7, node_8] -> node_9",
        )

        times: list[float] = []
        for _ in range(10):
            start = time.perf_counter()
            await workflow.run("Test")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_ms = sum(times) / len(times)
        assert avg_ms < 100, f"10-agent complex workflow avg {avg_ms:.2f}ms exceeds 100ms"


class TestStructuredOutputBenchmarks:
    """Structured output parsing benchmarks."""

    def test_schema_validation_speed(self) -> None:
        """OutputSchema validation throughput.

        Tests Pydantic validation performance.
        Target: < 500ms for 1000 validations.
        """
        import json

        from pydantic import BaseModel

        from agentchord.core.structured import OutputSchema

        class Result(BaseModel):
            name: str
            score: float
            tags: list[str]

        schema = OutputSchema(Result)
        test_data = json.dumps({"name": "test", "score": 0.95, "tags": ["a", "b"]})

        start = time.perf_counter()
        for _ in range(1000):
            schema.validate(test_data)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 500, f"1000 validations took {elapsed_ms:.2f}ms"

    def test_json_extraction_speed(self) -> None:
        """JSON extraction from messy LLM output.

        Tests regex-based JSON extraction from markdown-wrapped output.
        Target: < 1000ms for 1000 extractions.
        """
        from pydantic import BaseModel

        from agentchord.core.structured import OutputSchema

        class Simple(BaseModel):
            value: int

        schema = OutputSchema(Simple)
        messy_input = 'Here is the result:\n```json\n{"value": 42}\n```\nDone!'

        start = time.perf_counter()
        for _ in range(1000):
            schema.validate(messy_input)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 1000, f"1000 extractions took {elapsed_ms:.2f}ms"

    def test_complex_schema_validation(self) -> None:
        """Complex nested schema validation.

        Tests performance with deeply nested Pydantic models.
        Target: < 1000ms for 500 validations.
        """
        import json

        from pydantic import BaseModel

        from agentchord.core.structured import OutputSchema

        class Address(BaseModel):
            street: str
            city: str
            zip: str

        class Person(BaseModel):
            name: str
            age: int
            address: Address
            tags: list[str]

        class Team(BaseModel):
            name: str
            members: list[Person]

        schema = OutputSchema(Team)
        test_data = json.dumps(
            {
                "name": "Engineering",
                "members": [
                    {
                        "name": "Alice",
                        "age": 30,
                        "address": {"street": "123 Main", "city": "NYC", "zip": "10001"},
                        "tags": ["python", "rust"],
                    },
                    {
                        "name": "Bob",
                        "age": 25,
                        "address": {"street": "456 Oak", "city": "SF", "zip": "94102"},
                        "tags": ["go", "typescript"],
                    },
                ],
            }
        )

        start = time.perf_counter()
        for _ in range(500):
            schema.validate(test_data)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 1000, f"500 complex validations took {elapsed_ms:.2f}ms"


class TestCostTrackingBenchmarks:
    """Cost tracking performance benchmarks."""

    def test_cost_tracker_track_throughput(self) -> None:
        """Cost tracker track() throughput.

        Tests cost tracking overhead for high-volume scenarios.
        Target: < 100ms for 1000 track calls.
        """
        from agentchord.tracking.models import CostEntry, TokenUsage

        tracker = CostTracker()

        start = time.perf_counter()
        for i in range(1000):
            tracker.track(
                CostEntry(
                    model="test-model",
                    usage=TokenUsage(prompt_tokens=100, completion_tokens=50),
                    cost_usd=0.01,
                )
            )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100, f"1000 cost records took {elapsed_ms:.2f}ms"
        assert abs(tracker.total_cost - 10.0) < 0.01  # 1000 * 0.01 (with floating point tolerance)

    def test_cost_tracker_get_summary(self) -> None:
        """Cost tracker summary generation.

        Tests summary aggregation performance.
        Target: < 50ms for summary after 1000 records.
        """
        from agentchord.tracking.models import CostEntry, TokenUsage

        tracker = CostTracker()

        for i in range(1000):
            tracker.track(
                CostEntry(
                    model=f"model_{i % 3}",
                    usage=TokenUsage(prompt_tokens=100, completion_tokens=50),
                    cost_usd=0.01,
                )
            )

        start = time.perf_counter()
        for _ in range(100):
            _ = tracker.get_summary()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 50, f"100 get_summary() calls took {elapsed_ms:.2f}ms"


class TestToolExecutionBenchmarks:
    """Tool execution benchmarks."""

    @pytest.mark.asyncio
    async def test_tool_registration_overhead(self, bench_provider: Any) -> None:
        """Tool registration performance.

        Tests overhead of registering tools with agents.
        Target: < 10ms for registering 10 tools.
        """
        from agentchord.tools.base import Tool, ToolParameter

        def dummy_func(x: int) -> int:
            return x * 2

        tools = [
            Tool(
                name=f"tool_{i}",
                description=f"Tool {i}",
                parameters=[ToolParameter(name="x", type="integer")],
                func=dummy_func,
            )
            for i in range(10)
        ]

        start = time.perf_counter()
        agent = Agent(
            name="tool-bench",
            role="Benchmark",
            llm_provider=bench_provider,
            tools=tools,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 10, f"Registering 10 tools took {elapsed_ms:.2f}ms"
        assert len(agent.tools) == 10

    @pytest.mark.asyncio
    async def test_tool_execution_sync(self) -> None:
        """Synchronous tool execution overhead.

        Tests tool wrapper execution performance.
        Target: < 100ms for 500 sync tool executions.
        """
        from agentchord.tools.base import Tool, ToolParameter

        def add(a: int, b: int) -> int:
            return a + b

        tool = Tool(
            name="add",
            description="Add two numbers",
            parameters=[
                ToolParameter(name="a", type="integer"),
                ToolParameter(name="b", type="integer"),
            ],
            func=add,
        )

        start = time.perf_counter()
        for i in range(500):
            await tool.execute(a=i, b=1)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100, f"500 sync tool executions took {elapsed_ms:.2f}ms"

    @pytest.mark.asyncio
    async def test_tool_execution_async(self) -> None:
        """Asynchronous tool execution overhead.

        Tests async tool wrapper execution performance.
        Target: < 100ms for 500 async tool executions.
        """
        from agentchord.tools.base import Tool, ToolParameter

        async def add_async(a: int, b: int) -> int:
            return a + b

        tool = Tool(
            name="add_async",
            description="Add two numbers asynchronously",
            parameters=[
                ToolParameter(name="a", type="integer"),
                ToolParameter(name="b", type="integer"),
            ],
            func=add_async,
        )

        start = time.perf_counter()
        for i in range(500):
            await tool.execute(a=i, b=1)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100, f"500 async tool executions took {elapsed_ms:.2f}ms"
