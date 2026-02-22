"""Tests for executor MCP tool attachment to agents and multi-agent members.

Tests cover:
- _build_agent_tools with "serverId:toolName" format (specific tool)
- _build_agent_tools with "serverId" format (all tools from server)
- _mcp_tool_to_agentchord_tool helper
- _run_multi_agent passing mcpTools per member
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.executor import WorkflowExecutor, WorkflowNode
from app.core.mcp_manager import MCPTool


@pytest.fixture
def mcp_tools_registry():
    """Create a realistic MCP tools registry with multiple servers."""
    return {
        "brave-search": [
            MCPTool(
                server_id="brave-search",
                name="brave_web_search",
                description="Search the web using Brave",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                    },
                    "required": ["query"],
                },
            ),
            MCPTool(
                server_id="brave-search",
                name="brave_local_search",
                description="Search locally using Brave",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Local search query"},
                    },
                    "required": ["query"],
                },
            ),
        ],
        "tavily": [
            MCPTool(
                server_id="tavily",
                name="tavily_search",
                description="Tavily search",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                    },
                    "required": ["query"],
                },
            ),
        ],
        "markdown2pdf": [
            MCPTool(
                server_id="markdown2pdf",
                name="create_pdf_from_markdown",
                description="Generate a PDF document",
                input_schema={
                    "type": "object",
                    "properties": {
                        "html": {"type": "string", "description": "HTML content"},
                        "filename": {"type": "string", "description": "Output filename"},
                    },
                    "required": ["html"],
                },
            ),
        ],
    }


@pytest.mark.asyncio
class TestBuildAgentToolsSpecificTool:
    """Test _build_agent_tools with serverId:toolName format."""

    async def test_specific_tool_returns_one_tool(self, executor, mcp_tools_registry):
        executor.mcp_manager._tools = mcp_tools_registry
        tools = await executor._build_agent_tools(["brave-search:brave_web_search"])
        assert len(tools) == 1
        assert tools[0].name == "brave-search__brave_web_search"
        assert tools[0].description == "Search the web using Brave"

    async def test_specific_tool_not_found_skipped(self, executor, mcp_tools_registry):
        executor.mcp_manager._tools = mcp_tools_registry
        tools = await executor._build_agent_tools(["nonexistent:tool"])
        assert len(tools) == 0

    async def test_multiple_specific_tools(self, executor, mcp_tools_registry):
        executor.mcp_manager._tools = mcp_tools_registry
        tools = await executor._build_agent_tools([
            "brave-search:brave_web_search",
            "tavily:tavily_search",
        ])
        assert len(tools) == 2
        names = {t.name for t in tools}
        assert names == {"brave-search__brave_web_search", "tavily__tavily_search"}

    async def test_specific_tool_preserves_parameters(self, executor, mcp_tools_registry):
        executor.mcp_manager._tools = mcp_tools_registry
        tools = await executor._build_agent_tools(["markdown2pdf:create_pdf_from_markdown"])
        assert len(tools) == 1
        tool = tools[0]
        assert len(tool.parameters) == 2
        html_param = next(p for p in tool.parameters if p.name == "html")
        assert html_param.required is True
        filename_param = next(p for p in tool.parameters if p.name == "filename")
        assert filename_param.required is False


@pytest.mark.asyncio
class TestBuildAgentToolsServerOnly:
    """Test _build_agent_tools with server-only ID format (no colon)."""

    async def test_server_only_returns_all_tools(self, executor, mcp_tools_registry):
        executor.mcp_manager._tools = mcp_tools_registry
        tools = await executor._build_agent_tools(["brave-search"])
        assert len(tools) == 2
        names = {t.name for t in tools}
        assert names == {"brave-search__brave_web_search", "brave-search__brave_local_search"}

    async def test_server_only_single_tool_server(self, executor, mcp_tools_registry):
        executor.mcp_manager._tools = mcp_tools_registry
        tools = await executor._build_agent_tools(["markdown2pdf"])
        assert len(tools) == 1
        assert tools[0].name == "markdown2pdf__create_pdf_from_markdown"

    async def test_server_only_not_found_returns_empty(self, executor, caplog):
        executor.mcp_manager._tools = {}
        tools = await executor._build_agent_tools(["nonexistent"])
        assert len(tools) == 0
        assert "No tools found for MCP server: nonexistent" in caplog.text

    async def test_mixed_formats(self, executor, mcp_tools_registry):
        """Test mixing server-only and specific tool IDs."""
        executor.mcp_manager._tools = mcp_tools_registry
        tools = await executor._build_agent_tools([
            "brave-search",             # all tools from brave (2)
            "tavily:tavily_search",     # specific tavily tool (1)
        ])
        assert len(tools) == 3
        names = {t.name for t in tools}
        assert "brave-search__brave_web_search" in names
        assert "brave-search__brave_local_search" in names
        assert "tavily__tavily_search" in names

    async def test_server_only_multiple_servers(self, executor, mcp_tools_registry):
        """Test binding all tools from multiple servers."""
        executor.mcp_manager._tools = mcp_tools_registry
        tools = await executor._build_agent_tools([
            "brave-search",    # 2 tools
            "markdown2pdf",   # 1 tool
        ])
        assert len(tools) == 3


@pytest.mark.asyncio
class TestMcpToolToAgentChordTool:
    """Test _mcp_tool_to_agentchord_tool helper method."""

    async def test_creates_tool_with_correct_name(self, executor):
        mcp_tool = MCPTool(
            server_id="server1",
            name="tool1",
            description="Test tool",
            input_schema={"type": "object", "properties": {}},
        )
        tool = executor._mcp_tool_to_agentchord_tool(mcp_tool)
        assert tool.name == "server1__tool1"
        assert tool.description == "Test tool"

    async def test_creates_tool_with_parameters(self, executor):
        mcp_tool = MCPTool(
            server_id="s",
            name="t",
            description="Search",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        )
        tool = executor._mcp_tool_to_agentchord_tool(mcp_tool)
        assert len(tool.parameters) == 1
        assert tool.parameters[0].name == "query"
        assert tool.parameters[0].required is True

    async def test_tool_func_calls_mcp_manager(self, executor):
        """Verify the generated tool func calls mcp_manager.execute_tool."""
        executor.mcp_manager.execute_tool = AsyncMock(return_value={"result": "ok"})

        mcp_tool = MCPTool(
            server_id="my-server",
            name="my_tool",
            description="A tool",
            input_schema={"type": "object", "properties": {}},
        )
        tool = executor._mcp_tool_to_agentchord_tool(mcp_tool)

        # Call the tool's func
        result = await tool.func(param1="value1")
        executor.mcp_manager.execute_tool.assert_awaited_once_with(
            "my-server", "my_tool", {"param1": "value1"}
        )

    async def test_closure_captures_correct_server_and_tool(self, executor, mcp_tools_registry):
        """Verify each tool's closure captures its own server_id/tool_name."""
        executor.mcp_manager._tools = mcp_tools_registry
        executor.mcp_manager.execute_tool = AsyncMock(return_value={"result": "ok"})

        tools = await executor._build_agent_tools(["brave-search"])
        assert len(tools) == 2

        # Call first tool
        await tools[0].func(query="test1")
        # Call second tool
        await tools[1].func(query="test2")

        calls = executor.mcp_manager.execute_tool.call_args_list
        assert len(calls) == 2
        # Both should use "brave-search" server but different tool names
        server_ids = {c.args[0] for c in calls}
        assert server_ids == {"brave-search"}
        tool_names = {c.args[1] for c in calls}
        assert tool_names == {"brave_web_search", "brave_local_search"}


@pytest.mark.asyncio
class TestRunMultiAgentMcpTools:
    """Test that _run_multi_agent passes mcpTools to members."""

    async def test_member_mcp_tools_are_built(self, executor, mcp_tools_registry):
        """Verify that member mcpTools config results in tools being built."""
        executor.mcp_manager._tools = mcp_tools_registry
        member_config = {
            "id": "m1",
            "name": "researcher",
            "role": "worker",
            "model": "gpt-4o",
            "systemPrompt": "Research news",
            "mcpTools": ["brave-search"],
        }
        tools = await executor._build_agent_tools(member_config.get("mcpTools", []))
        assert len(tools) == 2  # both brave search tools

    async def test_member_without_mcp_tools(self, executor):
        """Verify that member without mcpTools gets no tools."""
        member_config = {
            "id": "m2",
            "name": "writer",
            "role": "worker",
            "model": "gpt-4o",
            "systemPrompt": "Write content",
        }
        tools = await executor._build_agent_tools(member_config.get("mcpTools", []))
        assert len(tools) == 0

    async def test_member_with_specific_tools(self, executor, mcp_tools_registry):
        """Verify specific tool IDs in member config."""
        executor.mcp_manager._tools = mcp_tools_registry
        member_config = {
            "mcpTools": ["brave-search:brave_web_search", "tavily:tavily_search"],
        }
        tools = await executor._build_agent_tools(member_config.get("mcpTools", []))
        assert len(tools) == 2
        names = {t.name for t in tools}
        assert names == {"brave-search__brave_web_search", "tavily__tavily_search"}

    async def test_multi_agent_mock_mode_with_mcp_tools(self, executor, mcp_tools_registry):
        """Verify multi_agent node with member mcpTools runs in mock mode."""
        from app.core.executor import Workflow, WorkflowEdge
        import uuid

        executor.mcp_manager._tools = mcp_tools_registry

        node = WorkflowNode(
            id="team-1",
            type="multi_agent",
            data={
                "name": "Research Team",
                "strategy": "map_reduce",
                "maxRounds": 5,
                "members": [
                    {
                        "name": "searcher",
                        "role": "worker",
                        "model": "gpt-4o",
                        "systemPrompt": "Search for news",
                        "mcpTools": ["brave-search"],
                    },
                    {
                        "name": "writer",
                        "role": "worker",
                        "model": "gpt-4o",
                        "systemPrompt": "Write summary",
                    },
                ],
            },
        )

        workflow = Workflow(
            id=str(uuid.uuid4()),
            name="Multi-Agent Test",
            nodes=[node],
            edges=[],
        )

        # Mock mode skips actual LLM calls
        execution = await executor.run(workflow, "test input", mode="mock")
        assert execution.status == "completed"

    async def test_empty_mcp_tools_list(self, executor):
        """Verify empty mcpTools list returns no tools."""
        tools = await executor._build_agent_tools([])
        assert len(tools) == 0
