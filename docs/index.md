# AgentChord

**프로토콜 네이티브 멀티에이전트 AI 프레임워크**

AgentChord는 Python으로 멀티에이전트 AI 시스템을 구축하기 위한 asyncio 기반 프레임워크입니다. [MCP](https://modelcontextprotocol.io/) (Model Context Protocol)와 [A2A](https://google.github.io/A2A/) (Agent-to-Agent) 프로토콜을 네이티브로 지원합니다.

## 왜 AgentChord인가?

- **단순한 API** - 3줄 코드로 에이전트 생성
- **프로토콜 네이티브** - MCP·A2A를 후처리 없이 내장 지원
- **프로바이더 무관** - OpenAI, Anthropic, Gemini, Ollama를 한 줄로 교체
- **프로덕션 준비** - 재시도, 서킷 브레이커, 타임아웃, 비용 추적 내장
- **조합 가능** - Flow DSL로 직관적인 워크플로우 구성

## 빠른 예제

```python
from agentchord import Agent, Workflow

# 에이전트 생성
researcher = Agent(name="researcher", role="리서치 전문가", model="gpt-4o-mini")
writer = Agent(name="writer", role="콘텐츠 작성자", model="gpt-4o-mini")

# 워크플로우로 조합
workflow = Workflow(
    agents=[researcher, writer],
    flow="researcher -> writer",
)

# 실행
result = workflow.run_sync("양자 컴퓨팅에 대해 작성해줘")
print(result.output)
```

## 빠른 설치

```bash
pip install agentchord[all]
```

## 문서 구성

- [시작하기](getting-started.md) - 설치 및 첫 번째 에이전트
- [핵심 개념](guides/core-concepts.md) - Agent, Workflow, Flow DSL 이해
- [가이드](guides/tools.md) - 도구, 메모리, 프로바이더, 복원력, 스트리밍
- [API 레퍼런스](api/core.md) - 전체 API 문서
- [예제](examples.md) - 18개 실행 가능한 예제
