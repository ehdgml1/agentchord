"""Built-in web search tool using Tavily API."""

from __future__ import annotations

import httpx

from agentchord.tools.base import Tool, ToolParameter


def create_web_search_tool(api_key: str, max_results: int = 5) -> Tool:
    """Create a web search tool using Tavily Search API.

    Args:
        api_key: Tavily API key.
        max_results: Maximum search results to return.

    Returns:
        Tool object for web search.
    """

    async def web_search(query: str) -> str:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "max_results": max_results,
                    "include_answer": True,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        answer = data.get("answer", "")
        results = data.get("results", [])

        parts: list[str] = []
        if answer:
            parts.append(f"Summary: {answer}\n")
        for r in results:
            parts.append(
                f"- {r.get('title', 'Untitled')}: {r.get('content', '')[:200]}"
            )
            parts.append(f"  URL: {r.get('url', '')}")

        return "\n".join(parts) if parts else "No results found."

    return Tool(
        name="web_search",
        description=(
            "Search the web for current information. "
            "Use this to find recent news, facts, or data."
        ),
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description="The search query to look up on the web",
                required=True,
            ),
        ],
        func=web_search,
    )
