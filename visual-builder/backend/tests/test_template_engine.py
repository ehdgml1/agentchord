"""Tests for template engine in workflow executor."""
import pytest
import pytest_asyncio
from app.core.executor import WorkflowNode, Workflow, WorkflowEdge, WorkflowExecutor
import uuid
from datetime import datetime


@pytest.mark.asyncio
async def test_simple_template_resolution(executor):
    """Test {{node1}} resolves to node1's output string."""
    context = {
        "node1": "Hello World",
        "input": "test",
    }
    template = "Output: {{node1}}"
    result = executor._resolve_template(template, context)
    assert result == "Output: Hello World"


@pytest.mark.asyncio
async def test_nested_field_access(executor):
    """Test {{node1.result.url}} with dict context."""
    context = {
        "node1": {
            "result": {
                "url": "https://example.com",
                "status": 200,
            }
        },
        "input": "test",
    }
    template = "Fetched from {{node1.result.url}}"
    result = executor._resolve_template(template, context)
    assert result == "Fetched from https://example.com"


@pytest.mark.asyncio
async def test_unresolved_template_kept(executor):
    """Test {{missing}} stays as {{missing}}."""
    context = {
        "node1": "value",
        "input": "test",
    }
    template = "Value: {{missing}}"
    result = executor._resolve_template(template, context)
    assert result == "Value: {{missing}}"


@pytest.mark.asyncio
async def test_multiple_templates_in_string(executor):
    """Test multiple templates in one string."""
    context = {
        "node1": {"url": "https://api.example.com"},
        "node2": {"path": "/data/output.json"},
        "input": "test",
    }
    template = "Fetch {{node1.url}} and save to {{node2.path}}"
    result = executor._resolve_template(template, context)
    assert result == "Fetch https://api.example.com and save to /data/output.json"


@pytest.mark.asyncio
async def test_input_source_with_template(executor):
    """Test inputSource takes priority but templates still resolve in the value."""
    # Create a simple workflow with two nodes
    nodes = [
        WorkflowNode(
            id="node1",
            type="agent",
            data={
                "name": "Agent 1",
                "role": "Process",
                "model": "gpt-4o-mini",
            },
        ),
        WorkflowNode(
            id="node2",
            type="agent",
            data={
                "name": "Agent 2",
                "role": "Format",
                "model": "gpt-4o-mini",
                "inputSource": "node1",  # Explicit input source
            },
        ),
    ]
    edges = [WorkflowEdge(id="edge1", source="node1", target="node2")]
    workflow = Workflow(
        id=str(uuid.uuid4()),
        name="Test Workflow",
        nodes=nodes,
        edges=edges,
    )

    context = {
        "input": "original input",
        "node1": "Result with {{placeholder}}",
        "placeholder": "resolved value",
    }

    # When inputSource is set, it should use that node's output
    # and apply template resolution to it
    result = executor._resolve_input(nodes[1], context)
    assert result == "Result with resolved value"


@pytest.mark.asyncio
async def test_input_template_override(executor):
    """Test inputTemplate in node data overrides inputSource."""
    node = WorkflowNode(
        id="node2",
        type="agent",
        data={
            "name": "Agent 2",
            "role": "Process",
            "model": "gpt-4o-mini",
            "inputSource": "node1",
            "inputTemplate": "Custom: {{node1}} and {{nodeX}}",
        },
    )

    context = {
        "input": "original",
        "node1": "First",
        "nodeX": "Second",
    }

    result = executor._resolve_input(node, context)
    assert result == "Custom: First and Second"


@pytest.mark.asyncio
async def test_mcp_params_template_resolution(executor):
    """Test MCP tool parameters with templates get resolved."""
    node = WorkflowNode(
        id="tool1",
        type="mcp_tool",
        data={
            "serverId": "test-server",
            "toolName": "fetch_url",
            "parameters": {
                "url": "{{node1.endpoint}}",
                "output_path": "{{node2.path}}",
                "static_value": "no template here",
            },
        },
    )

    context = {
        "node1": {"endpoint": "https://api.example.com/v1"},
        "node2": {"path": "/tmp/output.json"},
    }

    # Call _run_mcp_tool
    result = await executor._run_mcp_tool(node, context)

    # The mock MCP manager should receive resolved parameters
    assert result["arguments"]["url"] == "https://api.example.com/v1"
    assert result["arguments"]["output_path"] == "/tmp/output.json"
    assert result["arguments"]["static_value"] == "no template here"


@pytest.mark.asyncio
async def test_no_templates_passthrough(executor):
    """Test strings without {{}} pass through unchanged."""
    context = {
        "node1": "value",
        "input": "test",
    }
    template = "Just a plain string without templates"
    result = executor._resolve_template(template, context)
    assert result == "Just a plain string without templates"


@pytest.mark.asyncio
async def test_template_with_numeric_values(executor):
    """Test templates with numeric values get converted to strings."""
    context = {
        "node1": {"count": 42, "price": 99.99},
        "input": "test",
    }
    template = "Count: {{node1.count}}, Price: {{node1.price}}"
    result = executor._resolve_template(template, context)
    assert result == "Count: 42, Price: 99.99"


@pytest.mark.asyncio
async def test_template_with_boolean_values(executor):
    """Test templates with boolean values get converted to strings."""
    context = {
        "node1": {"success": True, "failed": False},
        "input": "test",
    }
    template = "Success: {{node1.success}}, Failed: {{node1.failed}}"
    result = executor._resolve_template(template, context)
    assert result == "Success: True, Failed: False"


@pytest.mark.asyncio
async def test_partial_path_resolution(executor):
    """Test template with partial path that cannot be fully resolved."""
    context = {
        "node1": "just a string, not a dict",
        "input": "test",
    }
    # Trying to access .field on a string should keep template unresolved
    template = "Value: {{node1.field}}"
    result = executor._resolve_template(template, context)
    assert result == "Value: {{node1.field}}"


@pytest.mark.asyncio
async def test_deep_nested_field_access(executor):
    """Test deeply nested field access."""
    context = {
        "node1": {
            "data": {
                "user": {
                    "profile": {
                        "name": "John Doe"
                    }
                }
            }
        },
        "input": "test",
    }
    template = "User: {{node1.data.user.profile.name}}"
    result = executor._resolve_template(template, context)
    assert result == "User: John Doe"


@pytest.mark.asyncio
async def test_template_in_workflow_execution(executor, simple_workflow):
    """Test templates work end-to-end in workflow execution."""
    # Modify the workflow to use templates
    simple_workflow.nodes[0].data["inputTemplate"] = "Process: {{input}}"
    simple_workflow.nodes[1].data["inputTemplate"] = "Result from {{start}}"

    # Run in mock mode to avoid actual agent calls
    execution = await executor.run(
        workflow=simple_workflow,
        input="test input",
        mode="mock",
    )

    # Check execution succeeded
    assert execution.status.value == "completed"
    assert len(execution.node_executions) == 2
