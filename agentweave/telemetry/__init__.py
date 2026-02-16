"""OpenTelemetry integration for AgentWeave.

Provides automatic tracing and metrics for agent, workflow, and LLM operations.
Requires: pip install agentweave[telemetry]
"""
from __future__ import annotations

from agentweave.telemetry.tracer import AgentWeaveTracer, setup_telemetry, get_tracer
from agentweave.telemetry.metrics import AgentWeaveMetrics
from agentweave.telemetry.collector import (
    TraceCollector,
    TraceSpan,
    ExecutionTrace,
    export_traces_jsonl,
)

__all__ = [
    "AgentWeaveTracer",
    "AgentWeaveMetrics",
    "setup_telemetry",
    "get_tracer",
    "TraceCollector",
    "TraceSpan",
    "ExecutionTrace",
    "export_traces_jsonl",
]
