#!/usr/bin/env python3
"""AgentWeave Hello World Example.

이 예제는 AgentWeave의 기본적인 Agent 사용법을 보여줍니다.

실행 전 준비:
    1. OpenAI API 키 설정:
       export OPENAI_API_KEY="sk-your-api-key"

    2. 또는 .env 파일 생성:
       echo 'OPENAI_API_KEY=sk-your-api-key' > .env

실행:
    python examples/01_hello_world.py
"""

from agentweave import Agent


def main() -> None:
    """기본 Agent 사용 예제."""
    # 1. Agent 생성
    agent = Agent(
        name="assistant",
        role="친절한 AI 어시스턴트",
        model="gpt-4o-mini",  # 비용 효율적인 모델
        temperature=0.7,
    )

    print("=" * 50)
    print("AgentWeave Hello World")
    print("=" * 50)
    print(f"Agent: {agent.name}")
    print(f"Role: {agent.role}")
    print(f"Model: {agent.model}")
    print("=" * 50)

    # 2. Agent 실행
    user_input = "안녕하세요! 자기소개 해주세요."
    print(f"\nUser: {user_input}\n")

    result = agent.run_sync(user_input)

    # 3. 결과 출력
    print(f"Assistant: {result.output}\n")
    print("-" * 50)
    print("Statistics:")
    print(f"  - Tokens: {result.usage.total_tokens:,}")
    print(f"    - Prompt: {result.usage.prompt_tokens:,}")
    print(f"    - Completion: {result.usage.completion_tokens:,}")
    print(f"  - Cost: ${result.cost:.6f}")
    print(f"  - Duration: {result.duration_ms}ms")
    print("-" * 50)


if __name__ == "__main__":
    main()
