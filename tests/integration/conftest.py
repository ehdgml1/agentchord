"""Shared fixtures for integration tests."""

from __future__ import annotations

import pytest

from agentchord.core.agent import Agent
from agentchord.core.types import ToolCall, Usage
from agentchord.memory.conversation import ConversationMemory
from agentchord.tracking.cost import CostTracker
from agentchord.tracking.callbacks import CallbackManager
from tests.conftest import MockLLMProvider, MockToolCallProvider


@pytest.fixture
def wired_agent():
    """Factory for creating a fully-wired agent with all subsystems."""

    def _factory(
        response_content: str = "Test response",
        with_memory: bool = True,
        with_cost_tracker: bool = True,
        with_callbacks: bool = True,
        tools: list | None = None,
        llm_provider: MockLLMProvider | MockToolCallProvider | None = None,
    ) -> tuple:
        memory = ConversationMemory() if with_memory else None
        tracker = CostTracker() if with_cost_tracker else None
        callbacks = CallbackManager() if with_callbacks else None
        provider = llm_provider or MockLLMProvider(response_content=response_content)

        agent = Agent(
            name="integration-test",
            role="Integration test agent",
            llm_provider=provider,
            memory=memory,
            cost_tracker=tracker,
            callbacks=callbacks,
            tools=tools,
        )

        return agent, memory, tracker, callbacks

    return _factory
