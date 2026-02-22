"""Unit tests for the built-in web search tool."""

from __future__ import annotations

import pytest

import httpx

from agentchord.tools.base import Tool, ToolParameter
from agentchord.tools.web_search import create_web_search_tool


class TestCreateWebSearchTool:
    """Tests for create_web_search_tool factory."""

    def test_returns_tool_instance(self) -> None:
        """Should return a valid Tool object."""
        tool = create_web_search_tool(api_key="test-key")
        assert isinstance(tool, Tool)

    def test_tool_name(self) -> None:
        """Should have the correct name."""
        tool = create_web_search_tool(api_key="test-key")
        assert tool.name == "web_search"

    def test_tool_description(self) -> None:
        """Should have a meaningful description."""
        tool = create_web_search_tool(api_key="test-key")
        assert "search" in tool.description.lower()
        assert "web" in tool.description.lower()

    def test_tool_has_query_parameter(self) -> None:
        """Should define a 'query' parameter of type string."""
        tool = create_web_search_tool(api_key="test-key")
        assert len(tool.parameters) == 1
        param = tool.parameters[0]
        assert isinstance(param, ToolParameter)
        assert param.name == "query"
        assert param.type == "string"
        assert param.required is True

    def test_tool_is_async(self) -> None:
        """The underlying function should be async."""
        tool = create_web_search_tool(api_key="test-key")
        assert tool.is_async is True

    def test_openai_schema(self) -> None:
        """Should produce a valid OpenAI function-calling schema."""
        tool = create_web_search_tool(api_key="test-key")
        schema = tool.to_openai_schema()
        assert schema["type"] == "function"
        fn = schema["function"]
        assert fn["name"] == "web_search"
        assert "query" in fn["parameters"]["properties"]
        assert "query" in fn["parameters"]["required"]

    def test_anthropic_schema(self) -> None:
        """Should produce a valid Anthropic tool schema."""
        tool = create_web_search_tool(api_key="test-key")
        schema = tool.to_anthropic_schema()
        assert schema["name"] == "web_search"
        assert "query" in schema["input_schema"]["properties"]


@pytest.mark.asyncio
class TestWebSearchExecution:
    """Tests for the web_search function with mocked HTTP."""

    async def test_successful_search(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should parse Tavily response into formatted text."""
        mock_response = {
            "answer": "Python is a programming language.",
            "results": [
                {
                    "title": "Python.org",
                    "content": "Welcome to Python, the official home of the language.",
                    "url": "https://python.org",
                },
                {
                    "title": "Wikipedia",
                    "content": "Python is a high-level programming language.",
                    "url": "https://en.wikipedia.org/wiki/Python",
                },
            ],
        }

        async def mock_post(self, url, **kwargs):
            resp = httpx.Response(200, json=mock_response, request=httpx.Request("POST", url))
            return resp

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        tool = create_web_search_tool(api_key="test-key")
        result = await tool.func(query="Python programming")

        assert "Summary: Python is a programming language." in result
        assert "Python.org" in result
        assert "https://python.org" in result
        assert "Wikipedia" in result

    async def test_search_no_answer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should handle response without answer field."""
        mock_response = {
            "results": [
                {
                    "title": "Result 1",
                    "content": "Some content here",
                    "url": "https://example.com",
                },
            ],
        }

        async def mock_post(self, url, **kwargs):
            return httpx.Response(200, json=mock_response, request=httpx.Request("POST", url))

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        tool = create_web_search_tool(api_key="test-key")
        result = await tool.func(query="test")

        assert "Summary:" not in result
        assert "Result 1" in result
        assert "https://example.com" in result

    async def test_search_empty_results(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should return 'No results found.' when response is empty."""
        mock_response = {"results": []}

        async def mock_post(self, url, **kwargs):
            return httpx.Response(200, json=mock_response, request=httpx.Request("POST", url))

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        tool = create_web_search_tool(api_key="test-key")
        result = await tool.func(query="obscure query")

        assert result == "No results found."

    async def test_search_truncates_long_content(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should truncate content to 200 characters."""
        long_content = "x" * 500
        mock_response = {
            "results": [
                {
                    "title": "Long",
                    "content": long_content,
                    "url": "https://example.com",
                },
            ],
        }

        async def mock_post(self, url, **kwargs):
            return httpx.Response(200, json=mock_response, request=httpx.Request("POST", url))

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        tool = create_web_search_tool(api_key="test-key")
        result = await tool.func(query="test")

        # The content portion should be truncated to 200 chars
        lines = result.split("\n")
        content_line = [l for l in lines if l.startswith("- Long:")][0]
        # "- Long: " prefix + 200 chars of content
        assert len(long_content[:200]) == 200
        assert "x" * 200 in content_line
        assert "x" * 201 not in content_line

    async def test_search_api_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should raise on API error (handled by Tool.execute)."""
        async def mock_post(self, url, **kwargs):
            return httpx.Response(
                401,
                json={"error": "Invalid API key"},
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        tool = create_web_search_tool(api_key="bad-key")
        # Direct call raises; Tool.execute() would catch it
        with pytest.raises(httpx.HTTPStatusError):
            await tool.func(query="test")

    async def test_search_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should propagate timeout errors."""
        async def mock_post(self, url, **kwargs):
            raise httpx.ReadTimeout("Connection timed out")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        tool = create_web_search_tool(api_key="test-key")
        with pytest.raises(httpx.ReadTimeout):
            await tool.func(query="test")

    async def test_execute_wraps_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Tool.execute() should return error ToolResult on failure."""
        async def mock_post(self, url, **kwargs):
            raise httpx.ReadTimeout("Connection timed out")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        tool = create_web_search_tool(api_key="test-key")
        result = await tool.execute(query="test")

        assert result.success is False
        assert "timed out" in result.error.lower()

    async def test_max_results_passed_to_api(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should pass max_results to the Tavily API request body."""
        captured_json = {}

        async def mock_post(self, url, **kwargs):
            captured_json.update(kwargs.get("json", {}))
            return httpx.Response(
                200,
                json={"results": []},
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        tool = create_web_search_tool(api_key="test-key", max_results=3)
        await tool.func(query="test")

        assert captured_json["max_results"] == 3
        assert captured_json["api_key"] == "test-key"
        assert captured_json["include_answer"] is True


class TestWebSearchToolExport:
    """Tests for public API export."""

    def test_importable_from_tools_package(self) -> None:
        """Should be importable from agentchord.tools."""
        from agentchord.tools import create_web_search_tool as imported

        assert imported is create_web_search_tool

    def test_in_all(self) -> None:
        """Should be listed in __all__."""
        import agentchord.tools as tools_mod

        assert "create_web_search_tool" in tools_mod.__all__
