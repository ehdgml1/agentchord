#!/usr/bin/env python3
"""Sequential Workflow Example.

이 예제는 여러 Agent가 순차적으로 협력하는 워크플로우를 보여줍니다.
각 Agent의 출력이 다음 Agent의 입력으로 전달됩니다.

실행 전 준비:
    export OPENAI_API_KEY="sk-your-api-key"

실행:
    python examples/03_workflow_sequential.py
"""

from agentchord import Agent
from agentchord.core.workflow import Workflow


def main() -> None:
    """순차 워크플로우 예제."""
    # 1. Agent 정의
    researcher = Agent(
        name="researcher",
        role="주제에 대해 핵심 정보를 조사하는 연구원",
        model="gpt-4o-mini",
        system_prompt="""당신은 연구 전문가입니다.
주어진 주제에 대해 핵심 정보 3가지를 간결하게 조사해주세요.
각 항목은 한 줄로 정리해주세요.""",
    )

    writer = Agent(
        name="writer",
        role="조사된 정보를 바탕으로 글을 작성하는 작가",
        model="gpt-4o-mini",
        system_prompt="""당신은 콘텐츠 작가입니다.
제공된 연구 정보를 바탕으로 200자 이내의 짧은 글을 작성해주세요.
독자가 이해하기 쉽게 작성해주세요.""",
    )

    reviewer = Agent(
        name="reviewer",
        role="작성된 글을 검토하고 피드백을 제공하는 편집자",
        model="gpt-4o-mini",
        system_prompt="""당신은 편집자입니다.
작성된 글을 검토하고 다음을 수행하세요:
1. 잘된 점 1가지
2. 개선할 점 1가지
3. 최종 평가 (한 문장)""",
    )

    # 2. Workflow 생성
    workflow = Workflow(
        agents=[researcher, writer, reviewer],
        flow="researcher -> writer -> reviewer",
    )

    print("=" * 60)
    print("AgentChord Sequential Workflow")
    print("=" * 60)
    print("Flow: researcher -> writer -> reviewer")
    print("=" * 60)

    # 3. 실행
    topic = "2024년 AI 트렌드"
    print(f"\nInput: {topic}\n")
    print("-" * 60)

    result = workflow.run_sync(topic)

    # 4. 결과 출력
    print("\n[Agent Execution History]")
    for i, agent_result in enumerate(result.agent_results, 1):
        agent_name = agent_result.metadata.get("agent_name", "unknown")
        print(f"\n--- {i}. {agent_name} ---")
        print(agent_result.output[:500])  # 최대 500자
        print(f"(Tokens: {agent_result.usage.total_tokens}, Cost: ${agent_result.cost:.6f})")

    print("\n" + "=" * 60)
    print("[Final Output]")
    print("=" * 60)
    print(result.output)

    print("\n" + "-" * 60)
    print("[Statistics]")
    print(f"  Status: {result.status.value}")
    print(f"  Total Tokens: {result.total_tokens:,}")
    print(f"  Total Cost: ${result.total_cost:.6f}")
    print(f"  Total Duration: {result.total_duration_ms}ms")
    print("-" * 60)


if __name__ == "__main__":
    main()
