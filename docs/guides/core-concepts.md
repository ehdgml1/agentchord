# 핵심 개념

AgentChord의 기본 구성 요소를 설명합니다.

## Agent

Agent는 AgentChord의 기본 단위입니다. LLM을 설정, 도구, 메모리와 함께 래핑합니다.

### Agent 생성

```python
from agentchord import Agent

agent = Agent(
    name="researcher",              # 고유 식별자
    role="Research specialist",     # 역할 설명 (시스템 프롬프트에 사용됨)
    model="gpt-4o-mini",           # LLM 모델 (프로바이더 자동 감지)
    temperature=0.7,               # 창의성 (0.0-2.0)
    max_tokens=4096,               # 최대 응답 길이
    timeout=60.0,                  # 요청 타임아웃 (초)
    system_prompt=None,            # 커스텀 시스템 프롬프트 (None이면 자동 생성)
)
```

### 선택적 통합 파라미터

```python
from agentchord import Agent
from agentchord.memory import ConversationMemory
from agentchord.tracking.cost import CostTracker
from agentchord.resilience import create_default_resilience
from agentchord.tracking.callbacks import CallbackManager

agent = Agent(
    name="full",
    role="Fully configured agent",
    model="gpt-4o-mini",
    llm_provider=custom_provider,   # 자동 감지 프로바이더 대신 직접 지정
    memory=ConversationMemory(),    # 대화 히스토리 기억
    cost_tracker=CostTracker(),     # 토큰 사용량 및 비용 추적
    resilience=create_default_resilience(),  # 재시도, 서킷 브레이커, 타임아웃
    tools=[my_tool],               # 호출 가능한 도구 목록
    callbacks=CallbackManager(),    # 이벤트 알림
    mcp_client=mcp,                # MCP 프로토콜 클라이언트
)
```

### 실행

```python
# 비동기 (권장)
result = await agent.run("Hello!")

# 동기 래퍼
result = agent.run_sync("Hello!")

# 스트리밍
async for chunk in agent.stream("이야기를 들려줘"):
    print(chunk.delta, end="")
```

### AgentResult

`run()` 호출은 `AgentResult`를 반환합니다:

| 필드 | 타입 | 설명 |
|------|------|------|
| `output` | str | 최종 텍스트 응답 |
| `messages` | list[Message] | 전체 대화 히스토리 |
| `usage` | Usage | 토큰 수 (프롬프트 + 컴플리션) |
| `cost` | float | 예상 비용 (USD) |
| `duration_ms` | int | 실행 시간 (밀리초) |
| `metadata` | dict | agent_name, model, provider, tool_rounds 포함 |
| `parsed_output` | dict or None | output_schema 사용 시 파싱된 출력 |

```python
result = await agent.run("Hello!")
print(result.output)                          # "Hi there!"
print(result.usage.total_tokens)              # 150
print(result.cost)                            # 0.000225
print(result.metadata["agent_name"])          # "researcher"
print(result.metadata["tool_rounds"])         # 1
```

## Workflow

Workflow는 Flow DSL을 사용해 여러 Agent를 조율합니다.

### Flow DSL 문법

| 패턴 | 문법 | 설명 |
|------|------|------|
| 순차 실행 | `"A -> B -> C"` | 각 에이전트가 이전 출력을 입력으로 받음 |
| 병렬 실행 | `"[A, B]"` | 에이전트가 동시에 실행됨 |
| 혼합 | `"A -> [B, C] -> D"` | 두 패턴 조합 |

```python
from agentchord import Agent, Workflow

researcher = Agent(name="researcher", role="Research", model="gpt-4o-mini")
writer = Agent(name="writer", role="Writing", model="gpt-4o-mini")

workflow = Workflow(
    agents=[researcher, writer],
    flow="researcher -> writer",
)

result = workflow.run_sync("AI에 대해 글 써줘")
```

### 병합 전략

병렬 에이전트가 완료되면 출력이 병합됩니다:

| 전략 | 동작 |
|------|------|
| `CONCAT_NEWLINE` | `\n\n`으로 연결 (기본값) |
| `CONCAT` | 구분자 없이 연결 |
| `FIRST` | 첫 번째 에이전트 출력만 사용 |
| `LAST` | 마지막 에이전트 출력만 사용 |

```python
from agentchord import Workflow, MergeStrategy

workflow = Workflow(
    agents=[a, b, c],
    flow="[a, b] -> c",
    merge_strategy=MergeStrategy.FIRST,
)
```

### WorkflowResult

| 속성 | 타입 | 설명 |
|------|------|------|
| `output` | str | 최종 출력 |
| `status` | WorkflowStatus | COMPLETED, FAILED 등 |
| `is_success` | bool | COMPLETED이면 True |
| `error` | str or None | FAILED 시 에러 메시지 |
| `total_cost` | float | 전체 에이전트 비용 합계 |
| `total_tokens` | int | 전체 에이전트 토큰 합계 |
| `total_duration_ms` | int | 전체 실행 시간 |
| `agent_results` | list[AgentResult] | 개별 에이전트 결과 |
| `usage` | Usage | 집계된 토큰 사용량 |

## WorkflowState

워크플로우 단계 사이를 흐르는 불변 상태 객체입니다.

```python
state = WorkflowState(input="이 데이터를 분석해줘")

# 상태 필드
state.input           # 원본 입력
state.output          # 현재 출력 (에이전트가 업데이트)
state.history         # list[AgentResult] - 모든 에이전트 실행 기록
state.context         # dict - 에이전트 간 공유 데이터
state.effective_input # output이 있으면 output, 없으면 input
```

상태는 불변이며 메서드는 새 복사본을 반환합니다:

```python
state = state.with_output("분석 완료")
state = state.with_context("key", "value")
state = state.with_status(WorkflowStatus.COMPLETED)
```

## Provider Registry

AgentChord는 모델 이름 접두사로 LLM 프로바이더를 자동 감지합니다:

| 접두사 | 프로바이더 | API 키 환경변수 |
|--------|-----------|----------------|
| `gpt-`, `o1-` | OpenAI | `OPENAI_API_KEY` |
| `claude-` | Anthropic | `ANTHROPIC_API_KEY` |
| `gemini-` | Google Gemini | `GOOGLE_API_KEY` |
| `ollama/` | Ollama (로컬) | 없음 |

```python
# 모델 이름에서 자동 감지
agent1 = Agent(name="a", role="R", model="gpt-4o")            # → OpenAI
agent2 = Agent(name="b", role="R", model="claude-3-5-sonnet") # → Anthropic
agent3 = Agent(name="c", role="R", model="gemini-2.0-flash")  # → Gemini
agent4 = Agent(name="d", role="R", model="ollama/llama3.2")   # → Ollama
```

### 커스텀 프로바이더 등록

```python
from agentchord.llm.registry import get_registry

registry = get_registry()
registry.register("custom", my_factory, ["custom-"])

# 이제 "custom-v1"이 커스텀 프로바이더로 라우팅됨
agent = Agent(name="a", role="R", model="custom-v1")
```

## 메시지와 타입

### Message

```python
from agentchord import Message, MessageRole

# 역할: SYSTEM, USER, ASSISTANT, TOOL
msg = Message(role=MessageRole.USER, content="Hello")

# 팩토리 메서드 사용
msg = Message.user("Hello")
msg = Message.system("You are a helpful assistant")
msg = Message.assistant("Hi there!")
```

### Usage

```python
from agentchord import Usage

usage = Usage(prompt_tokens=100, completion_tokens=50)
print(usage.total_tokens)  # 150
```

### ToolCall

```python
from agentchord import ToolCall

tc = ToolCall(id="call_123", name="calculator", arguments={"expr": "2+2"})
```

### StreamChunk

```python
from agentchord.core.types import StreamChunk

# agent.stream() 중에 yield됨
# chunk.content      - 지금까지 누적된 전체 텍스트
# chunk.delta        - 이번 청크의 새 텍스트
# chunk.finish_reason - 마지막 청크에서 "stop"
# chunk.usage        - 마지막 청크에서 토큰 수
```

## 종합 예제

```python
from agentchord import Agent, Workflow, tool
from agentchord.memory import ConversationMemory
from agentchord.tracking.cost import CostTracker

@tool(description="웹에서 검색")
def search(query: str) -> str:
    return f"Results for: {query}"

tracker = CostTracker()

researcher = Agent(
    name="researcher",
    role="웹 검색으로 리서치",
    model="gpt-4o-mini",
    tools=[search],
    cost_tracker=tracker,
)

writer = Agent(
    name="writer",
    role="리서치 결과로 글 작성",
    model="gpt-4o-mini",
    cost_tracker=tracker,
)

workflow = Workflow(
    agents=[researcher, writer],
    flow="researcher -> writer",
)

result = workflow.run_sync("양자 컴퓨팅에 대해 써줘")
print(result.output)
print(f"총 비용: ${tracker.get_summary().total_cost:.4f}")
```
