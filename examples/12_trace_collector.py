"""Example: Using TraceCollector to capture and export execution traces.

This example demonstrates:
- Creating a TraceCollector
- Attaching it to an Agent via callbacks
- Capturing execution traces
- Exporting traces to JSON and JSONL formats
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from agentweave import Agent, TraceCollector
from agentweave.llm.base import BaseLLMProvider
from agentweave.core.types import LLMResponse, Message, StreamChunk, Usage


class MockProvider(BaseLLMProvider):
    """Mock LLM provider for demonstration."""

    async def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any,
    ) -> LLMResponse:
        """Mock completion."""
        return LLMResponse(
            content="Mock response from the agent.",
            model=self.model,
            usage=Usage(prompt_tokens=10, completion_tokens=20),
            finish_reason="stop",
        )

    async def stream(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """Mock streaming."""
        yield StreamChunk(
            content="Mock response",
            delta="Mock response",
            finish_reason="stop",
            usage=Usage(prompt_tokens=10, completion_tokens=20),
        )

    @property
    def model(self) -> str:
        return "mock-model"

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return 0.001

    @property
    def cost_per_1k_output_tokens(self) -> float:
        return 0.002


async def main():
    """Run trace collector example."""
    # Create trace collector
    collector = TraceCollector()
    print("Created TraceCollector")

    # Create agent with collector attached
    provider = MockProvider()
    agent = Agent(
        name="demo",
        role="Demo Agent",
        llm_provider=provider,
        callbacks=collector.callback_manager,
    )
    print(f"Created Agent with callbacks attached")

    # Run agent multiple times to generate traces
    print("\nRunning agent 3 times...")
    for i in range(3):
        result = await agent.run(f"Hello {i + 1}")
        print(f"  Run {i + 1}: {result.output[:50]}...")

    # Get collected traces
    traces = collector.traces
    print(f"\nCollected {len(traces)} traces")

    # Examine last trace
    last_trace = collector.get_last_trace()
    if last_trace:
        print(f"\nLast trace details:")
        print(f"  ID: {last_trace.id}")
        print(f"  Name: {last_trace.name}")
        print(f"  Duration: {last_trace.duration_ms:.2f}ms")
        print(f"  Spans: {last_trace.span_count}")
        print(f"  Errors: {last_trace.error_count}")

        print(f"\n  Span details:")
        for i, span in enumerate(last_trace.spans, 1):
            print(f"    {i}. {span.name} ({span.kind})")
            print(f"       Status: {span.status}")
            print(f"       Duration: {span.duration_ms:.2f}ms" if span.duration_ms else "       Still running")
            if span.parent_id:
                print(f"       Parent: {span.parent_id}")

    # Save last trace to JSON
    output_dir = Path("traces")
    output_dir.mkdir(exist_ok=True)

    if last_trace:
        json_path = output_dir / "last_trace.json"
        last_trace.save(json_path)
        print(f"\nSaved last trace to: {json_path}")

    # Export all traces to JSONL
    from agentweave.telemetry.collector import export_traces_jsonl
    jsonl_path = output_dir / "all_traces.jsonl"
    export_traces_jsonl(traces, jsonl_path)
    print(f"Exported all traces to: {jsonl_path}")

    # Load trace back
    loaded_trace = collector.get_last_trace().__class__.load(json_path)
    print(f"\nLoaded trace from file:")
    print(f"  Name: {loaded_trace.name}")
    print(f"  Spans: {loaded_trace.span_count}")

    # Clear collector
    collector.clear()
    print(f"\nCleared collector, now has {len(collector.traces)} traces")


if __name__ == "__main__":
    asyncio.run(main())
