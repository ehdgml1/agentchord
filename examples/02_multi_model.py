#!/usr/bin/env python3
"""여러 모델 사용 예제.

이 예제는 OpenAI와 Anthropic 모델을 모두 사용하는 방법을 보여줍니다.

실행 전 준비:
    export OPENAI_API_KEY="sk-your-openai-key"
    export ANTHROPIC_API_KEY="sk-ant-your-anthropic-key"
"""

import asyncio

from agentweave import Agent


async def compare_models() -> None:
    """여러 모델의 응답을 비교합니다."""
    # OpenAI Agent
    openai_agent = Agent(
        name="openai-assistant",
        role="OpenAI 기반 어시스턴트",
        model="gpt-4o-mini",
    )

    # Anthropic Agent
    anthropic_agent = Agent(
        name="claude-assistant",
        role="Claude 기반 어시스턴트",
        model="claude-3-5-haiku-latest",
    )

    question = "Python의 장점을 3가지만 간단히 설명해주세요."

    print("=" * 60)
    print("Multi-Model Comparison")
    print("=" * 60)
    print(f"\nQuestion: {question}\n")
    print("-" * 60)

    # 병렬 실행
    results = await asyncio.gather(
        openai_agent.run(question),
        anthropic_agent.run(question),
    )

    openai_result, anthropic_result = results

    # OpenAI 결과
    print(f"\n[{openai_agent.model}]")
    print(openai_result.output)
    print(f"  Cost: ${openai_result.cost:.6f} | Tokens: {openai_result.usage.total_tokens}")

    # Anthropic 결과
    print(f"\n[{anthropic_agent.model}]")
    print(anthropic_result.output)
    print(f"  Cost: ${anthropic_result.cost:.6f} | Tokens: {anthropic_result.usage.total_tokens}")

    # 총 비용
    total_cost = openai_result.cost + anthropic_result.cost
    print("-" * 60)
    print(f"Total Cost: ${total_cost:.6f}")


if __name__ == "__main__":
    asyncio.run(compare_models())
