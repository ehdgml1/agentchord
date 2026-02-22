"""AgentChord OpenTelemetry tracer.

Provides tracing instrumentation for agents, workflows, tools, and LLM calls.
Falls back to no-op if OpenTelemetry is not installed.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.trace import StatusCode, Span
    HAS_OTEL = True
except ImportError:
    HAS_OTEL = False

# Semantic convention attribute names
ATTR_AGENT_NAME = "agentchord.agent.name"
ATTR_AGENT_ROLE = "agentchord.agent.role"
ATTR_AGENT_MODEL = "agentchord.agent.model"
ATTR_PROVIDER = "agentchord.provider"
ATTR_TOOL_NAME = "agentchord.tool.name"
ATTR_TOOL_SUCCESS = "agentchord.tool.success"
ATTR_WORKFLOW_NAME = "agentchord.workflow.name"
ATTR_WORKFLOW_FLOW = "agentchord.workflow.flow"
ATTR_TOKENS_PROMPT = "agentchord.tokens.prompt"
ATTR_TOKENS_COMPLETION = "agentchord.tokens.completion"
ATTR_TOKENS_TOTAL = "agentchord.tokens.total"
ATTR_COST_USD = "agentchord.cost.usd"
ATTR_DURATION_MS = "agentchord.duration_ms"
ATTR_TOOL_ROUNDS = "agentchord.tool_rounds"


class AgentChordTracer:
    """OpenTelemetry tracer for AgentChord operations.

    Provides context managers for creating spans around agent, workflow,
    LLM, and tool operations. Falls back to no-op if OTEL not installed.

    Example:
        >>> tracer = AgentChordTracer()
        >>> with tracer.agent_span("researcher", model="gpt-4o") as span:
        ...     # agent execution here
        ...     span.set_attribute("agentchord.tokens.total", 150)
    """

    def __init__(self, service_name: str = "agentchord") -> None:
        self._enabled = HAS_OTEL
        self._service_name = service_name
        self._tracer = None
        if self._enabled:
            self._tracer = trace.get_tracer(
                "agentchord",
                schema_url="https://agentchord.dev/schema",
            )

    @property
    def enabled(self) -> bool:
        """Whether OpenTelemetry is available and tracing is active."""
        return self._enabled

    @contextmanager
    def agent_span(
        self,
        agent_name: str,
        *,
        model: str = "",
        role: str = "",
        provider: str = "",
    ) -> Iterator[Any]:
        """Create a span for an agent execution.

        Args:
            agent_name: Name of the agent.
            model: LLM model being used.
            role: Agent's role description.
            provider: LLM provider name.
        """
        if not self._enabled or not self._tracer:
            yield _NoOpSpan()
            return

        with self._tracer.start_as_current_span(
            f"agent.{agent_name}",
            attributes={
                ATTR_AGENT_NAME: agent_name,
                ATTR_AGENT_MODEL: model,
                ATTR_AGENT_ROLE: role,
                ATTR_PROVIDER: provider,
            },
        ) as span:
            try:
                yield span
            except Exception as e:
                span.set_status(StatusCode.ERROR, str(e))
                span.record_exception(e)
                raise

    @contextmanager
    def workflow_span(
        self,
        workflow_name: str,
        *,
        flow: str = "",
        agent_count: int = 0,
    ) -> Iterator[Any]:
        """Create a span for a workflow execution."""
        if not self._enabled or not self._tracer:
            yield _NoOpSpan()
            return

        with self._tracer.start_as_current_span(
            f"workflow.{workflow_name}",
            attributes={
                ATTR_WORKFLOW_NAME: workflow_name,
                ATTR_WORKFLOW_FLOW: flow,
                "agentchord.workflow.agent_count": agent_count,
            },
        ) as span:
            try:
                yield span
            except Exception as e:
                span.set_status(StatusCode.ERROR, str(e))
                span.record_exception(e)
                raise

    @contextmanager
    def llm_span(
        self,
        model: str,
        *,
        provider: str = "",
    ) -> Iterator[Any]:
        """Create a span for an LLM API call."""
        if not self._enabled or not self._tracer:
            yield _NoOpSpan()
            return

        with self._tracer.start_as_current_span(
            f"llm.{provider or 'unknown'}.{model}",
            attributes={
                ATTR_AGENT_MODEL: model,
                ATTR_PROVIDER: provider,
            },
        ) as span:
            try:
                yield span
            except Exception as e:
                span.set_status(StatusCode.ERROR, str(e))
                span.record_exception(e)
                raise

    @contextmanager
    def tool_span(self, tool_name: str) -> Iterator[Any]:
        """Create a span for a tool execution."""
        if not self._enabled or not self._tracer:
            yield _NoOpSpan()
            return

        with self._tracer.start_as_current_span(
            f"tool.{tool_name}",
            attributes={ATTR_TOOL_NAME: tool_name},
        ) as span:
            try:
                yield span
            except Exception as e:
                span.set_status(StatusCode.ERROR, str(e))
                span.record_exception(e)
                raise


class _NoOpSpan:
    """No-op span for when OpenTelemetry is not installed."""

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def set_status(self, status: Any, description: str = "") -> None:
        pass

    def record_exception(self, exception: Exception) -> None:
        pass

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        pass


# Module-level singleton
_tracer: AgentChordTracer | None = None


def setup_telemetry(
    service_name: str = "agentchord",
    exporter: Any = None,
) -> AgentChordTracer:
    """Set up OpenTelemetry tracing for AgentChord.

    Args:
        service_name: Service name for the tracer.
        exporter: Optional SpanExporter. If not provided, uses default.

    Returns:
        Configured AgentChordTracer instance.

    Raises:
        ImportError: If opentelemetry packages are not installed.
    """
    global _tracer

    if not HAS_OTEL:
        raise ImportError(
            "OpenTelemetry packages not installed. "
            "Install with: pip install agentchord[telemetry]"
        )

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    if exporter:
        provider.add_span_processor(SimpleSpanProcessor(exporter))

    trace.set_tracer_provider(provider)

    _tracer = AgentChordTracer(service_name=service_name)
    return _tracer


def get_tracer() -> AgentChordTracer:
    """Get the current tracer (creates a default if needed)."""
    global _tracer
    if _tracer is None:
        _tracer = AgentChordTracer()
    return _tracer
