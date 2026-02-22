"""Tests for Agent's MCP integration and provider registry usage."""

import pytest
from unittest.mock import AsyncMock

from agentchord.core.agent import Agent
from agentchord.core.types import ToolCall
from agentchord.errors.exceptions import ModelNotFoundError
from agentchord.protocols.mcp.types import MCPTool, MCPToolResult
from tests.conftest import MockLLMProvider, MockToolCallProvider


class TestAgentProviderRegistry:
    """Test Agent's use of the provider registry."""

    def test_agent_uses_registry_for_openai(self, mock_provider: MockLLMProvider) -> None:
        """Test agent creation with explicit provider (backward compatibility)."""
        agent = Agent(
            name="test_agent",
            role="test_role",
            model="gpt-4o-mini",
            llm_provider=mock_provider,
        )

        assert agent.name == "test_agent"
        assert agent.role == "test_role"
        assert agent.model == "gpt-4o-mini"
        assert agent._provider is mock_provider

    def test_agent_detects_ollama_model(self) -> None:
        """Test agent handles Ollama model identifiers."""
        # Create agent with Ollama model but pass mock provider to avoid connection
        mock_provider = MockLLMProvider(model="ollama/llama3.2")
        agent = Agent(
            name="test_agent",
            role="test_role",
            model="ollama/llama3.2",
            llm_provider=mock_provider,
        )

        assert agent.model == "ollama/llama3.2"

    def test_agent_unknown_model_raises(self) -> None:
        """Test that unknown model without provider raises ModelNotFoundError."""
        with pytest.raises(ModelNotFoundError):
            Agent(
                name="test_agent",
                role="test_role",
                model="unknown-model-xyz-123",
            )


class TestAgentMCPSetup:
    """Test Agent's MCP client setup and tool registration."""

    def test_mcp_client_stored(self) -> None:
        """Test MCP client is stored in agent."""
        mock_client = AsyncMock()
        mock_provider = MockLLMProvider()

        agent = Agent(
            name="test_agent",
            role="test_role",
            mcp_client=mock_client,
            llm_provider=mock_provider,
        )

        assert agent.mcp_client is mock_client

    def test_mcp_client_default_none(self) -> None:
        """Test MCP client defaults to None when not provided."""
        mock_provider = MockLLMProvider()

        agent = Agent(
            name="test_agent",
            role="test_role",
            llm_provider=mock_provider,
        )

        assert agent.mcp_client is None

    @pytest.mark.asyncio
    async def test_setup_mcp_no_client(self) -> None:
        """Test setup_mcp returns empty list when no client configured."""
        mock_provider = MockLLMProvider()

        agent = Agent(
            name="test_agent",
            role="test_role",
            llm_provider=mock_provider,
        )

        result = await agent.setup_mcp()

        assert result == []
        assert len(agent.tools) == 0

    @pytest.mark.asyncio
    async def test_setup_mcp_registers_tools(self) -> None:
        """Test setup_mcp registers MCP tools with the agent."""
        # Create mock MCP tool
        mcp_tool = MCPTool(
            name="test_tool",
            description="A test tool",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Query parameter"},
                },
                "required": ["query"],
            },
            server_id="test_server",
        )

        # Create mock MCP client
        mock_client = AsyncMock()
        mock_client.list_tools = AsyncMock(return_value=[mcp_tool])

        mock_provider = MockLLMProvider()

        agent = Agent(
            name="test_agent",
            role="test_role",
            llm_provider=mock_provider,
            mcp_client=mock_client,
        )

        # Setup MCP tools
        registered_names = await agent.setup_mcp()

        # Verify tools were registered
        assert registered_names == ["test_tool"]
        assert len(agent.tools) == 1
        assert agent.tools[0].name == "test_tool"
        assert agent.tools[0].description == "A test tool"

    @pytest.mark.asyncio
    async def test_setup_mcp_creates_executor(self) -> None:
        """Test setup_mcp creates tool executor if none exists."""
        # Create mock MCP tool
        mcp_tool = MCPTool(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object", "properties": {}},
            server_id="test_server",
        )

        # Create mock MCP client
        mock_client = AsyncMock()
        mock_client.list_tools = AsyncMock(return_value=[mcp_tool])

        mock_provider = MockLLMProvider()

        # Agent without tools initially has no executor
        agent = Agent(
            name="test_agent",
            role="test_role",
            llm_provider=mock_provider,
        )

        assert agent._tool_executor is None

        # Set MCP client and setup
        agent._mcp_client = mock_client
        await agent.setup_mcp()

        # Executor should now exist
        assert agent._tool_executor is not None
        assert len(agent.tools) == 1


class TestAgentMCPToolExecution:
    """Test Agent's execution with MCP tools."""

    @pytest.mark.asyncio
    async def test_agent_run_with_mcp_tools(self) -> None:
        """Test agent execution with MCP tool calling."""
        # Create mock MCP tool
        mcp_tool = MCPTool(
            name="search",
            description="Search for information",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
            server_id="search_server",
        )

        # Create mock MCP client
        mock_client = AsyncMock()
        mock_client.list_tools = AsyncMock(return_value=[mcp_tool])
        mock_client.call_tool = AsyncMock(
            return_value=MCPToolResult(content="Search result: AgentChord is amazing!")
        )

        # Create mock provider that returns tool_calls, then final response
        tool_call = ToolCall(
            id="call_1",
            name="search",
            arguments={"query": "AgentChord"},
        )

        mock_provider = MockToolCallProvider(
            tool_calls_sequence=[[tool_call], None],
            responses=["", "Based on the search, AgentChord is a great framework!"],
        )

        # Create agent with MCP client and mock provider
        agent = Agent(
            name="test_agent",
            role="test_role",
            llm_provider=mock_provider,
            mcp_client=mock_client,
        )

        # Setup MCP tools
        await agent.setup_mcp()

        # Run agent
        result = await agent.run("Tell me about AgentChord")

        # Verify MCP tool was called
        mock_client.call_tool.assert_called_once()
        call_args = mock_client.call_tool.call_args
        # call_tool(tool_name, kwargs) - positional args
        assert call_args[0][0] == "search"  # tool name
        assert call_args[0][1]["query"] == "AgentChord"  # kwargs dict

        # Verify final result
        assert "AgentChord is a great framework" in result.output
        assert result.metadata["tool_rounds"] == 2
        assert mock_provider.call_count == 2

    @pytest.mark.asyncio
    async def test_agent_run_mcp_tool_error_handling(self) -> None:
        """Test agent handles MCP tool errors gracefully."""
        # Create mock MCP tool
        mcp_tool = MCPTool(
            name="failing_tool",
            description="A tool that fails",
            input_schema={
                "type": "object",
                "properties": {
                    "param": {"type": "string"},
                },
            },
            server_id="test_server",
        )

        # Create mock MCP client that returns error
        mock_client = AsyncMock()
        mock_client.list_tools = AsyncMock(return_value=[mcp_tool])
        mock_client.call_tool = AsyncMock(
            return_value=MCPToolResult(
                content="Error: Tool execution failed",
                is_error=True,
            )
        )

        # Create mock provider
        tool_call = ToolCall(
            id="call_1",
            name="failing_tool",
            arguments={"param": "test"},
        )

        mock_provider = MockToolCallProvider(
            tool_calls_sequence=[[tool_call], None],
            responses=["", "The tool failed, but I handled it gracefully."],
        )

        # Create agent
        agent = Agent(
            name="test_agent",
            role="test_role",
            llm_provider=mock_provider,
            mcp_client=mock_client,
        )

        await agent.setup_mcp()

        # Run agent
        result = await agent.run("Use the failing tool")

        # Should complete even though tool failed
        assert result.output == "The tool failed, but I handled it gracefully."

        # Verify the error was passed to the model as tool message
        assert mock_provider.call_count == 2
        tool_messages = [
            msg for msg in mock_provider.received_messages[1]
            if msg.role.value == "tool"
        ]
        assert len(tool_messages) == 1
        assert "Error: Tool execution failed" in tool_messages[0].content

    @pytest.mark.asyncio
    async def test_agent_run_without_mcp_tools(self) -> None:
        """Test agent runs normally without MCP tools."""
        mock_provider = MockLLMProvider(response_content="Hello world")

        agent = Agent(
            name="test_agent",
            role="test_role",
            llm_provider=mock_provider,
        )

        result = await agent.run("Say hello")

        assert result.output == "Hello world"
        assert len(agent.tools) == 0
