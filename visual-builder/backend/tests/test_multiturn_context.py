"""Tests for multi-turn conversation context passthrough in executor."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.executor import WorkflowNode
from agentchord.memory.conversation import ConversationMemory
from agentchord.memory.base import MemoryEntry
from agentchord import Agent


class MockAgentResult:
    """Mock agent result."""
    def __init__(self, output: str):
        self.output = output
        self.usage = None


@pytest.mark.asyncio
async def test_run_agent_with_chat_history(executor):
    """Test that chat_history from context is injected into ConversationMemory."""
    node = WorkflowNode(
        id="agent1",
        type="agent",
        data={
            "name": "TestAgent",
            "role": "Assistant",
            "model": "gpt-4",
            "systemPrompt": "You are a helpful assistant",
        },
        position={"x": 0, "y": 0},
    )

    context = {
        "input": "What did we discuss?",
        "chat_history": [
            {"role": "user", "content": "Hello, I need help with Python"},
            {"role": "assistant", "content": "Sure, I can help with Python. What do you need?"},
            {"role": "user", "content": "How do I read a file?"},
            {"role": "assistant", "content": "You can use open() function."},
        ],
    }

    with patch("agentchord.Agent") as mock_agent_class:
        mock_agent_instance = AsyncMock()
        mock_agent_instance.run = AsyncMock(return_value=MockAgentResult("We discussed Python file reading"))
        mock_agent_class.return_value = mock_agent_instance

        with patch.object(executor, "_build_agent_tools", return_value=[]):
            with patch.object(executor, "_create_llm_provider", return_value=MagicMock()):
                with patch.object(executor, "_resolve_input", return_value="What did we discuss?"):
                    result = await executor._run_agent(node, context)

    # Verify Agent was called with memory parameter
    mock_agent_class.assert_called_once()
    call_kwargs = mock_agent_class.call_args.kwargs

    assert "memory" in call_kwargs
    memory = call_kwargs["memory"]

    # Verify memory is ConversationMemory instance
    assert isinstance(memory, ConversationMemory)

    # Verify chat history was loaded into memory
    entries = memory.get_recent(limit=10)
    assert len(entries) == 4

    assert entries[0].role == "user"
    assert entries[0].content == "Hello, I need help with Python"

    assert entries[1].role == "assistant"
    assert entries[1].content == "Sure, I can help with Python. What do you need?"

    assert entries[2].role == "user"
    assert entries[2].content == "How do I read a file?"

    assert entries[3].role == "assistant"
    assert entries[3].content == "You can use open() function."


@pytest.mark.asyncio
async def test_run_agent_without_chat_history(executor):
    """Test that when no chat_history, memory is None."""
    node = WorkflowNode(
        id="agent1",
        type="agent",
        data={
            "name": "TestAgent",
            "role": "Assistant",
            "model": "gpt-4",
        },
        position={"x": 0, "y": 0},
    )

    context = {
        "input": "Hello",
    }

    with patch("agentchord.Agent") as mock_agent_class:
        mock_agent_instance = AsyncMock()
        mock_agent_instance.run = AsyncMock(return_value=MockAgentResult("Hi there!"))
        mock_agent_class.return_value = mock_agent_instance

        with patch.object(executor, "_build_agent_tools", return_value=[]):
            with patch.object(executor, "_create_llm_provider", return_value=MagicMock()):
                with patch.object(executor, "_resolve_input", return_value="Hello"):
                    result = await executor._run_agent(node, context)

    # Verify Agent was called with memory=None
    mock_agent_class.assert_called_once()
    call_kwargs = mock_agent_class.call_args.kwargs

    assert "memory" in call_kwargs
    assert call_kwargs["memory"] is None


@pytest.mark.asyncio
async def test_run_agent_empty_chat_history(executor):
    """Test that empty chat_history list does not create memory."""
    node = WorkflowNode(
        id="agent1",
        type="agent",
        data={
            "name": "TestAgent",
            "role": "Assistant",
            "model": "gpt-4",
        },
        position={"x": 0, "y": 0},
    )

    context = {
        "input": "Hello",
        "chat_history": [],
    }

    with patch("agentchord.Agent") as mock_agent_class:
        mock_agent_instance = AsyncMock()
        mock_agent_instance.run = AsyncMock(return_value=MockAgentResult("Hi!"))
        mock_agent_class.return_value = mock_agent_instance

        with patch.object(executor, "_build_agent_tools", return_value=[]):
            with patch.object(executor, "_create_llm_provider", return_value=MagicMock()):
                with patch.object(executor, "_resolve_input", return_value="Hello"):
                    result = await executor._run_agent(node, context)

    # Empty list should not create memory
    mock_agent_class.assert_called_once()
    call_kwargs = mock_agent_class.call_args.kwargs

    assert "memory" in call_kwargs
    assert call_kwargs["memory"] is None


@pytest.mark.asyncio
async def test_chat_history_filters_empty_content(executor):
    """Test that messages with empty content are skipped."""
    node = WorkflowNode(
        id="agent1",
        type="agent",
        data={
            "name": "TestAgent",
            "role": "Assistant",
            "model": "gpt-4",
        },
        position={"x": 0, "y": 0},
    )

    context = {
        "input": "Hello",
        "chat_history": [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": ""},  # Empty content - should be skipped
            {"role": "user", "content": "Second message"},
            {"role": "assistant", "content": "Second response"},
            {"role": "user", "content": ""},  # Empty content - should be skipped
        ],
    }

    with patch("agentchord.Agent") as mock_agent_class:
        mock_agent_instance = AsyncMock()
        mock_agent_instance.run = AsyncMock(return_value=MockAgentResult("Response"))
        mock_agent_class.return_value = mock_agent_instance

        with patch.object(executor, "_build_agent_tools", return_value=[]):
            with patch.object(executor, "_create_llm_provider", return_value=MagicMock()):
                with patch.object(executor, "_resolve_input", return_value="Hello"):
                    result = await executor._run_agent(node, context)

    # Verify memory only contains messages with content
    mock_agent_class.assert_called_once()
    call_kwargs = mock_agent_class.call_args.kwargs

    memory = call_kwargs["memory"]
    assert isinstance(memory, ConversationMemory)

    entries = memory.get_recent(limit=10)
    assert len(entries) == 3  # Only 3 out of 5 messages had content

    assert entries[0].content == "First message"
    assert entries[1].content == "Second message"
    assert entries[2].content == "Second response"
