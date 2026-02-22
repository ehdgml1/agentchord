#!/usr/bin/env python3
"""A2A Server Example.

이 예제는 Agent를 A2A(Agent2Agent) 프로토콜로 외부에 노출하는 방법을 보여줍니다.
다른 시스템의 Agent가 HTTP를 통해 이 Agent와 통신할 수 있습니다.

실행 전 준비:
    1. 의존성 설치:
       pip install starlette uvicorn

    2. 환경 변수 설정:
       export OPENAI_API_KEY="sk-your-api-key"

서버 실행:
    python examples/06_a2a_server.py

클라이언트 테스트 (다른 터미널):
    # Agent Card 조회
    curl http://localhost:8080/agent-card

    # 태스크 생성
    curl -X POST http://localhost:8080/tasks \\
         -H "Content-Type: application/json" \\
         -d '{"input": "Hello, agent!"}'

    # 태스크 상태 조회
    curl http://localhost:8080/tasks/{task_id}
"""

import asyncio
import sys

from agentchord import Agent
from agentchord.protocols.a2a import A2AServer, AgentCard


async def main() -> None:
    """A2A 서버 예제."""
    print("=" * 60)
    print("AgentChord A2A Server Example")
    print("=" * 60)

    # 1. Agent 생성
    agent = Agent(
        name="assistant",
        role="다국어 지원 AI 어시스턴트",
        model="gpt-4o-mini",
        system_prompt="""당신은 친절하고 도움이 되는 AI 어시스턴트입니다.
사용자의 질문에 간결하고 정확하게 답변해주세요.
한국어와 영어 모두 지원합니다.""",
    )

    # 2. Agent Card 정의
    card = AgentCard(
        name="agentchord-assistant",
        description="A helpful multilingual AI assistant powered by AgentChord",
        version="1.0.0",
        capabilities=[
            "text_generation",
            "question_answering",
            "translation",
            "summarization",
        ],
        input_modes=["text"],
        output_modes=["text"],
        metadata={
            "framework": "AgentChord",
            "model": "gpt-4o-mini",
        },
    )

    # 3. A2A 서버 생성
    server = A2AServer(agent=agent, card=card)

    print(f"\nAgent: {agent.name}")
    print(f"Role: {agent.role}")
    print(f"Model: {agent.model}")
    print("-" * 60)

    print("\n[A2A Endpoints]")
    print("  GET  /agent-card     - Agent 메타데이터 조회")
    print("  POST /tasks          - 새 태스크 생성")
    print("  GET  /tasks/{id}     - 태스크 상태 조회")
    print("  POST /tasks/{id}/cancel - 태스크 취소")
    print("  GET  /health         - 헬스체크")

    print("\n[Test Commands]")
    print('  curl http://localhost:8080/agent-card')
    print('  curl -X POST http://localhost:8080/tasks \\')
    print('       -H "Content-Type: application/json" \\')
    print('       -d \'{"input": "안녕하세요!"}\'')

    print("\n" + "-" * 60)
    print("Starting A2A server on http://0.0.0.0:8080")
    print("Press Ctrl+C to stop")
    print("-" * 60 + "\n")

    # 4. 서버 시작
    try:
        await server.start(host="0.0.0.0", port=8080)
    except ImportError as e:
        print(f"\nError: {e}")
        print("\nInstall required packages:")
        print("  pip install starlette uvicorn")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        await server.stop()


async def demo_client() -> None:
    """A2A 클라이언트 데모 (별도 스크립트로 실행)."""
    from agentchord.protocols.a2a import A2AClient

    print("=" * 60)
    print("A2A Client Demo")
    print("=" * 60)

    async with A2AClient("http://localhost:8080") as client:
        # Agent Card 조회
        card = await client.get_agent_card()
        print(f"\nConnected to: {card.name}")
        print(f"Description: {card.description}")
        print(f"Capabilities: {card.capabilities}")

        # 태스크 생성 및 대기
        print("\nSending message...")
        response = await client.ask("안녕하세요! 당신은 누구인가요?")
        print(f"Response: {response}")


if __name__ == "__main__":
    # 커맨드라인 인자로 client 모드 지원
    if len(sys.argv) > 1 and sys.argv[1] == "client":
        asyncio.run(demo_client())
    else:
        asyncio.run(main())
