#!/usr/bin/env python3
"""Tool System Example.

이 예제는 AgentChord의 Tool 시스템 사용법을 보여줍니다.

실행:
    python examples/09_tools.py
"""

import asyncio
import json

from agentchord.tools import Tool, ToolParameter, ToolResult, tool, ToolExecutor


def demo_tool_decorator() -> None:
    """@tool 데코레이터 데모."""
    print("=" * 60)
    print("1. @tool Decorator Demo")
    print("=" * 60)

    # @tool 데코레이터로 함수를 Tool로 변환
    @tool(description="두 숫자를 더합니다")
    def add(a: int, b: int) -> int:
        return a + b

    @tool(description="문자열을 대문자로 변환합니다")
    def uppercase(text: str) -> str:
        return text.upper()

    @tool(name="calculator_multiply", description="두 숫자를 곱합니다")
    def multiply(x: float, y: float) -> float:
        return x * y

    print("\n[생성된 Tools]")
    print(f"  - {add.name}: {add.description}")
    print(f"  - {uppercase.name}: {uppercase.description}")
    print(f"  - {multiply.name}: {multiply.description}")

    print("\n[add 파라미터]")
    for param in add.parameters:
        print(f"  - {param.name}: {param.type} (required={param.required})")


async def demo_tool_execution() -> None:
    """Tool 실행 데모."""
    print("\n" + "=" * 60)
    print("2. Tool Execution Demo")
    print("=" * 60)

    @tool(description="두 숫자를 나눕니다")
    def divide(a: float, b: float) -> float:
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b

    # 성공 케이스
    result = await divide.execute(a=10, b=2)
    print("\n[성공 케이스] 10 / 2")
    print(f"  success: {result.success}")
    print(f"  result: {result.result}")

    # 에러 케이스
    result = await divide.execute(a=10, b=0)
    print("\n[에러 케이스] 10 / 0")
    print(f"  success: {result.success}")
    print(f"  error: {result.error}")


async def demo_tool_executor() -> None:
    """ToolExecutor 데모."""
    print("\n" + "=" * 60)
    print("3. ToolExecutor Demo")
    print("=" * 60)

    @tool(description="Add two numbers")
    def add(a: int, b: int) -> int:
        return a + b

    @tool(description="Subtract two numbers")
    def subtract(a: int, b: int) -> int:
        return a - b

    # ToolExecutor 생성
    executor = ToolExecutor([add, subtract])

    print("\n[등록된 Tools]")
    for name in executor.tool_names:
        print(f"  - {name}")

    # 도구 실행
    print("\n[실행]")
    result = await executor.execute("add", a=5, b=3)
    print(f"  add(5, 3) = {result.result}")

    result = await executor.execute("subtract", a=10, b=4)
    print(f"  subtract(10, 4) = {result.result}")

    # 없는 도구
    result = await executor.execute("multiply", a=2, b=3)
    print(f"  multiply(2, 3) = Error: {result.error}")


def demo_schema_conversion() -> None:
    """스키마 변환 데모."""
    print("\n" + "=" * 60)
    print("4. Schema Conversion Demo")
    print("=" * 60)

    @tool(description="Search the web for information")
    def web_search(query: str, max_results: int = 10) -> list:
        return [f"Result for: {query}"]

    print("\n[OpenAI Schema]")
    openai_schema = web_search.to_openai_schema()
    print(json.dumps(openai_schema, indent=2))

    print("\n[Anthropic Schema]")
    anthropic_schema = web_search.to_anthropic_schema()
    print(json.dumps(anthropic_schema, indent=2))


async def main() -> None:
    """메인 함수."""
    print("\n" + "=" * 60)
    print("AgentChord Tool System Examples")
    print("=" * 60)

    demo_tool_decorator()
    await demo_tool_execution()
    await demo_tool_executor()
    demo_schema_conversion()

    print("\n" + "=" * 60)
    print("Tool System Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
