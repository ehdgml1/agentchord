"""AgentWeave OpenTelemetry tracer.

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
ATTR_AGENT_NAME = "agentweave.agent.name"
ATTR_AGENT_ROLE = "agentweave.agent.role"
ATTR_AGENT_MODEL = "agentweave.agent.model"
ATTR_PROVIDER = "agentweave.provider"
ATTR_TOOL_NAME = "agentweave.tool.name"
ATTR_TOOL_SUCCESS = "agentweave.tool.success"
ATTR_WORKFLOW_NAME = "agentweave.workflow.name"
ATTR_WORKFLOW_FLOW = "agentweave.workflow.flow"
ATTR_TOKENS_PROMPT = "agentweave.tokens.prompt"
ATTR_TOKENS_COMPLETION = "agentweave.tokens.completion"
ATTR_TOKENS_TOTAL = "agentweave.tokens.total"
ATTR_COST_USD = "agentweave.cost.usd"
ATTR_DURATION_MS = "agentweave.duration_ms"
ATTR_TOOL_ROUNDS = "agentweave.tool_rounds"


class AgentWeaveTracer:
    """OpenTelemetry tracer for AgentWeave operations.

    Provides context managers for creating spans around agent, workflow,
    LLM, and tool operations. Falls back to no-op if OTEL not installed.

    Example:
        >>> tracer = AgentWeaveTracer()
        >>> with tracer.agent_span("researcher", model="gpt-4o") as span:
        ...     # agent execution here
        ...     span.set_attribute("agentweave.tokens.total", 150)
    """

    def __init__(self, service_name: str = "agentweave") -> None:
        self._enabled = HAS_OTEL
        self._service_name = service_name
        self._tracer = None
        if self._enabled:
            self._tracer = trace.get_tracer(
                "agentweave",
                schema_url="https://agentweave.dev/schema",
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
                "agentweave.workflow.agent_count": agent_count,
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
_tracer: AgentWeaveTracer | None = None


def setup_telemetry(
    service_name: str = "agentweave",
    exporter: Any = None,
) -> AgentWeaveTracer:
    """Set up OpenTelemetry tracing for AgentWeave.

    Args:
        service_name: Service name for the tracer.
        exporter: Optional SpanExporter. If not provided, uses default.

    Returns:
        Configured AgentWeaveTracer instance.

    Raises:
        ImportError: If opentelemetry packages are not installed.
    """
    global _tracer

    if not HAS_OTEL:
        raise ImportError(
            "OpenTelemetry packages not installed. "
            "Install with: pip install agentweave[telemetry]"
        )

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    if exporter:
        provider.add_span_processor(SimpleSpanProcessor(exporter))

    trace.set_tracer_provider(provider)

    _tracer = AgentWeaveTracer(service_name=service_name)
    return _tracer


def get_tracer() -> AgentWeaveTracer:
    """Get the current tracer (creates a default if needed)."""
    global _tracer
    if _tracer is None:
        _tracer = AgentWeaveTracer()
    return _tracer
