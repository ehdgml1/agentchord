# 예제

AgentChord에는 `examples/` 디렉토리에 18개의 완전한 예제가 포함되어 있습니다.

## 예제 실행 방법

```bash
# API 키 설정
export OPENAI_API_KEY="sk-your-key"

# 예제 실행
python examples/01_hello_world.py
```

API 키가 필요 없는 예제(mock 모드)는 키 없이도 바로 실행할 수 있습니다.

## 예제 목록

| # | 파일명 | 설명 | 주요 기능 |
|---|--------|------|----------|
| 00 | `demo.py` | 프레임워크 데모 | 전체 기능 시연 |
| 01 | `hello_world.py` | 기본 에이전트 | `Agent`, `run_sync()` |
| 02 | `multi_model.py` | 다중 프로바이더 | OpenAI·Anthropic·Gemini·Ollama 비교 |
| 03 | `workflow_sequential.py` | 순차 워크플로우 | `Workflow`, Flow DSL `->` |
| 04 | `workflow_parallel.py` | 병렬 워크플로우 | `[agent1, agent2]`, `MergeStrategy` |
| 05 | `with_mcp.py` | MCP 통합 | MCP 클라이언트, mock 모드 |
| 06 | `a2a_server.py` | A2A 프로토콜 서버 | A2A 서버 구동, 에이전트 노출 |
| 07 | `memory_system.py` | 메모리 시스템 | `ConversationMemory`, `WorkingMemory` |
| 08 | `cost_tracking.py` | 비용 추적 | `CostTracker`, 토큰 사용량 집계 |
| 09 | `tools.py` | 도구 시스템 | `@tool` 데코레이터, 도구 실행 루프 |
| 10 | `streaming.py` | 스트리밍 | `agent.stream()`, 도구 호출 포함 |
| 11 | `full_agent.py` | 전체 기능 통합 | 도구+메모리+비용+스트리밍 조합 |
| 12a | `lifecycle_management.py` | 라이프사이클 관리 | `async with Agent()`, `close()` |
| 12b | `memory_persistence.py` | 영속 메모리 | `JSONFileStore`, `SQLiteStore` |
| 12c | `trace_collector.py` | 실행 추적 | `TraceCollector`, JSON/JSONL 내보내기 |
| 13 | `structured_output.py` | 구조화된 출력 | `OutputSchema`, Pydantic 검증 |
| 14 | `rag_pipeline.py` | RAG 파이프라인 | 문서 수집·검색·생성, 하이브리드 검색 |
| 15 | `multi_agent_team.py` | 멀티에이전트 팀 | `AgentTeam`, 5가지 전략 |
| 16 | `debate_strategy.py` | 토론 전략 | `DebateStrategy`, 에이전트 간 토론 수렴 |

## 주요 예제 상세

### Hello World (01)

```python
from agentchord import Agent

agent = Agent(name="assistant", role="AI 도우미", model="gpt-4o-mini")
result = agent.run_sync("안녕!")
print(result.output)
```

### Flow DSL 워크플로우 (03-04)

```python
# 순차 실행: A -> B -> C
workflow = Workflow(agents=[a, b, c], flow="researcher -> writer -> reviewer")

# 병렬 실행: [A, B] -> C
workflow = Workflow(agents=[a, b, c], flow="[analyst1, analyst2] -> summarizer")

# 혼합 패턴: A -> [B, C] -> D
workflow = Workflow(agents=[a, b, c, d], flow="researcher -> [analyst1, analyst2] -> writer")
```

### 도구 시스템 (09)

```python
from agentchord import tool

@tool(description="두 숫자를 더합니다")
def add(a: int, b: int) -> int:
    return a + b

agent = Agent(name="math", role="계산기", tools=[add])
```

### 멀티에이전트 팀 (15)

```python
from agentchord.orchestration import AgentTeam, OrchestrationStrategy

team = AgentTeam(
    name="research_team",
    members=[researcher, analyst, writer],
    strategy=OrchestrationStrategy.COORDINATOR,
)

result = await team.run("AI 시장 동향 보고서 작성")
print(result.output)
```

### RAG 파이프라인 (14)

```python
from agentchord.rag import RAGPipeline, create_rag_tools

pipeline = RAGPipeline(...)
rag_tools = create_rag_tools(pipeline)

agent = Agent(
    name="rag_agent",
    role="문서 기반 Q&A 전문가",
    model="gpt-4o-mini",
    tools=rag_tools,
)
```
