#!/usr/bin/env python3
"""Streaming Example.

AgentWeave의 스트리밍 기능을 보여줍니다.
도구가 없을 때는 순수 스트리밍, 도구가 있을 때는 도구 실행 후 응답을 보여줍니다.

이 예제는 Mock 프로바이더로 실행되어 API 키가 필요 없습니다.

실행:
    python examples/10_streaming.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agentweave import Agent
from agentweave.tools import tool
from agentweave.core.types import ToolCall
from tests.conftest import MockLLMProvider, MockToolCallProvider


async def demo_basic_streaming() -> None:
    """기본 스트리밍 데모 (도구 없음)."""
    print("=" * 60)
    print("1. Basic Streaming (No Tools)")
    print("=" * 60)

    agent = Agent(
        name="storyteller",
        role="창의적인 이야기꾼",
        llm_provider=MockLLMProvider(
            response_content="옛날 옛적에 용감한 기사가 살았습니다. 그는 마을을 지키며 평화를 수호했답니다."
        ),
    )

    print("\n[스트리밍 출력]")
    async for chunk in agent.stream("짧은 이야기를 들려주세요"):
        print(f"  chunk.delta: {chunk.delta[:50] if len(chunk.delta) > 50 else chunk.delta}")
        print(f"  chunk.finish_reason: {chunk.finish_reason}")
        if chunk.usage:
            print(f"  chunk.usage: {chunk.usage.total_tokens} tokens")


async def demo_streaming_with_tools() -> None:
    """도구 호출 + 스트리밍 데모."""
    print("\n" + "=" * 60)
    print("2. Streaming with Tool Calling")
    print("=" * 60)

    @tool(description="두 숫자를 더합니다")
    def add(a: int, b: int) -> int:
        return a + b

    # 첫 호출: tool_calls 반환, 두 번째: 최종 텍스트
    provider = MockToolCallProvider(
        tool_calls_sequence=[
            [ToolCall(id="call_1", name="add", arguments={"a": 10, "b": 20})],
            None,  # No tool calls = final response
        ],
        responses=["", "10 + 20 = 30 입니다!"],
    )

    agent = Agent(
        name="calculator",
        role="수학 도우미",
        llm_provider=provider,
        tools=[add],
    )

    print("\n[스트리밍 + 도구 호출]")
    async for chunk in agent.stream("10 + 20을 계산해줘"):
        print(f"  chunk.content: {chunk.content}")
        if chunk.finish_reason:
            print(f"  finish_reason: {chunk.finish_reason}")

    print(f"\n[도구 호출 횟수] LLM calls: {provider.call_count}")


async def demo_streaming_concept() -> None:
    """스트리밍 개념 설명."""
    print("\n" + "=" * 60)
    print("3. Streaming Architecture")
    print("=" * 60)

    print("""
[스트리밍 모드]

    도구 없음 (순수 스트리밍):
        User → Agent → provider.stream() → StreamChunk 즉시 전달
                                          ↓ delta="옛날"
                                          ↓ delta=" 옛적에"
                                          ↓ delta=" ..."

    도구 있음 (하이브리드):
        User → Agent → provider.complete() → tool_calls 감지
                     → tool 실행 (add(10, 20) = 30)
                     → provider.complete() → 최종 응답
                     → StreamChunk로 전달

[실제 사용 코드]

    agent = Agent(
        name="assistant",
        model="gpt-4o-mini",  # 실제 API 키 필요
        tools=[search_tool, calc_tool],
    )

    async for chunk in agent.stream("최근 주가를 계산해줘"):
        print(chunk.delta, end="", flush=True)
""")


async def main() -> None:
    print("\n" + "=" * 60)
    print("AgentWeave Streaming Examples")
    print("=" * 60)

    await demo_basic_streaming()
    await demo_streaming_with_tools()
    await demo_streaming_concept()

    print("\n" + "=" * 60)
    print("Streaming Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
