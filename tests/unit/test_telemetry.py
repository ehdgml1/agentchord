"""Unit tests for AgentChord telemetry module."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from agentchord.telemetry import AgentChordTracer, AgentChordMetrics, setup_telemetry, get_tracer
from agentchord.telemetry.tracer import (
    _NoOpSpan,
    ATTR_AGENT_NAME,
    ATTR_AGENT_ROLE,
    ATTR_AGENT_MODEL,
    ATTR_PROVIDER,
    ATTR_TOOL_NAME,
    ATTR_TOOL_SUCCESS,
    ATTR_WORKFLOW_NAME,
    ATTR_WORKFLOW_FLOW,
    ATTR_TOKENS_PROMPT,
    ATTR_TOKENS_COMPLETION,
    ATTR_TOKENS_TOTAL,
    ATTR_COST_USD,
    ATTR_DURATION_MS,
    ATTR_TOOL_ROUNDS,
)

# Try to import OpenTelemetry components
try:
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from opentelemetry.trace import StatusCode
    HAS_OTEL = True
except ImportError:
    HAS_OTEL = False


class TestNoOpSpan:
    """Tests for _NoOpSpan class."""

    def test_set_attribute_no_error(self) -> None:
        """set_attribute should not raise when called."""
        span = _NoOpSpan()
        span.set_attribute("key", "value")  # Should not raise

    def test_set_status_no_error(self) -> None:
        """set_status should not raise when called."""
        span = _NoOpSpan()
        span.set_status("OK", "description")  # Should not raise

    def test_record_exception_no_error(self) -> None:
        """record_exception should not raise when called."""
        span = _NoOpSpan()
        exception = ValueError("test error")
        span.record_exception(exception)  # Should not raise

    def test_add_event_no_error(self) -> None:
        """add_event should not raise when called."""
        span = _NoOpSpan()
        span.add_event("event_name", {"attr": "value"})  # Should not raise


class TestSemanticAttributes:
    """Tests for semantic attribute constants."""

    def test_attribute_constants_exist(self) -> None:
        """All semantic attribute constants should be defined."""
        assert ATTR_AGENT_NAME == "agentchord.agent.name"
        assert ATTR_AGENT_ROLE == "agentchord.agent.role"
        assert ATTR_AGENT_MODEL == "agentchord.agent.model"
        assert ATTR_PROVIDER == "agentchord.provider"
        assert ATTR_TOOL_NAME == "agentchord.tool.name"
        assert ATTR_TOOL_SUCCESS == "agentchord.tool.success"
        assert ATTR_WORKFLOW_NAME == "agentchord.workflow.name"
        assert ATTR_WORKFLOW_FLOW == "agentchord.workflow.flow"
        assert ATTR_TOKENS_PROMPT == "agentchord.tokens.prompt"
        assert ATTR_TOKENS_COMPLETION == "agentchord.tokens.completion"
        assert ATTR_TOKENS_TOTAL == "agentchord.tokens.total"
        assert ATTR_COST_USD == "agentchord.cost.usd"
        assert ATTR_DURATION_MS == "agentchord.duration_ms"
        assert ATTR_TOOL_ROUNDS == "agentchord.tool_rounds"


class TestAgentChordTracerWithoutOTEL:
    """Tests for AgentChordTracer when OpenTelemetry is not available."""

    @patch("agentchord.telemetry.tracer.HAS_OTEL", False)
    def test_tracer_disabled_when_otel_unavailable(self) -> None:
        """tracer.enabled should return False when OTEL not installed."""
        tracer = AgentChordTracer()
        assert tracer.enabled is False

    @patch("agentchord.telemetry.tracer.HAS_OTEL", False)
    def test_agent_span_yields_noop_span(self) -> None:
        """agent_span should yield _NoOpSpan when OTEL disabled."""
        tracer = AgentChordTracer()
        with tracer.agent_span("test-agent", model="gpt-4o") as span:
            assert isinstance(span, _NoOpSpan)

    @patch("agentchord.telemetry.tracer.HAS_OTEL", False)
    def test_workflow_span_yields_noop_span(self) -> None:
        """workflow_span should yield _NoOpSpan when OTEL disabled."""
        tracer = AgentChordTracer()
        with tracer.workflow_span("test-workflow", flow="sequential") as span:
            assert isinstance(span, _NoOpSpan)

    @patch("agentchord.telemetry.tracer.HAS_OTEL", False)
    def test_llm_span_yields_noop_span(self) -> None:
        """llm_span should yield _NoOpSpan when OTEL disabled."""
        tracer = AgentChordTracer()
        with tracer.llm_span("gpt-4o", provider="openai") as span:
            assert isinstance(span, _NoOpSpan)

    @patch("agentchord.telemetry.tracer.HAS_OTEL", False)
    def test_tool_span_yields_noop_span(self) -> None:
        """tool_span should yield _NoOpSpan when OTEL disabled."""
        tracer = AgentChordTracer()
        with tracer.tool_span("calculator") as span:
            assert isinstance(span, _NoOpSpan)

    @patch("agentchord.telemetry.tracer.HAS_OTEL", False)
    def test_all_spans_dont_raise_on_error(self) -> None:
        """All span types should handle exceptions gracefully when disabled."""
        tracer = AgentChordTracer()

        # Should not raise, just propagate the original exception
        with pytest.raises(ValueError):
            with tracer.agent_span("test") as span:
                raise ValueError("test error")

        with pytest.raises(ValueError):
            with tracer.workflow_span("test") as span:
                raise ValueError("test error")

        with pytest.raises(ValueError):
            with tracer.llm_span("test") as span:
                raise ValueError("test error")

        with pytest.raises(ValueError):
            with tracer.tool_span("test") as span:
                raise ValueError("test error")


@pytest.mark.skipif(not HAS_OTEL, reason="OpenTelemetry not installed")
class TestAgentChordTracerWithOTEL:
    """Tests for AgentChordTracer when OpenTelemetry is available.

    Note: These tests share a global exporter due to OTEL's singleton pattern.
    """

    @pytest.fixture(scope="class")
    def shared_exporter(self) -> "InMemorySpanExporter":
        """Create a shared exporter for all tests in this class."""
        return InMemorySpanExporter()

    @pytest.fixture(scope="class")
    def shared_tracer(self, shared_exporter: "InMemorySpanExporter") -> AgentChordTracer:
        """Create a shared tracer for all tests in this class."""
        # Reset module-level tracer first
        import agentchord.telemetry.tracer as tracer_module
        tracer_module._tracer = None
        return setup_telemetry(service_name="test-telemetry", exporter=shared_exporter)

    def test_tracer_enabled_when_otel_available(self, shared_tracer: AgentChordTracer) -> None:
        """tracer.enabled should return True when OTEL installed."""
        assert shared_tracer.enabled is True

    def test_agent_span_creates_span_with_attributes(
        self, shared_tracer: AgentChordTracer, shared_exporter: "InMemorySpanExporter"
    ) -> None:
        """agent_span should create span with correct attributes."""
        initial_count = len(shared_exporter.get_finished_spans())

        with shared_tracer.agent_span(
            "test-agent",
            model="gpt-4o",
            role="researcher",
            provider="openai",
        ) as span:
            assert span is not None

        # Check the newly created span
        spans = shared_exporter.get_finished_spans()
        assert len(spans) > initial_count
        span_data = spans[-1]  # Get the last span
        assert span_data.name == "agent.test-agent"
        assert span_data.attributes[ATTR_AGENT_NAME] == "test-agent"
        assert span_data.attributes[ATTR_AGENT_MODEL] == "gpt-4o"
        assert span_data.attributes[ATTR_AGENT_ROLE] == "researcher"
        assert span_data.attributes[ATTR_PROVIDER] == "openai"

    def test_workflow_span_creates_span_with_attributes(
        self, shared_tracer: AgentChordTracer, shared_exporter: "InMemorySpanExporter"
    ) -> None:
        """workflow_span should create span with correct attributes."""
        initial_count = len(shared_exporter.get_finished_spans())

        with shared_tracer.workflow_span(
            "research-pipeline",
            flow="sequential",
            agent_count=3,
        ) as span:
            assert span is not None

        spans = shared_exporter.get_finished_spans()
        assert len(spans) > initial_count
        span_data = spans[-1]
        assert span_data.name == "workflow.research-pipeline"
        assert span_data.attributes[ATTR_WORKFLOW_NAME] == "research-pipeline"
        assert span_data.attributes[ATTR_WORKFLOW_FLOW] == "sequential"
        assert span_data.attributes["agentchord.workflow.agent_count"] == 3

    def test_llm_span_creates_span_with_attributes(
        self, shared_tracer: AgentChordTracer, shared_exporter: "InMemorySpanExporter"
    ) -> None:
        """llm_span should create span with correct attributes."""
        initial_count = len(shared_exporter.get_finished_spans())

        with shared_tracer.llm_span("gpt-4o", provider="openai") as span:
            assert span is not None

        spans = shared_exporter.get_finished_spans()
        assert len(spans) > initial_count
        span_data = spans[-1]
        assert span_data.name == "llm.openai.gpt-4o"
        assert span_data.attributes[ATTR_AGENT_MODEL] == "gpt-4o"
        assert span_data.attributes[ATTR_PROVIDER] == "openai"

    def test_tool_span_creates_span_with_attributes(
        self, shared_tracer: AgentChordTracer, shared_exporter: "InMemorySpanExporter"
    ) -> None:
        """tool_span should create span with correct attributes."""
        initial_count = len(shared_exporter.get_finished_spans())

        with shared_tracer.tool_span("calculator") as span:
            assert span is not None

        spans = shared_exporter.get_finished_spans()
        assert len(spans) > initial_count
        span_data = spans[-1]
        assert span_data.name == "tool.calculator"
        assert span_data.attributes[ATTR_TOOL_NAME] == "calculator"

    def test_span_records_exception_on_error(
        self, shared_tracer: AgentChordTracer, shared_exporter: "InMemorySpanExporter"
    ) -> None:
        """Span should record exception when error occurs."""
        initial_count = len(shared_exporter.get_finished_spans())

        error_msg = "Test error"
        with pytest.raises(ValueError):
            with shared_tracer.agent_span("test-agent-error") as span:
                raise ValueError(error_msg)

        spans = shared_exporter.get_finished_spans()
        assert len(spans) > initial_count
        span_data = spans[-1]
        assert span_data.status.status_code == StatusCode.ERROR
        assert error_msg in span_data.status.description

        # Check that exception event was recorded
        events = span_data.events
        assert len(events) > 0
        assert events[0].name == "exception"

    def test_nested_spans_work(
        self, shared_tracer: AgentChordTracer, shared_exporter: "InMemorySpanExporter"
    ) -> None:
        """Nested spans should work correctly (agent_span containing llm_span)."""
        initial_count = len(shared_exporter.get_finished_spans())

        with shared_tracer.agent_span("test-agent-nested", model="gpt-4o"):
            with shared_tracer.llm_span("gpt-4o", provider="openai"):
                pass

        spans = shared_exporter.get_finished_spans()
        new_spans = spans[initial_count:]
        assert len(new_spans) == 2

        # Find parent and child
        agent_span = next(s for s in new_spans if "test-agent-nested" in s.name)
        llm_span = next(s for s in new_spans if s.name == "llm.openai.gpt-4o")

        # Child should reference parent
        assert llm_span.parent is not None
        assert llm_span.parent.span_id == agent_span.context.span_id

    def test_span_can_set_custom_attributes(
        self, shared_tracer: AgentChordTracer, shared_exporter: "InMemorySpanExporter"
    ) -> None:
        """Span should allow setting custom attributes."""
        initial_count = len(shared_exporter.get_finished_spans())

        with shared_tracer.agent_span("test-agent-attrs") as span:
            span.set_attribute("custom.attr", "value")
            span.set_attribute(ATTR_TOKENS_TOTAL, 150)

        spans = shared_exporter.get_finished_spans()
        span_data = spans[-1]
        assert span_data.attributes["custom.attr"] == "value"
        assert span_data.attributes[ATTR_TOKENS_TOTAL] == 150


class TestAgentChordMetricsWithoutOTEL:
    """Tests for AgentChordMetrics when OpenTelemetry is not available."""

    @patch("agentchord.telemetry.metrics.HAS_OTEL", False)
    def test_record_agent_run_doesnt_raise(self) -> None:
        """record_agent_run should not raise when OTEL disabled."""
        metrics = AgentChordMetrics()
        metrics.record_agent_run(
            agent_name="test",
            model="gpt-4o",
            duration_ms=100,
            prompt_tokens=10,
            completion_tokens=20,
            cost=0.001,
        )  # Should not raise

    @patch("agentchord.telemetry.metrics.HAS_OTEL", False)
    def test_record_error_doesnt_raise(self) -> None:
        """record_error should not raise when OTEL disabled."""
        metrics = AgentChordMetrics()
        metrics.record_error(
            agent_name="test",
            error_type="ValueError",
        )  # Should not raise


@pytest.mark.skipif(not HAS_OTEL, reason="OpenTelemetry not installed")
class TestAgentChordMetricsWithOTEL:
    """Tests for AgentChordMetrics when OpenTelemetry is available."""

    def test_record_agent_run_tracks_metrics(self) -> None:
        """record_agent_run should track all metrics."""
        # Create a mock meter to capture calls
        with patch("agentchord.telemetry.metrics.metrics.get_meter") as mock_get_meter:
            # Set up mock meter and counters/histograms
            mock_meter = MagicMock()
            mock_get_meter.return_value = mock_meter

            mock_runs_counter = MagicMock()
            mock_duration_histogram = MagicMock()
            mock_tokens_counter = MagicMock()
            mock_cost_counter = MagicMock()

            mock_meter.create_counter.side_effect = [
                mock_runs_counter,
                mock_tokens_counter,
                mock_cost_counter,
                MagicMock(),  # errors counter
            ]
            mock_meter.create_histogram.return_value = mock_duration_histogram

            metrics = AgentChordMetrics()

            # Record a run
            metrics.record_agent_run(
                agent_name="test-agent",
                model="gpt-4o",
                duration_ms=150,
                prompt_tokens=100,
                completion_tokens=50,
                cost=0.005,
            )

            # Verify metrics were recorded
            mock_runs_counter.add.assert_called_once()
            mock_duration_histogram.record.assert_called_once()
            mock_tokens_counter.add.assert_called_once()
            mock_cost_counter.add.assert_called_once()

            # Check values
            runs_call = mock_runs_counter.add.call_args
            assert runs_call[0][0] == 1  # count
            assert runs_call[0][1] == {"agent_name": "test-agent", "model": "gpt-4o"}

            duration_call = mock_duration_histogram.record.call_args
            assert duration_call[0][0] == 150
            assert duration_call[0][1] == {"agent_name": "test-agent", "model": "gpt-4o"}

            tokens_call = mock_tokens_counter.add.call_args
            assert tokens_call[0][0] == 150  # 100 + 50
            assert tokens_call[0][1] == {"agent_name": "test-agent", "model": "gpt-4o"}

            cost_call = mock_cost_counter.add.call_args
            assert cost_call[0][0] == 0.005
            assert cost_call[0][1] == {"agent_name": "test-agent", "model": "gpt-4o"}

    def test_record_error_tracks_errors(self) -> None:
        """record_error should track error metrics."""
        with patch("agentchord.telemetry.metrics.metrics.get_meter") as mock_get_meter:
            mock_meter = MagicMock()
            mock_get_meter.return_value = mock_meter

            mock_errors_counter = MagicMock()
            mock_meter.create_counter.side_effect = [
                MagicMock(),  # runs
                MagicMock(),  # tokens
                MagicMock(),  # cost
                mock_errors_counter,  # errors
            ]
            mock_meter.create_histogram.return_value = MagicMock()

            metrics = AgentChordMetrics()

            metrics.record_error(
                agent_name="test-agent",
                error_type="ValueError",
            )

            mock_errors_counter.add.assert_called_once()
            call = mock_errors_counter.add.call_args
            assert call[0][0] == 1
            assert call[0][1] == {"agent_name": "test-agent", "error_type": "ValueError"}


class TestSetupTelemetry:
    """Tests for setup_telemetry function."""

    @patch("agentchord.telemetry.tracer.HAS_OTEL", False)
    def test_setup_raises_import_error_when_otel_unavailable(self) -> None:
        """setup_telemetry should raise ImportError when OTEL not installed."""
        with pytest.raises(ImportError) as exc_info:
            setup_telemetry()

        assert "OpenTelemetry packages not installed" in str(exc_info.value)
        assert "pip install agentchord[telemetry]" in str(exc_info.value)

    @pytest.mark.skipif(not HAS_OTEL, reason="OpenTelemetry not installed")
    def test_setup_returns_tracer(self) -> None:
        """setup_telemetry should return AgentChordTracer instance."""
        # Don't call setup_telemetry here since it may have been called in other tests
        # Just verify the return type
        import agentchord.telemetry.tracer as tracer_module
        tracer_module._tracer = None
        tracer = setup_telemetry(service_name="test-service")
        assert isinstance(tracer, AgentChordTracer)
        assert tracer.enabled is True


class TestGetTracer:
    """Tests for get_tracer function."""

    def test_get_tracer_returns_tracer(self) -> None:
        """get_tracer should return AgentChordTracer."""
        tracer = get_tracer()
        assert isinstance(tracer, AgentChordTracer)

    def test_get_tracer_returns_singleton(self) -> None:
        """get_tracer should return the same instance on multiple calls."""
        tracer1 = get_tracer()
        tracer2 = get_tracer()
        assert tracer1 is tracer2

    @pytest.mark.skipif(not HAS_OTEL, reason="OpenTelemetry not installed")
    def test_get_tracer_after_setup(self) -> None:
        """get_tracer should return the tracer set by setup_telemetry."""
        import agentchord.telemetry.tracer as tracer_module
        # Reset and set up fresh
        tracer_module._tracer = None
        exporter = InMemorySpanExporter()
        setup_tracer = setup_telemetry(service_name="test-gettracer", exporter=exporter)
        get_tracer_result = get_tracer()
        assert get_tracer_result is setup_tracer
