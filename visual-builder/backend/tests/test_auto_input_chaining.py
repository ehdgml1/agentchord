"""Tests for automatic input chaining between connected nodes."""
import pytest
import pytest_asyncio
from app.core.executor import WorkflowNode, WorkflowEdge


class TestAutoInputChaining:
    """Tests for _resolve_input with edge-based auto-chaining."""

    def test_single_upstream_node(self, executor):
        """Agent2 automatically receives Agent1's output via edge."""
        node = WorkflowNode(id="agent2", type="agent", data={})
        context = {
            "input": "original user input",
            "agent1": "Agent1's processed output",
        }
        edges = [WorkflowEdge(id="e1", source="agent1", target="agent2")]
        executor._current_edges = edges

        result = executor._resolve_input(node, context)
        assert result == "Agent1's processed output"

    def test_multiple_upstream_nodes(self, executor):
        """Node receives concatenated outputs from multiple parents."""
        node = WorkflowNode(id="merger", type="agent", data={})
        context = {
            "input": "original",
            "agent1": "Output from agent1",
            "agent2": "Output from agent2",
        }
        edges = [
            WorkflowEdge(id="e1", source="agent1", target="merger"),
            WorkflowEdge(id="e2", source="agent2", target="merger"),
        ]
        executor._current_edges = edges

        result = executor._resolve_input(node, context)
        assert "Output from agent1" in result
        assert "Output from agent2" in result

    def test_no_edges_fallback_to_input(self, executor):
        """Without edges, falls back to context input."""
        node = WorkflowNode(id="agent1", type="agent", data={})
        context = {"input": "user message"}
        executor._current_edges = []

        result = executor._resolve_input(node, context)
        assert result == "user message"

    def test_explicit_input_source_takes_priority(self, executor):
        """Explicit inputSource overrides edge auto-detection."""
        node = WorkflowNode(id="agent2", type="agent", data={"inputSource": "custom_key"})
        context = {
            "input": "original",
            "agent1": "from edge",
            "custom_key": "from explicit source",
        }
        edges = [WorkflowEdge(id="e1", source="agent1", target="agent2")]
        executor._current_edges = edges

        result = executor._resolve_input(node, context)
        assert result == "from explicit source"

    def test_explicit_input_template_takes_priority(self, executor):
        """Explicit inputTemplate overrides edge auto-detection."""
        node = WorkflowNode(id="agent2", type="agent", data={"inputTemplate": "Custom: {{agent1}}"})
        context = {
            "input": "original",
            "agent1": "agent1 output",
        }
        edges = [WorkflowEdge(id="e1", source="agent1", target="agent2")]
        executor._current_edges = edges

        result = executor._resolve_input(node, context)
        assert result == "Custom: agent1 output"

    def test_upstream_dict_output_extracts_output_field(self, executor):
        """When upstream output is a dict, extract the 'output' field."""
        node = WorkflowNode(id="agent2", type="agent", data={})
        context = {
            "input": "original",
            "agent1": {"output": "extracted value", "metadata": "ignored"},
        }
        edges = [WorkflowEdge(id="e1", source="agent1", target="agent2")]
        executor._current_edges = edges

        result = executor._resolve_input(node, context)
        assert result == "extracted value"

    def test_first_node_gets_user_input(self, executor):
        """First node (no incoming edges) gets original user input."""
        node = WorkflowNode(id="agent1", type="agent", data={})
        context = {"input": "user message"}
        edges = [WorkflowEdge(id="e1", source="agent1", target="agent2")]
        executor._current_edges = edges

        result = executor._resolve_input(node, context)
        assert result == "user message"

    def test_no_current_edges_attribute(self, executor):
        """Works when _current_edges is not set (backward compat)."""
        node = WorkflowNode(id="agent1", type="agent", data={})
        context = {"input": "user message"}
        # Don't set _current_edges at all

        result = executor._resolve_input(node, context)
        assert result == "user message"

    def test_upstream_dict_without_output_field(self, executor):
        """When upstream output is dict without 'output', stringify the dict."""
        node = WorkflowNode(id="agent2", type="agent", data={})
        context = {
            "input": "original",
            "agent1": {"result": "value", "status": "ok"},
        }
        edges = [WorkflowEdge(id="e1", source="agent1", target="agent2")]
        executor._current_edges = edges

        result = executor._resolve_input(node, context)
        # Should stringify the dict
        assert "result" in result
        assert "value" in result
        assert "status" in result

    def test_upstream_none_value_skipped(self, executor):
        """None values from upstream nodes are skipped."""
        node = WorkflowNode(id="agent3", type="agent", data={})
        context = {
            "input": "original",
            "agent1": None,
            "agent2": "valid output",
        }
        edges = [
            WorkflowEdge(id="e1", source="agent1", target="agent3"),
            WorkflowEdge(id="e2", source="agent2", target="agent3"),
        ]
        executor._current_edges = edges

        result = executor._resolve_input(node, context)
        assert result == "valid output"
        assert "None" not in result

    def test_multiple_upstream_concatenation_order(self, executor):
        """Multiple upstream outputs are concatenated with newlines."""
        node = WorkflowNode(id="merger", type="agent", data={})
        context = {
            "input": "original",
            "agent1": "First output",
            "agent2": "Second output",
            "agent3": "Third output",
        }
        edges = [
            WorkflowEdge(id="e1", source="agent1", target="merger"),
            WorkflowEdge(id="e2", source="agent2", target="merger"),
            WorkflowEdge(id="e3", source="agent3", target="merger"),
        ]
        executor._current_edges = edges

        result = executor._resolve_input(node, context)
        # Should have all three with double newlines between
        assert "First output" in result
        assert "Second output" in result
        assert "Third output" in result
        # Check separator
        assert "\n\n" in result

    def test_upstream_node_not_in_context_yet(self, executor):
        """Upstream nodes not yet executed (not in context) are skipped."""
        node = WorkflowNode(id="agent2", type="agent", data={})
        context = {
            "input": "original user input",
            # agent1 not yet executed, not in context
        }
        edges = [WorkflowEdge(id="e1", source="agent1", target="agent2")]
        executor._current_edges = edges

        result = executor._resolve_input(node, context)
        # Should fall back to input
        assert result == "original user input"

    def test_template_resolution_still_works_on_auto_chained_input(self, executor):
        """Template resolution works on auto-chained input."""
        node = WorkflowNode(id="agent2", type="agent", data={})
        context = {
            "input": "original",
            "agent1": "The answer is {{agent0}}",
            "agent0": "42",
        }
        edges = [WorkflowEdge(id="e1", source="agent1", target="agent2")]
        executor._current_edges = edges

        result = executor._resolve_input(node, context)
        # Should auto-chain agent1's output AND resolve template
        assert result == "The answer is 42"
