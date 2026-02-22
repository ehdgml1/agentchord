"""Metrics collection for AgentChord using OpenTelemetry.

Tracks latency, token counts, costs, and error rates.
"""
from __future__ import annotations

from typing import Any

try:
    from opentelemetry import metrics
    HAS_OTEL = True
except ImportError:
    HAS_OTEL = False


class AgentChordMetrics:
    """Collects metrics for AgentChord operations.

    Tracks:
    - agent_runs: Counter of agent executions
    - agent_duration: Histogram of execution time
    - tokens_used: Counter of tokens consumed
    - cost_total: Counter of estimated USD cost
    - errors: Counter of errors by type
    """

    def __init__(self, meter_name: str = "agentchord") -> None:
        self._enabled = HAS_OTEL
        if not self._enabled:
            return

        meter = metrics.get_meter(meter_name)

        self._agent_runs = meter.create_counter(
            "agentchord.agent.runs",
            description="Total number of agent runs",
            unit="1",
        )
        self._agent_duration = meter.create_histogram(
            "agentchord.agent.duration",
            description="Agent execution duration",
            unit="ms",
        )
        self._tokens_used = meter.create_counter(
            "agentchord.tokens.used",
            description="Total tokens consumed",
            unit="1",
        )
        self._cost_total = meter.create_counter(
            "agentchord.cost.total",
            description="Total estimated cost",
            unit="USD",
        )
        self._errors = meter.create_counter(
            "agentchord.errors",
            description="Total errors by type",
            unit="1",
        )

    def record_agent_run(
        self,
        agent_name: str,
        model: str,
        duration_ms: int,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float,
    ) -> None:
        """Record metrics for an agent run."""
        if not self._enabled:
            return

        attrs = {"agent_name": agent_name, "model": model}
        self._agent_runs.add(1, attrs)
        self._agent_duration.record(duration_ms, attrs)
        self._tokens_used.add(prompt_tokens + completion_tokens, attrs)
        self._cost_total.add(cost, attrs)

    def record_error(self, agent_name: str, error_type: str) -> None:
        """Record an error occurrence."""
        if not self._enabled:
            return
        self._errors.add(1, {"agent_name": agent_name, "error_type": error_type})
