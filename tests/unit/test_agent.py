"""Unit tests for Agent class."""

from __future__ import annotations

import pytest

from agentchord import Agent, AgentResult, Message, MessageRole
from tests.conftest import MockLLMProvider


class TestAgentCreation:
    """Tests for Agent initialization."""

    def test_agent_with_defaults(self, mock_provider: MockLLMProvider) -> None:
        """Agent should be created with default values."""
        agent = Agent(
            name="test-agent",
            role="Test role",
            llm_provider=mock_provider,
        )

        assert agent.name == "test-agent"
        assert agent.role == "Test role"
        assert agent.model == "gpt-4o-mini"
        assert agent.config.temperature == 0.7
        assert agent.config.max_tokens == 4096

    def test_agent_with_custom_config(self, mock_provider: MockLLMProvider) -> None:
        """Agent should accept custom configuration."""
        agent = Agent(
            name="custom-agent",
            role="Custom role",
            model="gpt-4o",
            temperature=0.5,
            max_tokens=2048,
            timeout=30.0,
            llm_provider=mock_provider,
        )

        assert agent.model == "gpt-4o"
        assert agent.config.temperature == 0.5
        assert agent.config.max_tokens == 2048
        assert agent.config.timeout == 30.0

    def test_agent_with_custom_system_prompt(
        self, mock_provider: MockLLMProvider
    ) -> None:
        """Agent should use custom system prompt when provided."""
        custom_prompt = "You are a specialized assistant."
        agent = Agent(
            name="prompted-agent",
            role="Test role",
            system_prompt=custom_prompt,
            llm_provider=mock_provider,
        )

        assert agent.system_prompt == custom_prompt

    def test_agent_default_system_prompt(
        self, mock_provider: MockLLMProvider
    ) -> None:
        """Agent should generate default system prompt from role."""
        agent = Agent(
            name="assistant",
            role="코드 분석 전문가",
            llm_provider=mock_provider,
        )

        assert "assistant" in agent.system_prompt
        assert "코드 분석 전문가" in agent.system_prompt


class TestAgentRun:
    """Tests for Agent.run() method."""

    @pytest.mark.asyncio
    async def test_run_returns_agent_result(
        self, mock_provider: MockLLMProvider
    ) -> None:
        """run() should return an AgentResult."""
        agent = Agent(
            name="test-agent",
            role="Test role",
            llm_provider=mock_provider,
        )

        result = await agent.run("Hello!")

        assert isinstance(result, AgentResult)
        assert result.output == "Mock response"
        assert result.cost >= 0
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_run_includes_correct_messages(
        self, mock_provider: MockLLMProvider
    ) -> None:
        """run() should include system, user, and assistant messages."""
        agent = Agent(
            name="test-agent",
            role="Test role",
            llm_provider=mock_provider,
        )

        result = await agent.run("Hello!")

        assert len(result.messages) == 3
        assert result.messages[0].role == MessageRole.SYSTEM
        assert result.messages[1].role == MessageRole.USER
        assert result.messages[1].content == "Hello!"
        assert result.messages[2].role == MessageRole.ASSISTANT

    @pytest.mark.asyncio
    async def test_run_tracks_usage(
        self, mock_provider: MockLLMProvider
    ) -> None:
        """run() should track token usage."""
        agent = Agent(
            name="test-agent",
            role="Test role",
            llm_provider=mock_provider,
        )

        result = await agent.run("Hello!")

        assert result.usage.prompt_tokens == 10
        assert result.usage.completion_tokens == 5
        assert result.usage.total_tokens == 15

    @pytest.mark.asyncio
    async def test_run_calculates_cost(
        self, mock_provider: MockLLMProvider
    ) -> None:
        """run() should calculate cost based on usage."""
        agent = Agent(
            name="test-agent",
            role="Test role",
            llm_provider=mock_provider,
        )

        result = await agent.run("Hello!")

        # MockProvider: $0.001/1K input, $0.002/1K output
        # 10 input tokens = $0.00001
        # 5 output tokens = $0.00001
        expected_cost = (10 / 1000 * 0.001) + (5 / 1000 * 0.002)
        assert result.cost == pytest.approx(expected_cost, rel=1e-6)

    @pytest.mark.asyncio
    async def test_run_includes_metadata(
        self, mock_provider: MockLLMProvider
    ) -> None:
        """run() should include agent metadata."""
        agent = Agent(
            name="test-agent",
            role="Test role",
            llm_provider=mock_provider,
        )

        result = await agent.run("Hello!")

        assert result.metadata["agent_name"] == "test-agent"
        assert result.metadata["provider"] == "mock"


class TestAgentRunSync:
    """Tests for Agent.run_sync() method."""

    def test_run_sync_returns_same_as_async(
        self, mock_provider: MockLLMProvider
    ) -> None:
        """run_sync() should return same result as run()."""
        agent = Agent(
            name="test-agent",
            role="Test role",
            llm_provider=mock_provider,
        )

        result = agent.run_sync("Hello!")

        assert isinstance(result, AgentResult)
        assert result.output == "Mock response"


class TestAgentRepr:
    """Tests for Agent string representation."""

    def test_repr(self, mock_provider: MockLLMProvider) -> None:
        """Agent should have informative repr."""
        agent = Agent(
            name="my-agent",
            role="My role",
            model="gpt-4o",
            llm_provider=mock_provider,
        )

        repr_str = repr(agent)

        assert "my-agent" in repr_str
        assert "My role" in repr_str
        assert "gpt-4o" in repr_str
