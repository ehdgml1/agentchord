"""Tests for built-in tool support in WorkflowExecutor.

Tests cover:
- _create_builtin_tool with valid/missing API key
- _build_agent_tools routing for built-in IDs ("web-search", "tavily")
- No regression for existing MCP tool ID formats
"""

import pytest
from unittest.mock import patch, MagicMock

from app.core.executor import WorkflowExecutor, WorkflowNode
from app.core.mcp_manager import MCPTool


@pytest.fixture
def mcp_tools_registry():
    """Create MCP tools registry for regression tests."""
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
                    },
                    "required": ["html"],
                },
            ),
        ],
    }


def _mock_settings(tavily_key: str = ""):
    """Create mock settings with configurable tavily_api_key."""
    settings = MagicMock()
    settings.tavily_api_key = tavily_key
    return settings


# =============================================================================
# _create_builtin_tool Tests
# =============================================================================


@pytest.mark.asyncio
class TestCreateBuiltinTool:
    """Tests for _create_builtin_tool method."""

    async def test_web_search_with_api_key(self, executor):
        """Should return a Tool when tavily_api_key is configured."""
        with patch("app.config.get_settings", return_value=_mock_settings("sk-test-key")):
            tool = executor._create_builtin_tool("web-search")

        assert tool is not None
        assert tool.name == "web_search"
        assert tool.is_async is True
        assert len(tool.parameters) == 1
        assert tool.parameters[0].name == "query"

    async def test_tavily_alias_with_api_key(self, executor):
        """Should return same tool for 'tavily' alias."""
        with patch("app.config.get_settings", return_value=_mock_settings("sk-test-key")):
            tool = executor._create_builtin_tool("tavily")

        assert tool is not None
        assert tool.name == "web_search"

    async def test_web_search_without_api_key(self, executor):
        """Should return None when tavily_api_key is empty."""
        with patch("app.config.get_settings", return_value=_mock_settings("")):
            tool = executor._create_builtin_tool("web-search")

        assert tool is None

    async def test_tavily_without_api_key(self, executor):
        """Should return None when tavily_api_key is empty."""
        with patch("app.config.get_settings", return_value=_mock_settings("")):
            tool = executor._create_builtin_tool("tavily")

        assert tool is None

    async def test_unknown_tool_id(self, executor):
        """Should return None for unrecognized built-in IDs."""
        tool = executor._create_builtin_tool("unknown-tool")
        assert tool is None


# =============================================================================
# _build_agent_tools with Built-in IDs
# =============================================================================


@pytest.mark.asyncio
class TestBuildAgentToolsBuiltin:
    """Tests for _build_agent_tools routing built-in tool IDs."""

    async def test_web_search_id_creates_tool(self, executor):
        """Should create web_search tool from 'web-search' ID."""
        with patch("app.config.get_settings", return_value=_mock_settings("sk-test")):
            tools = await executor._build_agent_tools(["web-search"])

        assert len(tools) == 1
        assert tools[0].name == "web_search"

    async def test_tavily_id_creates_tool(self, executor):
        """Should create web_search tool from 'tavily' ID."""
        with patch("app.config.get_settings", return_value=_mock_settings("sk-test")):
            tools = await executor._build_agent_tools(["tavily"])

        assert len(tools) == 1
        assert tools[0].name == "web_search"

    async def test_builtin_without_key_skipped(self, executor):
        """Should skip built-in tool when API key is missing."""
        with patch("app.config.get_settings", return_value=_mock_settings("")):
            tools = await executor._build_agent_tools(["web-search"])

        assert len(tools) == 0

    async def test_builtin_mixed_with_mcp(self, executor, mcp_tools_registry):
        """Should handle mix of built-in and MCP tool IDs."""
        executor.mcp_manager._tools = mcp_tools_registry

        with patch("app.config.get_settings", return_value=_mock_settings("sk-test")):
            tools = await executor._build_agent_tools([
                "web-search",
                "brave-search:brave_web_search",
            ])

        assert len(tools) == 2
        names = {t.name for t in tools}
        assert "web_search" in names
        assert "brave-search__brave_web_search" in names

    async def test_builtin_skipped_mcp_still_works(self, executor, mcp_tools_registry):
        """Built-in tool skip should not affect MCP tool resolution."""
        executor.mcp_manager._tools = mcp_tools_registry

        with patch("app.config.get_settings", return_value=_mock_settings("")):
            tools = await executor._build_agent_tools([
                "web-search",
                "brave-search:brave_web_search",
            ])

        assert len(tools) == 1
        assert tools[0].name == "brave-search__brave_web_search"


# =============================================================================
# Regression: Existing MCP Tool ID Formats
# =============================================================================


@pytest.mark.asyncio
class TestBuildAgentToolsMCPRegression:
    """Verify existing MCP tool formats still work after built-in addition."""

    async def test_specific_tool_format(self, executor, mcp_tools_registry):
        """serverId:toolName format should still resolve correctly."""
        executor.mcp_manager._tools = mcp_tools_registry

        tools = await executor._build_agent_tools(["brave-search:brave_web_search"])
        assert len(tools) == 1
        assert tools[0].name == "brave-search__brave_web_search"

    async def test_server_only_format(self, executor, mcp_tools_registry):
        """Server-only ID should still bind all tools from that server."""
        executor.mcp_manager._tools = mcp_tools_registry

        tools = await executor._build_agent_tools(["brave-search"])
        assert len(tools) == 1  # brave-search has 1 tool in this fixture

    async def test_empty_list(self, executor):
        """Empty list should return empty."""
        tools = await executor._build_agent_tools([])
        assert len(tools) == 0

    async def test_nonexistent_server(self, executor):
        """Nonexistent server should be skipped."""
        tools = await executor._build_agent_tools(["nonexistent"])
        assert len(tools) == 0

    async def test_nonexistent_specific_tool(self, executor):
        """Nonexistent specific tool should be skipped."""
        tools = await executor._build_agent_tools(["nonexistent:tool"])
        assert len(tools) == 0

    async def test_multiple_servers(self, executor, mcp_tools_registry):
        """Multiple server-only IDs should bind all their tools."""
        executor.mcp_manager._tools = mcp_tools_registry

        tools = await executor._build_agent_tools(["brave-search", "markdown2pdf"])
        assert len(tools) == 2
        names = {t.name for t in tools}
        assert "brave-search__brave_web_search" in names
        assert "markdown2pdf__create_pdf_from_markdown" in names


# =============================================================================
# _BUILTIN_TOOL_IDS class attribute
# =============================================================================


class TestBuiltinToolIds:
    """Tests for the _BUILTIN_TOOL_IDS class attribute."""

    def test_contains_web_search(self):
        """Should include 'web-search'."""
        assert "web-search" in WorkflowExecutor._BUILTIN_TOOL_IDS

    def test_contains_tavily(self):
        """Should include 'tavily'."""
        assert "tavily" in WorkflowExecutor._BUILTIN_TOOL_IDS

    def test_is_set(self):
        """Should be a set for O(1) lookup."""
        assert isinstance(WorkflowExecutor._BUILTIN_TOOL_IDS, set)
