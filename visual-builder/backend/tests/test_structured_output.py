"""Test structured output for agent nodes."""
import pytest
from app.core.executor import WorkflowNode


def test_get_mock_output_agent_with_output_fields(executor):
    """Test mock output for agent nodes with outputFields returns structured dict."""
    node = WorkflowNode(
        id="A",
        type="agent",
        data={
            "name": "Evaluator",
            "outputFields": [
                {"name": "score", "type": "number"},
                {"name": "feedback", "type": "text"},
                {"name": "approved", "type": "boolean"},
                {"name": "tags", "type": "list"},
            ]
        }
    )
    output = executor._get_mock_output(node)
    
    # Should return dict with all fields
    assert isinstance(output, dict)
    assert output["score"] == 85
    assert isinstance(output["feedback"], str)
    assert "[Mock]" in output["feedback"]
    # Should contain richer text demonstrating multi-sentence capability
    assert "detailed" in output["feedback"].lower() or "text" in output["feedback"].lower()
    assert output["approved"] is True
    assert isinstance(output["tags"], list)
    assert len(output["tags"]) == 3


def test_get_mock_output_agent_without_output_fields(executor):
    """Test mock output for agent nodes without outputFields returns string."""
    node = WorkflowNode(id="A", type="agent", data={"name": "TestAgent"})
    output = executor._get_mock_output(node)
    
    # Should return string for backward compatibility
    assert isinstance(output, str)
    assert "[Mock]" in output
    assert "TestAgent" in output


def test_get_mock_output_agent_with_empty_output_fields(executor):
    """Test mock output for agent nodes with empty outputFields array returns string."""
    node = WorkflowNode(
        id="A",
        type="agent",
        data={"name": "TestAgent", "outputFields": []}
    )
    output = executor._get_mock_output(node)
    
    # Should return string when outputFields is empty
    assert isinstance(output, str)
    assert "[Mock]" in output
    assert "TestAgent" in output


def test_get_mock_output_agent_with_invalid_fields(executor):
    """Test mock output handles fields with missing names gracefully."""
    node = WorkflowNode(
        id="A",
        type="agent",
        data={
            "name": "Evaluator",
            "outputFields": [
                {"name": "score", "type": "number"},
                {"name": "", "type": "text"},  # Empty name, should be skipped
                {"type": "boolean"},  # No name, should be skipped
            ]
        }
    )
    output = executor._get_mock_output(node)

    # Should only include valid field
    assert isinstance(output, dict)
    assert "score" in output
    assert len(output) == 1


def test_get_mock_output_agent_with_description(executor):
    """Test mock output uses description field when generating text mock data."""
    node = WorkflowNode(
        id="A",
        type="agent",
        data={
            "name": "Evaluator",
            "outputFields": [
                {"name": "reasoning", "type": "text", "description": "평가 근거를 상세히 설명"},
                {"name": "score", "type": "number", "description": "1-10 사이의 점수"},
            ]
        }
    )
    output = executor._get_mock_output(node)

    # Should include description in mock text
    assert isinstance(output, dict)
    assert "reasoning" in output
    assert "평가 근거를 상세히 설명" in output["reasoning"]
    assert "detailed" in output["reasoning"].lower()
    assert output["score"] == 85
