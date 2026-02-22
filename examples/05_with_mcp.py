#!/usr/bin/env python3
"""MCP Integration Example.

AgentChord에서 MCP(Model Context Protocol)를 사용하여
외부 도구를 Agent에 연결하는 방법을 보여줍니다.

이 예제는 시뮬레이션 모드로 실행되어 API 키 없이 동작합니다.
실제 MCP 서버 연결은 하단의 주석 코드를 참조하세요.

실행:
    python examples/05_with_mcp.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import AsyncMock

from agentchord import Agent
from agentchord.protocols.mcp.types import MCPTool, MCPToolResult
from agentchord.protocols.mcp.adapter import mcp_tool_to_tool
from tests.conftest import MockLLMProvider


async def demo_mcp_adapter() -> None:
    """MCP 도구 변환 데모."""
    print("=" * 60)
    print("1. MCP Tool → AgentChord Tool Adapter")
    print("=" * 60)

    # MCPTool 정의 (실제로는 MCP 서버에서 자동 발견됨)
    mcp_tool = MCPTool(
        name="read_file",
        description="Read contents of a file",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read"},
            },
            "required": ["path"],
        },
        server_id="filesystem",
    )

    # Mock MCP client for demo
    mock_client = AsyncMock()
    mock_client.call_tool = AsyncMock(
        return_value=MCPToolResult(content="Hello, World!", is_error=False)
    )

    # MCPTool → AgentChord Tool 변환
    tool = mcp_tool_to_tool(mcp_tool, mock_client)

    print(f"\n[변환된 Tool]")
    print(f"  Name: {tool.name}")
    print(f"  Description: {tool.description}")
    print(f"  Parameters: {[p.name for p in tool.parameters]}")
    print(f"  Is Async: {tool.is_async}")

    # 실행 테스트
    result = await tool.execute(path="/tmp/hello.txt")
    print(f"\n[실행 결과]")
    print(f"  Success: {result.success}")
    print(f"  Result: {result.result}")


async def demo_agent_with_mcp() -> None:
    """Agent + MCP 통합 데모."""
    print("\n" + "=" * 60)
    print("2. Agent + MCP Integration")
    print("=" * 60)

    # Mock MCP client
    mock_client = AsyncMock()

    # 여러 MCP 도구 등록
    mcp_tools = [
        MCPTool(
            name="search_files",
            description="Search for files",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
            server_id="filesystem",
        ),
        MCPTool(
            name="create_issue",
            description="Create a GitHub issue",
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["title"],
            },
            server_id="github",
        ),
    ]

    mock_client.list_tools = AsyncMock(return_value=mcp_tools)
    mock_client.call_tool = AsyncMock(
        return_value=MCPToolResult(content="Issue #42 created", is_error=False)
    )

    # Agent에 MCP 클라이언트 전달
    agent = Agent(
        name="developer",
        role="코드 분석 및 GitHub 작업 전문가",
        mcp_client=mock_client,
        llm_provider=MockLLMProvider(response_content="MCP 도구를 활용하여 작업을 완료했습니다."),
    )

    # MCP 도구 자동 등록
    tool_names = await agent.setup_mcp()
    print(f"\n[등록된 MCP 도구] {tool_names}")
    print(f"[Agent 전체 도구] {[t.name for t in agent.tools]}")

    # Agent 실행
    result = await agent.run("GitHub 이슈를 만들어줘")
    print(f"\n[Agent 응답]")
    print(f"  Output: {result.output}")
    print(f"  Duration: {result.duration_ms}ms")

    print("""
[실제 MCP 서버 연결 코드]

    import os
    from agentchord.protocols.mcp import MCPClient

    async with MCPClient() as mcp:
        # MCP 서버 연결
        await mcp.connect(
            "npx", ["-y", "@anthropic/mcp-server-github"],
            env={"GITHUB_TOKEN": os.getenv("GITHUB_TOKEN")}
        )

        # Agent에 연결
        agent = Agent(
            name="developer",
            role="GitHub 전문가",
            model="gpt-4o-mini",
            mcp_client=mcp,
        )
        await agent.setup_mcp()

        # 도구 자동 사용
        result = await agent.run("최근 이슈를 확인해줘")
""")


async def main() -> None:
    print("\n" + "=" * 60)
    print("AgentChord MCP Integration Examples")
    print("=" * 60)

    await demo_mcp_adapter()
    await demo_agent_with_mcp()

    print("\n" + "=" * 60)
    print("MCP Integration Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
