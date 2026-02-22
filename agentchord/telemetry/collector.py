"""Execution trace collector for AgentChord.

Captures detailed execution traces from agent and workflow runs,
with export to JSON/JSONL for analysis and visualization.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class TraceSpan:
    """A single span in an execution trace.

    Represents one unit of work (agent run, LLM call, tool execution, etc.).
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    parent_id: str | None = None
    name: str = ""
    kind: str = ""  # "agent", "llm", "tool", "workflow"
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    status: str = "running"  # "running", "ok", "error"
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)

    @property
    def duration_ms(self) -> float | None:
        """Calculate duration in milliseconds."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000

    def end(self, status: str = "ok") -> None:
        """Mark span as complete.

        Args:
            status: Final status ("ok" or "error").
        """
        self.end_time = time.time()
        self.status = status

    def add_event(self, name: str, **attrs: Any) -> None:
        """Add an event to this span.

        Args:
            name: Event name.
            **attrs: Event attributes.
        """
        self.events.append({"name": name, "timestamp": time.time(), **attrs})

    def to_dict(self) -> dict[str, Any]:
        """Convert span to dictionary."""
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "name": self.name,
            "kind": self.kind,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "attributes": self.attributes,
            "events": self.events,
        }


@dataclass
class ExecutionTrace:
    """Complete trace of an agent or workflow execution."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    spans: list[TraceSpan] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float | None:
        """Calculate total trace duration in milliseconds."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000

    @property
    def span_count(self) -> int:
        """Get total number of spans."""
        return len(self.spans)

    @property
    def error_count(self) -> int:
        """Get number of spans with error status."""
        return sum(1 for s in self.spans if s.status == "error")

    def end(self) -> None:
        """Mark trace as complete."""
        self.end_time = time.time()

    def add_span(self, span: TraceSpan) -> None:
        """Add a span to this trace.

        Args:
            span: Span to add.
        """
        self.spans.append(span)

    def to_dict(self) -> dict[str, Any]:
        """Convert trace to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "span_count": self.span_count,
            "error_count": self.error_count,
            "metadata": self.metadata,
            "spans": [s.to_dict() for s in self.spans],
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert trace to JSON string.

        Args:
            indent: JSON indentation level.

        Returns:
            JSON string representation.
        """
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def save(self, path: str | Path) -> None:
        """Save trace to JSON file.

        Args:
            path: File path to save to.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionTrace:
        """Load trace from dictionary.

        Args:
            data: Dictionary containing trace data.

        Returns:
            ExecutionTrace instance.
        """
        # Filter out computed properties from span data
        # Only pass known TraceSpan dataclass fields (exclude computed properties)
        _SPAN_FIELDS = {f.name for f in TraceSpan.__dataclass_fields__.values()}
        spans = []
        for span_data in data.get("spans", []):
            span_dict = {k: v for k, v in span_data.items() if k in _SPAN_FIELDS}
            spans.append(TraceSpan(**span_dict))

        return cls(
            id=data["id"],
            name=data["name"],
            start_time=data["start_time"],
            end_time=data.get("end_time"),
            spans=spans,
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def load(cls, path: str | Path) -> ExecutionTrace:
        """Load trace from JSON file.

        Args:
            path: File path to load from.

        Returns:
            ExecutionTrace instance.
        """
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)


class TraceCollector:
    """Collects execution traces from Agent and Workflow runs.

    Registers as a callback listener to automatically capture execution events.

    Example:
        >>> collector = TraceCollector()
        >>> agent = Agent(name="test", role="Test", callbacks=collector.callback_manager)
        >>> result = await agent.run("Hello")
        >>> trace = collector.get_last_trace()
        >>> trace.save("trace.json")
    """

    def __init__(self) -> None:
        """Initialize trace collector."""
        self._traces: list[ExecutionTrace] = []
        self._active_trace: ExecutionTrace | None = None
        self._span_stack: list[TraceSpan] = []
        self._callback_manager = self._create_callback_manager()

    @property
    def callback_manager(self):
        """Get the callback manager to pass to Agent/Workflow."""
        return self._callback_manager

    @property
    def traces(self) -> list[ExecutionTrace]:
        """Get all collected traces."""
        return list(self._traces)

    def get_last_trace(self) -> ExecutionTrace | None:
        """Get the most recent trace."""
        return self._traces[-1] if self._traces else None

    def clear(self) -> None:
        """Clear all collected traces."""
        self._traces.clear()
        self._active_trace = None
        self._span_stack.clear()

    def _create_callback_manager(self):
        """Create and configure callback manager."""
        from agentchord.tracking.callbacks import CallbackManager, CallbackEvent

        manager = CallbackManager()

        # Register handlers for all events
        manager.register(CallbackEvent.AGENT_START, self._on_agent_start)
        manager.register(CallbackEvent.AGENT_END, self._on_agent_end)
        manager.register(CallbackEvent.AGENT_ERROR, self._on_agent_error)
        manager.register(CallbackEvent.LLM_START, self._on_llm_start)
        manager.register(CallbackEvent.LLM_END, self._on_llm_end)
        manager.register(CallbackEvent.LLM_ERROR, self._on_llm_error)
        manager.register(CallbackEvent.TOOL_START, self._on_tool_start)
        manager.register(CallbackEvent.TOOL_END, self._on_tool_end)
        manager.register(CallbackEvent.TOOL_ERROR, self._on_tool_error)
        manager.register(CallbackEvent.WORKFLOW_START, self._on_workflow_start)
        manager.register(CallbackEvent.WORKFLOW_END, self._on_workflow_end)
        manager.register(CallbackEvent.WORKFLOW_STEP, self._on_workflow_step)

        return manager

    def _start_span(self, name: str, kind: str, **attrs: Any) -> TraceSpan:
        """Start a new span.

        Args:
            name: Span name.
            kind: Span kind ("agent", "llm", "tool", "workflow").
            **attrs: Span attributes.

        Returns:
            Created span.
        """
        parent_id = self._span_stack[-1].id if self._span_stack else None
        span = TraceSpan(name=name, kind=kind, parent_id=parent_id, attributes=attrs)

        if self._active_trace is None:
            self._active_trace = ExecutionTrace(name=name)

        self._active_trace.add_span(span)
        self._span_stack.append(span)
        return span

    def _end_span(self, status: str = "ok", **attrs: Any) -> TraceSpan | None:
        """End the current span.

        Args:
            status: Span status ("ok" or "error").
            **attrs: Additional attributes to add.

        Returns:
            Ended span, or None if no active span.
        """
        if not self._span_stack:
            return None
        span = self._span_stack.pop()
        span.end(status)
        span.attributes.update(attrs)
        return span

    def _finish_trace(self) -> None:
        """Finish the active trace and add to collection."""
        if self._active_trace:
            self._active_trace.end()
            self._traces.append(self._active_trace)
            self._active_trace = None
            self._span_stack.clear()

    # Callback handlers
    async def _on_agent_start(self, ctx) -> None:
        """Handle agent start event."""
        self._start_span(
            name=f"agent.{ctx.agent_name or 'unknown'}",
            kind="agent",
            agent_name=ctx.agent_name,
            input=ctx.data.get("input", ""),
        )

    async def _on_agent_end(self, ctx) -> None:
        """Handle agent end event."""
        self._end_span(
            status="ok",
            output=ctx.data.get("output", ""),
            duration_ms=ctx.data.get("duration_ms"),
            cost=ctx.data.get("cost"),
        )
        # If no parent spans, finish the trace
        if not self._span_stack:
            self._finish_trace()

    async def _on_agent_error(self, ctx) -> None:
        """Handle agent error event."""
        self._end_span(status="error", error=ctx.data.get("error", ""))
        if not self._span_stack:
            self._finish_trace()

    async def _on_llm_start(self, ctx) -> None:
        """Handle LLM start event."""
        self._start_span(
            name=f"llm.{ctx.data.get('model', 'unknown')}",
            kind="llm",
            model=ctx.data.get("model", ""),
        )

    async def _on_llm_end(self, ctx) -> None:
        """Handle LLM end event."""
        self._end_span(
            status="ok",
            tokens=ctx.data.get("tokens"),
        )

    async def _on_llm_error(self, ctx) -> None:
        """Handle LLM error event."""
        self._end_span(status="error", error=ctx.data.get("error", ""))

    async def _on_tool_start(self, ctx) -> None:
        """Handle tool start event."""
        self._start_span(
            name=f"tool.{ctx.data.get('tool_name', 'unknown')}",
            kind="tool",
            tool_name=ctx.data.get("tool_name", ""),
            arguments=ctx.data.get("arguments", {}),
        )

    async def _on_tool_end(self, ctx) -> None:
        """Handle tool end event."""
        self._end_span(
            status="ok",
            result=str(ctx.data.get("result", "")),
            success=ctx.data.get("success", True),
        )

    async def _on_tool_error(self, ctx) -> None:
        """Handle tool error event."""
        self._end_span(status="error", error=ctx.data.get("error", ""))

    async def _on_workflow_start(self, ctx) -> None:
        """Handle workflow start event."""
        self._start_span(
            name=f"workflow.{ctx.agent_name or 'unknown'}",
            kind="workflow",
        )

    async def _on_workflow_end(self, ctx) -> None:
        """Handle workflow end event."""
        self._end_span(
            status="ok",
            duration_ms=ctx.data.get("duration_ms"),
            total_cost=ctx.data.get("total_cost"),
        )
        self._finish_trace()

    async def _on_workflow_step(self, ctx) -> None:
        """Handle workflow step event."""
        if self._span_stack:
            self._span_stack[-1].add_event(
                "workflow_step",
                step=ctx.data.get("step"),
                agent_name=ctx.data.get("agent_name"),
            )


def export_traces_jsonl(traces: list[ExecutionTrace], path: str | Path) -> None:
    """Export multiple traces to JSONL (one JSON object per line).

    Args:
        traces: List of traces to export.
        path: File path to write to.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for trace in traces:
            f.write(json.dumps(trace.to_dict(), default=str) + "\n")
