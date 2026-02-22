#!/usr/bin/env python3
"""Full Agent Integration Example.

AgentChord의 모든 통합 기능을 하나의 Agent에서 시연합니다:
- Memory (대화 기록 유지)
- CostTracker (비용 추적)
- Callbacks (이벤트 모니터링)
- Tools (도구 사용)
- MCP (외부 도구 통합)

API 키 없이 Mock 프로바이더로 실행됩니다.

실행:
    python examples/11_full_agent.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import AsyncMock

from agentchord import Agent
from agentchord.core.types import ToolCall
from agentchord.memory import ConversationMemory
from agentchord.tracking import CostTracker, CallbackManager, CallbackEvent, CallbackContext
from agentchord.tools import tool
from agentchord.protocols.mcp.types import MCPTool, MCPToolResult
from tests.conftest import MockToolCallProvider


async def main() -> None:
    print("=" * 60)
    print("AgentChord Full Integration Demo")
    print("=" * 60)

    # ── 1. 도구 정의 ──
    @tool(description="날씨를 조회합니다")
    def get_weather(city: str) -> str:
        return f"{city}: 맑음, 22°C"

    @tool(description="두 숫자를 더합니다")
    def add(a: int, b: int) -> int:
        return a + b

    # ── 2. MCP 도구 (외부 도구 시뮬레이션) ──
    mock_mcp = AsyncMock()
    mock_mcp.list_tools = AsyncMock(return_value=[
        MCPTool(
            name="web_search",
            description="Search the web",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            server_id="brave-search",
        ),
    ])
    mock_mcp.call_tool = AsyncMock(
        return_value=MCPToolResult(content="검색 결과: AgentChord는 멀티에이전트 프레임워크입니다.", is_error=False)
    )

    # ── 3. 콜백 설정 ──
    events: list[str] = []
    callback_manager = CallbackManager()

    def on_event(ctx: CallbackContext) -> None:
        events.append(f"  [{ctx.event.value}] agent={ctx.agent_name}")

    callback_manager.register_global(on_event)

    # ── 4. LLM Provider (도구 호출 시뮬레이션) ──
    provider = MockToolCallProvider(
        tool_calls_sequence=[
            [ToolCall(id="call_1", name="get_weather", arguments={"city": "서울"})],
            None,  # Final text response
        ],
        responses=["", "서울 날씨는 맑고 22°C입니다. 좋은 하루 보내세요!"],
    )

    # ── 5. Agent 생성 (모든 기능 통합) ──
    agent = Agent(
        name="assistant",
        role="다재다능한 AI 어시스턴트",
        llm_provider=provider,
        memory=ConversationMemory(max_entries=100),
        cost_tracker=CostTracker(budget_limit=10.0),
        callbacks=callback_manager,
        tools=[get_weather, add],
        mcp_client=mock_mcp,
    )

    # MCP 도구 등록
    mcp_tool_names = await agent.setup_mcp()

    print(f"\n[Agent 설정]")
    print(f"  Name: {agent.name}")
    print(f"  Role: {agent.role}")
    print(f"  Tools: {[t.name for t in agent.tools]}")
    print(f"  MCP Tools: {mcp_tool_names}")
    print(f"  Memory: {type(agent.memory).__name__}")
    print(f"  Cost Tracker: budget=${agent.cost_tracker.remaining_budget:.2f}")

    # ── 6. 실행 ──
    print(f"\n[실행]")
    result = await agent.run("서울 날씨 어때?")

    print(f"  Output: {result.output}")
    print(f"  Duration: {result.duration_ms}ms")
    print(f"  Usage: {result.usage.total_tokens} tokens")
    print(f"  Cost: ${result.cost:.6f}")
    print(f"  Tool Rounds: {result.metadata.get('tool_rounds', 0)}")

    # ── 7. 콜백 이벤트 확인 ──
    print(f"\n[발생한 이벤트]")
    for event in events:
        print(event)

    # ── 8. 메모리 확인 ──
    print(f"\n[메모리 상태]")
    for entry in agent.memory.get_recent(5):
        print(f"  {entry.role}: {entry.content[:50]}...")

    # ── 9. 비용 추적 확인 ──
    summary = agent.cost_tracker.get_summary()
    print(f"\n[비용 추적]")
    print(f"  Total Cost: ${summary.total_cost_usd:.6f}")
    print(f"  Total Tokens: {summary.total_tokens}")
    print(f"  Remaining Budget: ${agent.cost_tracker.remaining_budget:.4f}")

    print("\n" + "=" * 60)
    print("Full Integration Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
