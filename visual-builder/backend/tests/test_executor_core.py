"""Direct unit tests for executor core logic.

Tests cover:
- _topological_sort (graph sorting, cycle detection)
- Template engine ({{nodeId.output.field}} resolution)
- Condition evaluation (simpleeval-based safe expression evaluation)
- Error fallback edge routing
"""

from __future__ import annotations

import pytest
from datetime import datetime, UTC

from app.core.executor import (
    WorkflowExecutor,
    WorkflowNode,
    WorkflowEdge,
    Workflow,
    ExecutionStatus,
    WorkflowValidationError,
    ExecutionStateStore,
)
from app.core.mcp_manager import MCPManager
from app.core.secret_store import SecretStore


@pytest.fixture
def mock_mcp_manager():
    """Mock MCP manager."""
    return MCPManager()


@pytest.fixture
def mock_secret_store():
    """Mock secret store."""
    class MockDB:
        async def execute(self, *args, **kwargs):
            pass
        async def fetchone(self, *args, **kwargs):
            return None
        async def fetchall(self, *args, **kwargs):
            return []
    return SecretStore(MockDB())


@pytest.fixture
def mock_state_store():
    """Mock state store."""
    class MockDB:
        async def execute(self, *args, **kwargs):
            pass
        async def fetchone(self, *args, **kwargs):
            return None
    return ExecutionStateStore(MockDB())


@pytest.fixture
def executor(mock_mcp_manager, mock_secret_store, mock_state_store):
    """Create executor instance."""
    return WorkflowExecutor(
        mcp_manager=mock_mcp_manager,
        secret_store=mock_secret_store,
        state_store=mock_state_store,
    )


# =============================================================================
# Topological Sort Tests
# =============================================================================

def test_topological_sort_linear_graph(executor):
    """Test simple linear graph A→B→C."""
    nodes = [
        WorkflowNode(id="A", type="agent", data={}),
        WorkflowNode(id="B", type="agent", data={}),
        WorkflowNode(id="C", type="agent", data={}),
    ]
    edges = [
        WorkflowEdge(id="e1", source="A", target="B"),
        WorkflowEdge(id="e2", source="B", target="C"),
    ]
    workflow = Workflow(id="w1", name="linear", nodes=nodes, edges=edges)

    result = executor._topological_sort(workflow)
    result_ids = [n.id for n in result]

    assert result_ids == ["A", "B", "C"]


def test_topological_sort_diamond_graph(executor):
    """Test diamond graph: A→B,C; B→D; C→D."""
    nodes = [
        WorkflowNode(id="A", type="agent", data={}),
        WorkflowNode(id="B", type="agent", data={}),
        WorkflowNode(id="C", type="agent", data={}),
        WorkflowNode(id="D", type="agent", data={}),
    ]
    edges = [
        WorkflowEdge(id="e1", source="A", target="B"),
        WorkflowEdge(id="e2", source="A", target="C"),
        WorkflowEdge(id="e3", source="B", target="D"),
        WorkflowEdge(id="e4", source="C", target="D"),
    ]
    workflow = Workflow(id="w1", name="diamond", nodes=nodes, edges=edges)

    result = executor._topological_sort(workflow)
    result_ids = [n.id for n in result]

    # A must be first, D must be last
    assert result_ids[0] == "A"
    assert result_ids[-1] == "D"
    # B and C can be in either order
    assert set(result_ids[1:3]) == {"B", "C"}


def test_topological_sort_disconnected_nodes(executor):
    """Test graph with disconnected nodes."""
    nodes = [
        WorkflowNode(id="A", type="agent", data={}),
        WorkflowNode(id="B", type="agent", data={}),
        WorkflowNode(id="C", type="agent", data={}),
    ]
    edges = [
        WorkflowEdge(id="e1", source="A", target="B"),
        # C is disconnected
    ]
    workflow = Workflow(id="w1", name="disconnected", nodes=nodes, edges=edges)

    result = executor._topological_sort(workflow)
    result_ids = [n.id for n in result]

    # All nodes should be present
    assert set(result_ids) == {"A", "B", "C"}


def test_topological_sort_single_node(executor):
    """Test graph with single node, no edges."""
    nodes = [WorkflowNode(id="A", type="agent", data={})]
    edges = []
    workflow = Workflow(id="w1", name="single", nodes=nodes, edges=edges)

    result = executor._topological_sort(workflow)
    result_ids = [n.id for n in result]

    assert result_ids == ["A"]


def test_topological_sort_complex_fan_out_fan_in(executor):
    """Test complex fan-out/fan-in graph."""
    nodes = [
        WorkflowNode(id="start", type="agent", data={}),
        WorkflowNode(id="b1", type="agent", data={}),
        WorkflowNode(id="b2", type="agent", data={}),
        WorkflowNode(id="b3", type="agent", data={}),
        WorkflowNode(id="merge", type="agent", data={}),
        WorkflowNode(id="end", type="agent", data={}),
    ]
    edges = [
        WorkflowEdge(id="e1", source="start", target="b1"),
        WorkflowEdge(id="e2", source="start", target="b2"),
        WorkflowEdge(id="e3", source="start", target="b3"),
        WorkflowEdge(id="e4", source="b1", target="merge"),
        WorkflowEdge(id="e5", source="b2", target="merge"),
        WorkflowEdge(id="e6", source="b3", target="merge"),
        WorkflowEdge(id="e7", source="merge", target="end"),
    ]
    workflow = Workflow(id="w1", name="fan", nodes=nodes, edges=edges)

    result = executor._topological_sort(workflow)
    result_ids = [n.id for n in result]

    # Start must be first
    assert result_ids[0] == "start"
    # End must be last
    assert result_ids[-1] == "end"
    # Merge must be second to last
    assert result_ids[-2] == "merge"
    # b1, b2, b3 can be in any order but before merge
    assert set(result_ids[1:4]) == {"b1", "b2", "b3"}


def test_topological_sort_with_feedback_loop(executor):
    """Test graph with feedback_loop node (allowed cycle)."""
    nodes = [
        WorkflowNode(id="A", type="agent", data={}),
        WorkflowNode(id="B", type="agent", data={}),
        WorkflowNode(id="loop", type="feedback_loop", data={}),
    ]
    edges = [
        WorkflowEdge(id="e1", source="A", target="B"),
        WorkflowEdge(id="e2", source="B", target="loop"),
        WorkflowEdge(id="e3", source="loop", target="B"),  # Back edge
    ]
    workflow = Workflow(id="w1", name="loop", nodes=nodes, edges=edges)

    # Should not raise, feedback loop edges are excluded
    result = executor._topological_sort(workflow)
    result_ids = [n.id for n in result]

    # A should be first
    assert result_ids[0] == "A"
    # B and loop can be in either order (loop's back edge is excluded)
    assert set(result_ids[1:]) == {"B", "loop"}


def test_has_cycle_pure_cycle(executor):
    """Test cycle detection for pure cycles (no feedback_loop)."""
    nodes = [
        WorkflowNode(id="A", type="agent", data={}),
        WorkflowNode(id="B", type="agent", data={}),
        WorkflowNode(id="C", type="agent", data={}),
    ]
    edges = [
        WorkflowEdge(id="e1", source="A", target="B"),
        WorkflowEdge(id="e2", source="B", target="C"),
        WorkflowEdge(id="e3", source="C", target="A"),  # Cycle back
    ]
    workflow = Workflow(id="w1", name="cycle", nodes=nodes, edges=edges)

    assert executor._has_cycle(workflow) is True


def test_has_cycle_no_cycle(executor):
    """Test cycle detection for acyclic graph."""
    nodes = [
        WorkflowNode(id="A", type="agent", data={}),
        WorkflowNode(id="B", type="agent", data={}),
        WorkflowNode(id="C", type="agent", data={}),
    ]
    edges = [
        WorkflowEdge(id="e1", source="A", target="B"),
        WorkflowEdge(id="e2", source="B", target="C"),
    ]
    workflow = Workflow(id="w1", name="no_cycle", nodes=nodes, edges=edges)

    assert executor._has_cycle(workflow) is False


def test_has_cycle_with_feedback_loop_allowed(executor):
    """Test that feedback_loop nodes allow cycles."""
    nodes = [
        WorkflowNode(id="A", type="agent", data={}),
        WorkflowNode(id="loop", type="feedback_loop", data={}),
    ]
    edges = [
        WorkflowEdge(id="e1", source="A", target="loop"),
        WorkflowEdge(id="e2", source="loop", target="A"),  # Back edge from feedback_loop
    ]
    workflow = Workflow(id="w1", name="loop", nodes=nodes, edges=edges)

    # Should NOT be considered a cycle because feedback_loop edges are excluded
    assert executor._has_cycle(workflow) is False


# =============================================================================
# Template Engine Tests
# =============================================================================

def test_resolve_template_basic(executor):
    """Test basic template resolution {{nodeId.output}}."""
    context = {
        "node1": {"output": "Hello World"},
    }
    template = "{{node1.output}}"
    result = executor._resolve_template(template, context)
    assert result == "Hello World"


def test_resolve_template_nested_field(executor):
    """Test nested field access {{nodeId.output.field.nested}}."""
    context = {
        "node1": {
            "output": {
                "field": {
                    "nested": "Deep Value"
                }
            }
        },
    }
    template = "{{node1.output.field.nested}}"
    result = executor._resolve_template(template, context)
    assert result == "Deep Value"


def test_resolve_template_missing_node_id(executor):
    """Test template with missing node ID (should leave unresolved)."""
    context = {
        "node1": {"output": "test"},
    }
    template = "{{node2.output}}"
    result = executor._resolve_template(template, context)
    # Should leave template unchanged when node not found
    assert result == "{{node2.output}}"


def test_resolve_template_missing_field(executor):
    """Test template with missing field path."""
    context = {
        "node1": {"output": "test"},
    }
    template = "{{node1.nonexistent.field}}"
    result = executor._resolve_template(template, context)
    # Should leave template unchanged when field path can't be traversed
    assert result == "{{node1.nonexistent.field}}"


def test_resolve_template_multiple_templates(executor):
    """Test multiple templates in one string."""
    context = {
        "node1": {"output": "Hello"},
        "node2": {"result": "World"},
    }
    template = "{{node1.output}} {{node2.result}}!"
    result = executor._resolve_template(template, context)
    assert result == "Hello World!"


def test_resolve_template_no_templates(executor):
    """Test string with no templates (passthrough)."""
    context = {"node1": {"output": "test"}}
    template = "Plain text with no templates"
    result = executor._resolve_template(template, context)
    assert result == "Plain text with no templates"


def test_resolve_template_empty_string(executor):
    """Test empty string template."""
    context = {"node1": {"output": "test"}}
    template = ""
    result = executor._resolve_template(template, context)
    assert result == ""


def test_resolve_template_none_values(executor):
    """Test template with None values in context."""
    context = {
        "node1": None,
    }
    template = "{{node1.output}}"
    result = executor._resolve_template(template, context)
    # Can't traverse None, should leave unresolved
    assert result == "{{node1.output}}"


def test_resolve_template_number_values(executor):
    """Test template with number values."""
    context = {
        "node1": {"count": 42, "price": 19.99},
    }
    template = "Count: {{node1.count}}, Price: {{node1.price}}"
    result = executor._resolve_template(template, context)
    assert result == "Count: 42, Price: 19.99"


def test_resolve_template_list_value(executor):
    """Test template with list value."""
    context = {
        "node1": {"items": ["a", "b", "c"]},
    }
    template = "Items: {{node1.items}}"
    result = executor._resolve_template(template, context)
    assert result == "Items: ['a', 'b', 'c']"


# =============================================================================
# Condition Evaluation Tests (simpleeval)
# =============================================================================

@pytest.mark.asyncio
async def test_run_condition_basic_comparisons(executor):
    """Test basic comparison operators in conditions."""
    node = WorkflowNode(id="cond1", type="condition", data={"condition": "5 > 3"})
    context = {"input": "test"}

    result = await executor._run_condition(node, context)

    assert result["result"] is True
    assert result["active_handle"] == "true"


@pytest.mark.asyncio
async def test_run_condition_equality(executor):
    """Test equality operators."""
    node = WorkflowNode(id="cond1", type="condition", data={"condition": "10 == 10"})
    context = {"input": "test"}

    result = await executor._run_condition(node, context)
    assert result["result"] is True

    node2 = WorkflowNode(id="cond2", type="condition", data={"condition": "10 != 5"})
    result2 = await executor._run_condition(node2, context)
    assert result2["result"] is True


@pytest.mark.asyncio
async def test_run_condition_boolean_operators(executor):
    """Test boolean and/or/not operators."""
    # AND
    node = WorkflowNode(id="cond1", type="condition", data={"condition": "True and True"})
    result = await executor._run_condition(node, {"input": "test"})
    assert result["result"] is True

    # OR
    node2 = WorkflowNode(id="cond2", type="condition", data={"condition": "False or True"})
    result2 = await executor._run_condition(node2, {"input": "test"})
    assert result2["result"] is True

    # NOT
    node3 = WorkflowNode(id="cond3", type="condition", data={"condition": "not False"})
    result3 = await executor._run_condition(node3, {"input": "test"})
    assert result3["result"] is True


@pytest.mark.asyncio
async def test_run_condition_string_operations(executor):
    """Test string operations in conditions."""
    node = WorkflowNode(
        id="cond1",
        type="condition",
        data={"condition": "len('hello') == 5"}
    )
    result = await executor._run_condition(node, {"input": "test"})
    assert result["result"] is True


@pytest.mark.asyncio
async def test_run_condition_context_access(executor):
    """Test accessing context variables in conditions."""
    node = WorkflowNode(
        id="cond1",
        type="condition",
        data={"condition": "context['node1'] == 'success'"}
    )
    context = {"input": "test", "node1": "success"}

    result = await executor._run_condition(node, context)
    assert result["result"] is True


@pytest.mark.asyncio
async def test_run_condition_input_access(executor):
    """Test accessing input variable in conditions."""
    node = WorkflowNode(
        id="cond1",
        type="condition",
        data={"condition": "len(input) > 0"}
    )
    context = {"input": "hello"}

    result = await executor._run_condition(node, context)
    assert result["result"] is True


@pytest.mark.asyncio
async def test_run_condition_malicious_import_blocked(executor):
    """Test that import statements are blocked."""
    node = WorkflowNode(
        id="cond1",
        type="condition",
        data={"condition": "__import__('os').system('ls')"}
    )
    context = {"input": "test"}

    # Should not raise, but return False on invalid expression
    result = await executor._run_condition(node, context)
    assert result["result"] is False


@pytest.mark.asyncio
async def test_run_condition_malicious_exec_blocked(executor):
    """Test that exec/eval are blocked."""
    node = WorkflowNode(
        id="cond1",
        type="condition",
        data={"condition": "exec('print(123)')"}
    )
    context = {"input": "test"}

    result = await executor._run_condition(node, context)
    assert result["result"] is False


@pytest.mark.asyncio
async def test_run_condition_nested_expressions(executor):
    """Test nested expressions."""
    node = WorkflowNode(
        id="cond1",
        type="condition",
        data={"condition": "(5 + 3) * 2 == 16"}
    )
    context = {"input": "test"}

    result = await executor._run_condition(node, context)
    assert result["result"] is True


@pytest.mark.asyncio
async def test_run_condition_safe_functions(executor):
    """Test whitelisted safe functions."""
    # len
    node1 = WorkflowNode(id="c1", type="condition", data={"condition": "len([1,2,3]) == 3"})
    result1 = await executor._run_condition(node1, {"input": "test"})
    assert result1["result"] is True

    # str
    node2 = WorkflowNode(id="c2", type="condition", data={"condition": "str(123) == '123'"})
    result2 = await executor._run_condition(node2, {"input": "test"})
    assert result2["result"] is True

    # int
    node3 = WorkflowNode(id="c3", type="condition", data={"condition": "int('42') == 42"})
    result3 = await executor._run_condition(node3, {"input": "test"})
    assert result3["result"] is True


@pytest.mark.asyncio
async def test_run_condition_false_result(executor):
    """Test condition that evaluates to false."""
    node = WorkflowNode(
        id="cond1",
        type="condition",
        data={"condition": "5 < 3"}
    )
    context = {"input": "test"}

    result = await executor._run_condition(node, context)
    assert result["result"] is False
    assert result["active_handle"] == "false"


@pytest.mark.asyncio
async def test_run_condition_invalid_expression(executor):
    """Test handling of invalid expressions."""
    node = WorkflowNode(
        id="cond1",
        type="condition",
        data={"condition": "invalid syntax here !!!"}
    )
    context = {"input": "test"}

    # Should default to False on error
    result = await executor._run_condition(node, context)
    assert result["result"] is False


# =============================================================================
# Error Fallback Edge Tests
# =============================================================================

def test_find_error_edge_target_exists(executor):
    """Test finding error edge target when it exists."""
    nodes = [
        WorkflowNode(id="A", type="agent", data={}),
        WorkflowNode(id="B", type="agent", data={}),
        WorkflowNode(id="ErrorHandler", type="agent", data={}),
    ]
    edges = [
        WorkflowEdge(id="e1", source="A", target="B"),
        WorkflowEdge(id="e2", source="A", target="ErrorHandler", source_handle="error"),
    ]
    workflow = Workflow(id="w1", name="error", nodes=nodes, edges=edges)

    target = executor._find_error_edge_target("A", workflow)
    assert target == "ErrorHandler"


def test_find_error_edge_target_not_exists(executor):
    """Test finding error edge when none exists."""
    nodes = [
        WorkflowNode(id="A", type="agent", data={}),
        WorkflowNode(id="B", type="agent", data={}),
    ]
    edges = [
        WorkflowEdge(id="e1", source="A", target="B"),
    ]
    workflow = Workflow(id="w1", name="no_error", nodes=nodes, edges=edges)

    target = executor._find_error_edge_target("A", workflow)
    assert target is None


def test_find_error_edge_target_multiple_edges(executor):
    """Test finding error edge among multiple edges from same node."""
    nodes = [
        WorkflowNode(id="A", type="agent", data={}),
        WorkflowNode(id="B", type="agent", data={}),
        WorkflowNode(id="C", type="agent", data={}),
        WorkflowNode(id="ErrorHandler", type="agent", data={}),
    ]
    edges = [
        WorkflowEdge(id="e1", source="A", target="B", source_handle="success"),
        WorkflowEdge(id="e2", source="A", target="C", source_handle="default"),
        WorkflowEdge(id="e3", source="A", target="ErrorHandler", source_handle="error"),
    ]
    workflow = Workflow(id="w1", name="multi", nodes=nodes, edges=edges)

    target = executor._find_error_edge_target("A", workflow)
    assert target == "ErrorHandler"


# =============================================================================
# Workflow Validation Tests
# =============================================================================

def test_validate_workflow_valid(executor):
    """Test validation passes for valid workflow."""
    nodes = [
        WorkflowNode(id="A", type="agent", data={}),
        WorkflowNode(id="B", type="agent", data={}),
    ]
    edges = [
        WorkflowEdge(id="e1", source="A", target="B"),
    ]
    workflow = Workflow(id="w1", name="valid", nodes=nodes, edges=edges)

    # Should not raise
    executor._validate_workflow(workflow)


def test_validate_workflow_too_many_nodes(executor):
    """Test validation fails for too many nodes."""
    nodes = [WorkflowNode(id=f"node{i}", type="agent", data={}) for i in range(101)]
    workflow = Workflow(id="w1", name="too_many", nodes=nodes, edges=[])

    with pytest.raises(WorkflowValidationError, match="maximum is 100"):
        executor._validate_workflow(workflow)


def test_validate_workflow_cycle_detected(executor):
    """Test validation fails for cyclic workflow."""
    nodes = [
        WorkflowNode(id="A", type="agent", data={}),
        WorkflowNode(id="B", type="agent", data={}),
        WorkflowNode(id="C", type="agent", data={}),
    ]
    edges = [
        WorkflowEdge(id="e1", source="A", target="B"),
        WorkflowEdge(id="e2", source="B", target="C"),
        WorkflowEdge(id="e3", source="C", target="A"),  # Cycle
    ]
    workflow = Workflow(id="w1", name="cycle", nodes=nodes, edges=edges)

    with pytest.raises(WorkflowValidationError, match="contains a cycle"):
        executor._validate_workflow(workflow)


def test_validate_workflow_orphan_nodes(executor):
    """Test validation fails for orphan nodes."""
    nodes = [
        WorkflowNode(id="A", type="agent", data={}),
        WorkflowNode(id="B", type="agent", data={}),
        WorkflowNode(id="Orphan", type="agent", data={}),
    ]
    edges = [
        WorkflowEdge(id="e1", source="A", target="B"),
    ]
    workflow = Workflow(id="w1", name="orphan", nodes=nodes, edges=edges)

    with pytest.raises(WorkflowValidationError, match="orphan nodes"):
        executor._validate_workflow(workflow)


def test_validate_workflow_single_node_allowed(executor):
    """Test single node with no edges is valid."""
    nodes = [WorkflowNode(id="A", type="agent", data={})]
    workflow = Workflow(id="w1", name="single", nodes=nodes, edges=[])

    # Should not raise (single node is allowed)
    executor._validate_workflow(workflow)


# =============================================================================
# Additional Helper Tests
# =============================================================================

def test_get_node_timeout_agent(executor):
    """Test timeout for agent nodes."""
    node = WorkflowNode(id="A", type="agent", data={})
    timeout = executor._get_node_timeout(node)
    assert timeout == executor.DEFAULT_NODE_TIMEOUT


def test_get_node_timeout_mcp_tool(executor):
    """Test timeout for MCP tool nodes."""
    node = WorkflowNode(id="A", type="mcp_tool", data={})
    timeout = executor._get_node_timeout(node)
    assert timeout == executor.DEFAULT_TOOL_TIMEOUT


def test_get_node_timeout_parallel(executor):
    """Test timeout for parallel nodes."""
    node = WorkflowNode(id="A", type="parallel", data={})
    timeout = executor._get_node_timeout(node)
    assert timeout == executor.DEFAULT_WORKFLOW_TIMEOUT


def test_get_node_timeout_feedback_loop(executor):
    """Test timeout for feedback_loop nodes."""
    node = WorkflowNode(id="A", type="feedback_loop", data={})
    timeout = executor._get_node_timeout(node)
    assert timeout == executor.DEFAULT_WORKFLOW_TIMEOUT


def test_get_mock_output_agent(executor):
    """Test mock output for agent nodes."""
    node = WorkflowNode(id="A", type="agent", data={"name": "TestAgent"})
    output = executor._get_mock_output(node)
    assert "[Mock]" in output
    assert "TestAgent" in output


def test_get_mock_output_mcp_tool(executor):
    """Test mock output for MCP tool nodes."""
    node = WorkflowNode(id="A", type="mcp_tool", data={"toolName": "search"})
    output = executor._get_mock_output(node)
    assert isinstance(output, dict)
    assert "[Mock]" in str(output)


def test_get_mock_output_mcp_tool_with_mock_response(executor):
    """Test mock output when mockResponse is provided."""
    node = WorkflowNode(
        id="A",
        type="mcp_tool",
        data={"toolName": "search", "mockResponse": {"custom": "mock"}}
    )
    output = executor._get_mock_output(node)
    assert output == {"custom": "mock"}


def test_get_mock_output_condition(executor):
    """Test mock output for condition nodes."""
    node = WorkflowNode(id="A", type="condition", data={})
    output = executor._get_mock_output(node)
    assert output["result"] is True
    assert output["active_handle"] == "true"


def test_get_mock_output_parallel(executor):
    """Test mock output for parallel nodes."""
    node = WorkflowNode(id="A", type="parallel", data={"branches": [1, 2]})
    output = executor._get_mock_output(node)
    assert output["parallel"] is True
    assert output["branches"] == 2


def test_get_mock_output_feedback_loop(executor):
    """Test mock output for feedback_loop nodes."""
    node = WorkflowNode(id="A", type="feedback_loop", data={})
    output = executor._get_mock_output(node)
    assert output["continue_loop"] is False
    assert output["reason"] == "mock_mode"
