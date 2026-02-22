#!/usr/bin/env python3
"""Parallel Workflow Example.

이 예제는 여러 Agent가 병렬로 실행되는 워크플로우를 보여줍니다.
같은 입력에 대해 여러 관점에서 동시에 분석합니다.

실행 전 준비:
    export OPENAI_API_KEY="sk-your-api-key"

실행:
    python examples/04_workflow_parallel.py
"""

import asyncio

from agentchord import Agent
from agentchord.core.executor import MergeStrategy
from agentchord.core.workflow import Workflow


async def main() -> None:
    """병렬 워크플로우 예제."""
    # 1. 다양한 관점의 Agent 정의
    tech_analyst = Agent(
        name="tech_analyst",
        role="기술적 관점에서 분석하는 전문가",
        model="gpt-4o-mini",
        system_prompt="""당신은 기술 분석가입니다.
주어진 주제를 기술적 관점에서 분석해주세요.
- 핵심 기술 요소
- 기술적 장단점
100자 이내로 간결하게 작성해주세요.""",
    )

    business_analyst = Agent(
        name="business_analyst",
        role="비즈니스 관점에서 분석하는 전문가",
        model="gpt-4o-mini",
        system_prompt="""당신은 비즈니스 분석가입니다.
주어진 주제를 비즈니스 관점에서 분석해주세요.
- 시장 기회
- 수익 모델
100자 이내로 간결하게 작성해주세요.""",
    )

    user_analyst = Agent(
        name="user_analyst",
        role="사용자 관점에서 분석하는 전문가",
        model="gpt-4o-mini",
        system_prompt="""당신은 UX 전문가입니다.
주어진 주제를 사용자 관점에서 분석해주세요.
- 사용자 가치
- 사용성 고려사항
100자 이내로 간결하게 작성해주세요.""",
    )

    synthesizer = Agent(
        name="synthesizer",
        role="여러 분석을 종합하는 전문가",
        model="gpt-4o-mini",
        system_prompt="""당신은 종합 분석가입니다.
제공된 여러 관점의 분석을 종합하여 최종 인사이트를 도출해주세요.
핵심 결론 3가지를 bullet point로 정리해주세요.""",
    )

    # 2. 병렬 + 순차 혼합 Workflow 생성
    workflow = Workflow(
        agents=[tech_analyst, business_analyst, user_analyst, synthesizer],
        flow="[tech_analyst, business_analyst, user_analyst] -> synthesizer",
        merge_strategy=MergeStrategy.CONCAT_NEWLINE,
    )

    print("=" * 60)
    print("AgentChord Parallel Workflow")
    print("=" * 60)
    print("Flow: [tech, business, user] -> synthesizer")
    print("=" * 60)

    # 3. 실행
    topic = "AI 기반 코드 리뷰 도구"
    print(f"\nInput: {topic}\n")
    print("-" * 60)

    result = await workflow.run(topic)

    # 4. 병렬 실행 결과 출력
    print("\n[Parallel Analysis Results]")
    for agent_result in result.agent_results[:3]:  # 처음 3개는 병렬 실행
        agent_name = agent_result.metadata.get("agent_name", "unknown")
        print(f"\n--- {agent_name} ---")
        print(agent_result.output)

    # 5. 최종 종합 결과
    print("\n" + "=" * 60)
    print("[Synthesized Output]")
    print("=" * 60)
    print(result.output)

    # 6. 통계
    print("\n" + "-" * 60)
    print("[Statistics]")
    print(f"  Status: {result.status.value}")
    print(f"  Agents executed: {len(result.agent_results)}")
    print(f"  Total Tokens: {result.total_tokens:,}")
    print(f"  Total Cost: ${result.total_cost:.6f}")
    print(f"  Total Duration: {result.total_duration_ms}ms")

    # 병렬 실행의 이점 표시
    if len(result.agent_results) >= 3:
        parallel_duration = max(
            r.duration_ms for r in result.agent_results[:3]
        )
        sequential_duration = sum(
            r.duration_ms for r in result.agent_results[:3]
        )
        savings = sequential_duration - parallel_duration
        print(f"\n  [Parallel Efficiency]")
        print(f"  If sequential: ~{sequential_duration}ms")
        print(f"  With parallel: ~{parallel_duration}ms (first 3 agents)")
        print(f"  Time saved: ~{savings}ms")
    print("-" * 60)


if __name__ == "__main__":
    asyncio.run(main())
