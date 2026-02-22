"""OpenTelemetry integration for AgentChord.

Provides automatic tracing and metrics for agent, workflow, and LLM operations.
Requires: pip install agentchord[telemetry]
"""
from __future__ import annotations

from agentchord.telemetry.tracer import AgentChordTracer, setup_telemetry, get_tracer
from agentchord.telemetry.metrics import AgentChordMetrics
from agentchord.telemetry.collector import (
    TraceCollector,
    TraceSpan,
    ExecutionTrace,
    export_traces_jsonl,
)

__all__ = [
    "AgentChordTracer",
    "AgentChordMetrics",
    "setup_telemetry",
    "get_tracer",
    "TraceCollector",
    "TraceSpan",
    "ExecutionTrace",
    "export_traces_jsonl",
]
