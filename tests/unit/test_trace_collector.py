"""Tests for execution trace collector."""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from agentweave.telemetry.collector import (
    ExecutionTrace,
    TraceCollector,
    TraceSpan,
    export_traces_jsonl,
)
from agentweave.tracking.callbacks import CallbackContext, CallbackEvent


class TestTraceSpan:
    """Tests for TraceSpan."""

    def test_creation(self):
        """Test span creation with defaults."""
        span = TraceSpan(name="test", kind="agent")

        assert span.id is not None
        assert span.parent_id is None
        assert span.name == "test"
        assert span.kind == "agent"
        assert span.start_time > 0
        assert span.end_time is None
        assert span.status == "running"
        assert span.attributes == {}
        assert span.events == []

    def test_creation_with_parent(self):
        """Test span creation with parent."""
        parent = TraceSpan(name="parent", kind="agent")
        child = TraceSpan(name="child", kind="llm", parent_id=parent.id)

        assert child.parent_id == parent.id

    def test_duration_ms_running(self):
        """Test duration is None for running span."""
        span = TraceSpan(name="test", kind="agent")
        assert span.duration_ms is None

    def test_duration_ms_completed(self):
        """Test duration calculation for completed span."""
        span = TraceSpan(name="test", kind="agent")
        time.sleep(0.01)  # 10ms
        span.end()

        assert span.duration_ms is not None
        assert span.duration_ms >= 10  # At least 10ms

    def test_end_with_ok_status(self):
        """Test ending span with ok status."""
        span = TraceSpan(name="test", kind="agent")
        span.end("ok")

        assert span.end_time is not None
        assert span.status == "ok"

    def test_end_with_error_status(self):
        """Test ending span with error status."""
        span = TraceSpan(name="test", kind="agent")
        span.end("error")

        assert span.end_time is not None
        assert span.status == "error"

    def test_add_event(self):
        """Test adding events to span."""
        span = TraceSpan(name="test", kind="agent")
        span.add_event("test_event", key="value", count=42)

        assert len(span.events) == 1
        event = span.events[0]
        assert event["name"] == "test_event"
        assert event["key"] == "value"
        assert event["count"] == 42
        assert "timestamp" in event

    def test_add_multiple_events(self):
        """Test adding multiple events."""
        span = TraceSpan(name="test", kind="agent")
        span.add_event("event1")
        span.add_event("event2")
        span.add_event("event3")

        assert len(span.events) == 3
        assert span.events[0]["name"] == "event1"
        assert span.events[1]["name"] == "event2"
        assert span.events[2]["name"] == "event3"

    def test_to_dict(self):
        """Test converting span to dict."""
        span = TraceSpan(
            name="test",
            kind="agent",
            attributes={"key": "value"},
        )
        span.add_event("test_event")
        span.end()

        data = span.to_dict()

        assert data["name"] == "test"
        assert data["kind"] == "agent"
        assert data["status"] == "ok"
        assert data["attributes"]["key"] == "value"
        assert len(data["events"]) == 1
        assert data["duration_ms"] is not None


class TestExecutionTrace:
    """Tests for ExecutionTrace."""

    def test_creation(self):
        """Test trace creation with defaults."""
        trace = ExecutionTrace(name="test_trace")

        assert trace.id is not None
        assert trace.name == "test_trace"
        assert trace.start_time > 0
        assert trace.end_time is None
        assert trace.spans == []
        assert trace.metadata == {}

    def test_duration_ms_running(self):
        """Test duration is None for running trace."""
        trace = ExecutionTrace(name="test")
        assert trace.duration_ms is None

    def test_duration_ms_completed(self):
        """Test duration calculation for completed trace."""
        trace = ExecutionTrace(name="test")
        time.sleep(0.01)
        trace.end()

        assert trace.duration_ms is not None
        assert trace.duration_ms >= 10

    def test_span_count(self):
        """Test span count property."""
        trace = ExecutionTrace(name="test")
        assert trace.span_count == 0

        trace.add_span(TraceSpan(name="span1", kind="agent"))
        assert trace.span_count == 1

        trace.add_span(TraceSpan(name="span2", kind="llm"))
        assert trace.span_count == 2

    def test_error_count(self):
        """Test error count property."""
        trace = ExecutionTrace(name="test")

        span1 = TraceSpan(name="span1", kind="agent")
        span1.end("ok")
        trace.add_span(span1)

        span2 = TraceSpan(name="span2", kind="llm")
        span2.end("error")
        trace.add_span(span2)

        span3 = TraceSpan(name="span3", kind="tool")
        span3.end("error")
        trace.add_span(span3)

        assert trace.error_count == 2

    def test_add_span(self):
        """Test adding spans to trace."""
        trace = ExecutionTrace(name="test")
        span = TraceSpan(name="test_span", kind="agent")

        trace.add_span(span)

        assert len(trace.spans) == 1
        assert trace.spans[0] == span

    def test_to_dict(self):
        """Test converting trace to dict."""
        trace = ExecutionTrace(name="test", metadata={"version": "1.0"})
        span = TraceSpan(name="span1", kind="agent")
        span.end()
        trace.add_span(span)
        trace.end()

        data = trace.to_dict()

        assert data["name"] == "test"
        assert data["span_count"] == 1
        assert data["error_count"] == 0
        assert data["metadata"]["version"] == "1.0"
        assert len(data["spans"]) == 1
        assert data["duration_ms"] is not None

    def test_to_json(self):
        """Test converting trace to JSON string."""
        trace = ExecutionTrace(name="test")
        json_str = trace.to_json()

        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["name"] == "test"

    def test_save_and_load(self, tmp_path):
        """Test saving and loading trace from file."""
        trace = ExecutionTrace(name="test")
        span = TraceSpan(name="span1", kind="agent")
        span.end()
        trace.add_span(span)
        trace.end()

        file_path = tmp_path / "trace.json"
        trace.save(file_path)

        assert file_path.exists()

        loaded = ExecutionTrace.load(file_path)

        assert loaded.id == trace.id
        assert loaded.name == trace.name
        assert loaded.span_count == 1
        assert loaded.spans[0].name == "span1"

    def test_from_dict(self):
        """Test creating trace from dict."""
        data = {
            "id": "test-id",
            "name": "test",
            "start_time": 1000.0,
            "end_time": 2000.0,
            "metadata": {"key": "value"},
            "spans": [
                {
                    "id": "span-1",
                    "parent_id": None,
                    "name": "span1",
                    "kind": "agent",
                    "start_time": 1000.0,
                    "end_time": 1500.0,
                    "status": "ok",
                    "attributes": {},
                    "events": [],
                }
            ],
        }

        trace = ExecutionTrace.from_dict(data)

        assert trace.id == "test-id"
        assert trace.name == "test"
        assert trace.start_time == 1000.0
        assert trace.end_time == 2000.0
        assert trace.metadata["key"] == "value"
        assert len(trace.spans) == 1
        assert trace.spans[0].name == "span1"

    def test_save_creates_directory(self, tmp_path):
        """Test save creates parent directory if needed."""
        trace = ExecutionTrace(name="test")
        file_path = tmp_path / "subdir" / "trace.json"

        trace.save(file_path)

        assert file_path.exists()
        assert file_path.parent.exists()


class TestTraceCollector:
    """Tests for TraceCollector."""

    def test_creation(self):
        """Test collector creation."""
        collector = TraceCollector()

        assert collector.callback_manager is not None
        assert collector.traces == []
        assert collector.get_last_trace() is None

    def test_callback_manager_registration(self):
        """Test callback manager has all handlers registered."""
        collector = TraceCollector()
        manager = collector.callback_manager

        # Check that handlers are registered for key events
        assert CallbackEvent.AGENT_START in manager._callbacks
        assert CallbackEvent.AGENT_END in manager._callbacks
        assert CallbackEvent.LLM_START in manager._callbacks
        assert CallbackEvent.LLM_END in manager._callbacks
        assert CallbackEvent.TOOL_START in manager._callbacks
        assert CallbackEvent.TOOL_END in manager._callbacks

    def test_get_last_trace_empty(self):
        """Test get_last_trace returns None when no traces."""
        collector = TraceCollector()
        assert collector.get_last_trace() is None

    def test_traces_returns_copy(self):
        """Test traces property returns a copy."""
        collector = TraceCollector()
        traces1 = collector.traces
        traces2 = collector.traces

        assert traces1 is not traces2

    def test_clear(self):
        """Test clearing collected traces."""
        collector = TraceCollector()
        collector._traces.append(ExecutionTrace(name="test"))
        collector._active_trace = ExecutionTrace(name="active")
        collector._span_stack.append(TraceSpan(name="span", kind="agent"))

        collector.clear()

        assert collector.traces == []
        assert collector._active_trace is None
        assert collector._span_stack == []

    @pytest.mark.asyncio
    async def test_agent_start_creates_span(self):
        """Test agent start event creates span."""
        collector = TraceCollector()

        ctx = CallbackContext(
            event=CallbackEvent.AGENT_START,
            agent_name="test_agent",
            data={"input": "Hello"},
        )

        await collector._on_agent_start(ctx)

        assert collector._active_trace is not None
        assert len(collector._span_stack) == 1
        span = collector._span_stack[0]
        assert span.name == "agent.test_agent"
        assert span.kind == "agent"
        assert span.attributes["agent_name"] == "test_agent"
        assert span.attributes["input"] == "Hello"

    @pytest.mark.asyncio
    async def test_agent_end_completes_span(self):
        """Test agent end event completes span."""
        collector = TraceCollector()

        # Start agent
        await collector._on_agent_start(
            CallbackContext(
                event=CallbackEvent.AGENT_START,
                agent_name="test_agent",
            )
        )

        # End agent
        await collector._on_agent_end(
            CallbackContext(
                event=CallbackEvent.AGENT_END,
                agent_name="test_agent",
                data={"output": "Response", "cost": 0.001},
            )
        )

        assert len(collector._span_stack) == 0
        assert len(collector.traces) == 1
        trace = collector.get_last_trace()
        assert trace is not None
        assert trace.span_count == 1
        span = trace.spans[0]
        assert span.status == "ok"
        assert span.attributes["output"] == "Response"
        assert span.attributes["cost"] == 0.001

    @pytest.mark.asyncio
    async def test_agent_error_creates_error_span(self):
        """Test agent error event creates error span."""
        collector = TraceCollector()

        await collector._on_agent_start(
            CallbackContext(event=CallbackEvent.AGENT_START, agent_name="test")
        )

        await collector._on_agent_error(
            CallbackContext(
                event=CallbackEvent.AGENT_ERROR,
                agent_name="test",
                data={"error": "Something went wrong"},
            )
        )

        trace = collector.get_last_trace()
        assert trace is not None
        assert trace.error_count == 1
        span = trace.spans[0]
        assert span.status == "error"
        assert span.attributes["error"] == "Something went wrong"

    @pytest.mark.asyncio
    async def test_llm_span_nested_in_agent(self):
        """Test LLM span is nested within agent span."""
        collector = TraceCollector()

        await collector._on_agent_start(
            CallbackContext(event=CallbackEvent.AGENT_START, agent_name="test")
        )

        await collector._on_llm_start(
            CallbackContext(
                event=CallbackEvent.LLM_START,
                data={"model": "gpt-4"},
            )
        )

        await collector._on_llm_end(
            CallbackContext(
                event=CallbackEvent.LLM_END,
                data={"tokens": 100},
            )
        )

        await collector._on_agent_end(
            CallbackContext(event=CallbackEvent.AGENT_END)
        )

        trace = collector.get_last_trace()
        assert trace.span_count == 2

        agent_span = trace.spans[0]
        llm_span = trace.spans[1]

        assert agent_span.kind == "agent"
        assert llm_span.kind == "llm"
        assert llm_span.parent_id == agent_span.id
        assert llm_span.attributes["model"] == "gpt-4"
        assert llm_span.attributes["tokens"] == 100

    @pytest.mark.asyncio
    async def test_tool_span_nested_in_agent(self):
        """Test tool span is nested within agent span."""
        collector = TraceCollector()

        await collector._on_agent_start(
            CallbackContext(event=CallbackEvent.AGENT_START, agent_name="test")
        )

        await collector._on_tool_start(
            CallbackContext(
                event=CallbackEvent.TOOL_START,
                data={"tool_name": "calculator", "arguments": {"x": 1, "y": 2}},
            )
        )

        await collector._on_tool_end(
            CallbackContext(
                event=CallbackEvent.TOOL_END,
                data={"result": 3, "success": True},
            )
        )

        await collector._on_agent_end(
            CallbackContext(event=CallbackEvent.AGENT_END)
        )

        trace = collector.get_last_trace()
        assert trace.span_count == 2

        tool_span = trace.spans[1]
        assert tool_span.kind == "tool"
        assert tool_span.attributes["tool_name"] == "calculator"
        assert tool_span.attributes["arguments"] == {"x": 1, "y": 2}
        assert tool_span.attributes["result"] == "3"

    @pytest.mark.asyncio
    async def test_workflow_span_with_events(self):
        """Test workflow span captures step events."""
        collector = TraceCollector()

        await collector._on_workflow_start(
            CallbackContext(
                event=CallbackEvent.WORKFLOW_START,
                agent_name="workflow1",
            )
        )

        await collector._on_workflow_step(
            CallbackContext(
                event=CallbackEvent.WORKFLOW_STEP,
                data={"step": 1, "agent_name": "agent1"},
            )
        )

        await collector._on_workflow_step(
            CallbackContext(
                event=CallbackEvent.WORKFLOW_STEP,
                data={"step": 2, "agent_name": "agent2"},
            )
        )

        await collector._on_workflow_end(
            CallbackContext(
                event=CallbackEvent.WORKFLOW_END,
                data={"total_cost": 0.05},
            )
        )

        trace = collector.get_last_trace()
        assert trace.span_count == 1

        workflow_span = trace.spans[0]
        assert workflow_span.kind == "workflow"
        assert len(workflow_span.events) == 2
        assert workflow_span.events[0]["step"] == 1
        assert workflow_span.events[1]["step"] == 2

    @pytest.mark.asyncio
    async def test_multiple_traces(self):
        """Test collector handles multiple traces."""
        collector = TraceCollector()

        # First trace
        await collector._on_agent_start(
            CallbackContext(event=CallbackEvent.AGENT_START, agent_name="agent1")
        )
        await collector._on_agent_end(
            CallbackContext(event=CallbackEvent.AGENT_END)
        )

        # Second trace
        await collector._on_agent_start(
            CallbackContext(event=CallbackEvent.AGENT_START, agent_name="agent2")
        )
        await collector._on_agent_end(
            CallbackContext(event=CallbackEvent.AGENT_END)
        )

        assert len(collector.traces) == 2
        assert collector.traces[0].spans[0].attributes["agent_name"] == "agent1"
        assert collector.traces[1].spans[0].attributes["agent_name"] == "agent2"

    @pytest.mark.asyncio
    async def test_llm_error_handling(self):
        """Test LLM error is captured correctly."""
        collector = TraceCollector()

        await collector._on_agent_start(
            CallbackContext(event=CallbackEvent.AGENT_START, agent_name="test")
        )

        await collector._on_llm_start(
            CallbackContext(event=CallbackEvent.LLM_START, data={"model": "gpt-4"})
        )

        await collector._on_llm_error(
            CallbackContext(
                event=CallbackEvent.LLM_ERROR,
                data={"error": "API error"},
            )
        )

        await collector._on_agent_end(
            CallbackContext(event=CallbackEvent.AGENT_END)
        )

        trace = collector.get_last_trace()
        llm_span = trace.spans[1]
        assert llm_span.status == "error"
        assert llm_span.attributes["error"] == "API error"

    @pytest.mark.asyncio
    async def test_tool_error_handling(self):
        """Test tool error is captured correctly."""
        collector = TraceCollector()

        await collector._on_agent_start(
            CallbackContext(event=CallbackEvent.AGENT_START, agent_name="test")
        )

        await collector._on_tool_start(
            CallbackContext(
                event=CallbackEvent.TOOL_START,
                data={"tool_name": "calculator"},
            )
        )

        await collector._on_tool_error(
            CallbackContext(
                event=CallbackEvent.TOOL_ERROR,
                data={"error": "Division by zero"},
            )
        )

        await collector._on_agent_end(
            CallbackContext(event=CallbackEvent.AGENT_END)
        )

        trace = collector.get_last_trace()
        tool_span = trace.spans[1]
        assert tool_span.status == "error"
        assert tool_span.attributes["error"] == "Division by zero"


class TestExportTracesJsonl:
    """Tests for export_traces_jsonl function."""

    def test_export_empty_list(self, tmp_path):
        """Test exporting empty list of traces."""
        file_path = tmp_path / "traces.jsonl"
        export_traces_jsonl([], file_path)

        assert file_path.exists()
        content = file_path.read_text()
        assert content == ""

    def test_export_single_trace(self, tmp_path):
        """Test exporting single trace."""
        trace = ExecutionTrace(name="test")
        span = TraceSpan(name="span1", kind="agent")
        span.end()
        trace.add_span(span)
        trace.end()

        file_path = tmp_path / "traces.jsonl"
        export_traces_jsonl([trace], file_path)

        assert file_path.exists()
        lines = file_path.read_text().strip().split("\n")
        assert len(lines) == 1

        data = json.loads(lines[0])
        assert data["name"] == "test"
        assert data["span_count"] == 1

    def test_export_multiple_traces(self, tmp_path):
        """Test exporting multiple traces."""
        traces = []
        for i in range(3):
            trace = ExecutionTrace(name=f"trace{i}")
            span = TraceSpan(name=f"span{i}", kind="agent")
            span.end()
            trace.add_span(span)
            trace.end()
            traces.append(trace)

        file_path = tmp_path / "traces.jsonl"
        export_traces_jsonl(traces, file_path)

        lines = file_path.read_text().strip().split("\n")
        assert len(lines) == 3

        for i, line in enumerate(lines):
            data = json.loads(line)
            assert data["name"] == f"trace{i}"

    def test_export_creates_directory(self, tmp_path):
        """Test export creates parent directory if needed."""
        trace = ExecutionTrace(name="test")
        file_path = tmp_path / "subdir" / "traces.jsonl"

        export_traces_jsonl([trace], file_path)

        assert file_path.exists()
        assert file_path.parent.exists()
