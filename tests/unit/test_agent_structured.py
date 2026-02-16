"""Integration tests for Agent with structured output support."""
from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import BaseModel, Field

from agentweave import Agent
from agentweave.core.structured import OutputSchema
from agentweave.core.types import LLMResponse, Usage, MessageRole
from agentweave.llm.base import BaseLLMProvider


class AnalysisResult(BaseModel):
    """Analysis result schema for testing."""

    sentiment: str = Field(..., description="Sentiment: positive, negative, or neutral")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    summary: str = Field(..., description="Brief summary")


class TaskList(BaseModel):
    """Task list schema for testing."""

    tasks: list[str] = Field(..., description="List of tasks")
    priority: str = Field(..., description="Priority level")


class MockStructuredProvider(BaseLLMProvider):
    """Mock provider that returns structured JSON responses."""

    def __init__(
        self,
        response_content: str,
        provider_name: str = "mock",
        model_name: str = "mock-model",
    ) -> None:
        self._response_content = response_content
        self._provider_name = provider_name
        self._model_name = model_name
        self._last_kwargs: dict = {}

    @property
    def model(self) -> str:
        return self._model_name

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return 0.001

    @property
    def cost_per_1k_output_tokens(self) -> float:
        return 0.002

    async def complete(self, messages, temperature=0.7, max_tokens=4096, **kwargs):
        # Store kwargs for verification
        self._last_kwargs = kwargs

        return LLMResponse(
            content=self._response_content,
            model=self._model_name,
            usage=Usage(prompt_tokens=50, completion_tokens=30),
            finish_reason="stop",
        )

    async def stream(self, messages, temperature=0.7, max_tokens=4096, **kwargs):
        # Not used in these tests
        raise NotImplementedError("Stream not implemented in mock")


@pytest.mark.asyncio
class TestAgentStructuredOutput:
    """Test Agent with structured output schema."""

    async def test_agent_run_with_output_schema_basic(self) -> None:
        """Test basic agent run with output schema."""
        json_response = '{"sentiment": "positive", "confidence": 0.95, "summary": "Great product"}'
        provider = MockStructuredProvider(json_response, provider_name="openai")

        agent = Agent(
            name="analyzer",
            role="Sentiment analyzer",
            llm_provider=provider,
        )

        schema = OutputSchema(AnalysisResult)
        result = await agent.run(
            "Analyze: I love this product!",
            output_schema=schema,
        )

        # Check raw output
        assert result.output == json_response

        # Check parsed output
        assert result.parsed_output is not None
        assert result.parsed_output["sentiment"] == "positive"
        assert result.parsed_output["confidence"] == 0.95
        assert result.parsed_output["summary"] == "Great product"

        # Check metadata
        assert result.metadata["output_schema"] == "AnalysisResult"

    async def test_agent_openai_provider_uses_response_format(self) -> None:
        """Test that OpenAI provider receives response_format parameter."""
        json_response = '{"tasks": ["task1", "task2"], "priority": "high"}'
        provider = MockStructuredProvider(json_response, provider_name="openai")

        agent = Agent(
            name="planner",
            role="Task planner",
            llm_provider=provider,
        )

        schema = OutputSchema(TaskList)
        await agent.run("Plan my day", output_schema=schema)

        # Verify response_format was passed to OpenAI
        assert "response_format" in provider._last_kwargs
        response_format = provider._last_kwargs["response_format"]
        assert response_format["type"] == "json_schema"
        assert response_format["json_schema"]["name"] == "TaskList"

    async def test_agent_non_openai_provider_injects_system_prompt(self) -> None:
        """Test that non-OpenAI providers get schema injected into system prompt."""
        json_response = '{"sentiment": "neutral", "confidence": 0.7, "summary": "Okay"}'
        provider = MockStructuredProvider(json_response, provider_name="anthropic")

        agent = Agent(
            name="analyzer",
            role="Sentiment analyzer",
            llm_provider=provider,
        )

        schema = OutputSchema(AnalysisResult)

        # Mock the complete method to capture messages
        original_complete = provider.complete
        captured_messages = []

        async def capture_complete(messages, **kwargs):
            captured_messages.extend(messages)
            return await original_complete(messages, **kwargs)

        provider.complete = capture_complete

        await agent.run("Analyze this", output_schema=schema)

        # Verify system message was modified
        system_msg = next(m for m in captured_messages if m.role == MessageRole.SYSTEM)
        assert "You MUST respond with valid JSON" in system_msg.content
        assert "schema" in system_msg.content.lower()

    async def test_agent_with_markdown_wrapped_json(self) -> None:
        """Test agent handling markdown-wrapped JSON response."""
        json_response = '''```json
{
    "sentiment": "positive",
    "confidence": 0.88,
    "summary": "Good vibes"
}
```'''
        provider = MockStructuredProvider(json_response)

        agent = Agent(
            name="analyzer",
            role="Sentiment analyzer",
            llm_provider=provider,
        )

        schema = OutputSchema(AnalysisResult)
        result = await agent.run("Analyze", output_schema=schema)

        # Should parse despite markdown wrapper
        assert result.parsed_output is not None
        assert result.parsed_output["sentiment"] == "positive"
        assert result.parsed_output["confidence"] == 0.88

    async def test_agent_with_invalid_json_response(self) -> None:
        """Test agent handling invalid JSON response."""
        json_response = '{"sentiment": "positive"}'  # Missing required fields
        provider = MockStructuredProvider(json_response)

        agent = Agent(
            name="analyzer",
            role="Sentiment analyzer",
            llm_provider=provider,
        )

        schema = OutputSchema(AnalysisResult)
        result = await agent.run("Analyze", output_schema=schema)

        # Should not crash, but parsed_output should be None
        assert result.output == json_response
        assert result.parsed_output is None

    async def test_agent_with_malformed_json_response(self) -> None:
        """Test agent handling malformed JSON response."""
        json_response = '{"invalid json'
        provider = MockStructuredProvider(json_response)

        agent = Agent(
            name="analyzer",
            role="Sentiment analyzer",
            llm_provider=provider,
        )

        schema = OutputSchema(AnalysisResult)
        result = await agent.run("Analyze", output_schema=schema)

        # Should not crash, but parsed_output should be None
        assert result.parsed_output is None

    async def test_agent_without_output_schema(self) -> None:
        """Test that agent works normally without output_schema."""
        provider = MockStructuredProvider("This is a normal text response")

        agent = Agent(
            name="helper",
            role="General assistant",
            llm_provider=provider,
        )

        result = await agent.run("Hello")

        # No parsing should occur
        assert result.output == "This is a normal text response"
        assert result.parsed_output is None
        assert result.metadata.get("output_schema") is None

    async def test_agent_schema_metadata_in_result(self) -> None:
        """Test that schema name is included in result metadata."""
        json_response = '{"tasks": ["buy milk"], "priority": "low"}'
        provider = MockStructuredProvider(json_response)

        agent = Agent(
            name="planner",
            role="Task planner",
            llm_provider=provider,
        )

        schema = OutputSchema(TaskList, description="Daily tasks")
        result = await agent.run("What to do?", output_schema=schema)

        assert result.metadata["output_schema"] == "TaskList"

    async def test_agent_multiple_calls_same_schema(self) -> None:
        """Test reusing the same schema across multiple agent calls."""
        schema = OutputSchema(AnalysisResult)

        # First call
        provider1 = MockStructuredProvider(
            '{"sentiment": "positive", "confidence": 0.9, "summary": "Good"}'
        )
        agent1 = Agent(name="a1", role="analyzer", llm_provider=provider1)
        result1 = await agent1.run("Test 1", output_schema=schema)

        # Second call
        provider2 = MockStructuredProvider(
            '{"sentiment": "negative", "confidence": 0.85, "summary": "Bad"}'
        )
        agent2 = Agent(name="a2", role="analyzer", llm_provider=provider2)
        result2 = await agent2.run("Test 2", output_schema=schema)

        # Both should parse correctly
        assert result1.parsed_output["sentiment"] == "positive"
        assert result2.parsed_output["sentiment"] == "negative"

    async def test_agent_different_schemas(self) -> None:
        """Test using different schemas with the same agent (sequentially)."""
        provider = MockStructuredProvider("")

        agent = Agent(
            name="versatile",
            role="Multi-purpose agent",
            llm_provider=provider,
        )

        # First call with AnalysisResult schema
        provider._response_content = '{"sentiment": "neutral", "confidence": 0.5, "summary": "Meh"}'
        schema1 = OutputSchema(AnalysisResult)
        result1 = await agent.run("Analyze", output_schema=schema1)

        # Second call with TaskList schema
        provider._response_content = '{"tasks": ["task1"], "priority": "medium"}'
        schema2 = OutputSchema(TaskList)
        result2 = await agent.run("Plan", output_schema=schema2)

        # Both should work with their respective schemas
        assert result1.parsed_output["sentiment"] == "neutral"
        assert result2.parsed_output["tasks"] == ["task1"]
        assert result1.metadata["output_schema"] == "AnalysisResult"
        assert result2.metadata["output_schema"] == "TaskList"

    def test_agent_sync_with_output_schema(self) -> None:
        """Test synchronous agent.run_sync with output schema."""
        json_response = '{"sentiment": "positive", "confidence": 0.92, "summary": "Excellent"}'
        provider = MockStructuredProvider(json_response)

        agent = Agent(
            name="analyzer",
            role="Sentiment analyzer",
            llm_provider=provider,
        )

        schema = OutputSchema(AnalysisResult)
        result = agent.run_sync("Analyze this", output_schema=schema)

        # Should work the same as async
        assert result.parsed_output is not None
        assert result.parsed_output["sentiment"] == "positive"
        assert result.parsed_output["confidence"] == 0.92

    async def test_agent_preserves_other_metadata(self) -> None:
        """Test that output_schema doesn't interfere with other metadata."""
        json_response = '{"tasks": ["task"], "priority": "low"}'
        provider = MockStructuredProvider(json_response, provider_name="mock", model_name="test-model")

        agent = Agent(
            name="planner",
            role="Task planner",
            model="test-model",
            llm_provider=provider,
        )

        schema = OutputSchema(TaskList)
        result = await agent.run("Plan", output_schema=schema)

        # Other metadata should still be present
        assert result.metadata["agent_name"] == "planner"
        assert result.metadata["model"] == "test-model"
        assert result.metadata["provider"] == "mock"
        assert result.metadata["tool_rounds"] == 1
        assert result.metadata["output_schema"] == "TaskList"

    async def test_agent_usage_and_cost_preserved(self) -> None:
        """Test that usage tracking and cost calculation still work with output_schema."""
        json_response = '{"sentiment": "positive", "confidence": 0.9, "summary": "Great"}'
        provider = MockStructuredProvider(json_response)

        agent = Agent(
            name="analyzer",
            role="Sentiment analyzer",
            llm_provider=provider,
        )

        schema = OutputSchema(AnalysisResult)
        result = await agent.run("Analyze", output_schema=schema)

        # Usage should be tracked
        assert result.usage.prompt_tokens == 50
        assert result.usage.completion_tokens == 30
        assert result.usage.total_tokens == 80

        # Cost should be calculated
        assert result.cost > 0
