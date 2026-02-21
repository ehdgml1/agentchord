# 핵심 API 레퍼런스

AgentChord 핵심 컴포넌트에 대한 완전한 API 레퍼런스입니다. 에이전트, 워크플로우, 실행 엔진, 타입을 다룹니다.

---

## Message

대화에서 주고받는 단일 메시지입니다.

```python
from agentchord.core import Message, MessageRole

# 팩토리 메서드로 생성
msg = Message.system("당신은 도움이 되는 어시스턴트입니다.")
msg = Message.user("안녕하세요!")
msg = Message.assistant("안녕하세요, 무엇을 도와드릴까요?")

# 직접 생성
msg = Message(role=MessageRole.USER, content="파이썬이 뭔가요?")
```

**필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `role` | `MessageRole` | 발신자 역할 (SYSTEM, USER, ASSISTANT, TOOL) |
| `content` | `str` | 메시지 내용 |
| `name` | `str \| None` | 발신자 이름 (선택적) |
| `tool_calls` | `list[ToolCall] \| None` | 어시스턴트가 요청한 도구 호출 목록 |
| `tool_call_id` | `str \| None` | 이 메시지가 응답하는 도구 호출 ID |

**클래스 메서드:**

| 메서드 | 반환값 | 설명 |
|--------|--------|------|
| `system(content: str)` | `Message` | 시스템 메시지 생성 |
| `user(content: str)` | `Message` | 사용자 메시지 생성 |
| `assistant(content: str)` | `Message` | 어시스턴트 메시지 생성 |

---

## MessageRole

대화에서 메시지 역할을 나타내는 열거형입니다.

```python
from agentchord.core import MessageRole

role = MessageRole.SYSTEM    # "system"
role = MessageRole.USER      # "user"
role = MessageRole.ASSISTANT # "assistant"
role = MessageRole.TOOL      # "tool"
```

**값:**

| 값 | 문자열 | 설명 |
|----|--------|------|
| `SYSTEM` | `"system"` | 시스템 지시 메시지 |
| `USER` | `"user"` | 사용자 입력 메시지 |
| `ASSISTANT` | `"assistant"` | 어시스턴트 응답 메시지 |
| `TOOL` | `"tool"` | 도구 실행 결과 메시지 |

---

## ToolCall

어시스턴트가 생성 과정에서 요청한 도구 호출입니다.

```python
from agentchord.core import ToolCall

tool_call = ToolCall(
    id="call_abc123",
    name="search",
    arguments={"query": "AI 트렌드 2025"}
)
```

**필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | `str` | 이 도구 호출의 고유 식별자 |
| `name` | `str` | 호출할 도구 이름 |
| `arguments` | `dict[str, Any]` | 도구에 전달할 인자 |

---

## Usage

단일 LLM 호출의 토큰 사용 통계입니다.

```python
from agentchord.core import Usage

usage = Usage(prompt_tokens=100, completion_tokens=50)
print(usage.total_tokens)  # 150
```

**필드:**

| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `prompt_tokens` | `int` | >= 0 | 프롬프트에 사용된 토큰 수 |
| `completion_tokens` | `int` | >= 0 | 생성에 사용된 토큰 수 |

**프로퍼티:**

| 프로퍼티 | 타입 | 설명 |
|----------|------|------|
| `total_tokens` | `int` | 프롬프트와 컴플리션 토큰의 합계 |

---

## LLMResponse

LLM 프로바이더로부터 받은 응답입니다.

```python
from agentchord.core import LLMResponse, Usage

response = LLMResponse(
    content="파이썬은 범용 프로그래밍 언어입니다.",
    model="gpt-4o-mini",
    usage=Usage(prompt_tokens=50, completion_tokens=30),
    finish_reason="stop",
)
print(response.content)
print(response.usage.total_tokens)  # 80
```

**필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `content` | `str` | 생성된 텍스트 |
| `model` | `str` | 사용된 모델 식별자 |
| `usage` | `Usage` | 토큰 사용 통계 |
| `finish_reason` | `str` | 완료 이유 (stop, length, tool_calls 등) |
| `tool_calls` | `list[ToolCall] \| None` | 모델이 요청한 도구 호출 목록 |
| `raw_response` | `dict[str, Any] \| None` | 프로바이더 원본 응답 |

---

## AgentResult

에이전트 실행 결과입니다.

```python
result = await agent.run("파이썬의 장점은?")

print(result.output)               # 최종 텍스트 출력
print(result.parsed_output)        # 구조화된 출력 (output_schema 사용 시)
print(result.cost)                 # USD 비용
print(result.usage.total_tokens)   # 총 토큰 수
print(result.duration_ms)          # 실행 시간 (밀리초)
print(result.metadata["model"])    # 사용 모델 정보
```

**필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `output` | `str` | 에이전트의 최종 텍스트 출력 |
| `parsed_output` | `dict[str, Any] \| None` | `output_schema` 사용 시 파싱된 구조화 출력 |
| `messages` | `list[Message]` | 전체 대화 기록 |
| `usage` | `Usage` | 토큰 사용 통계 |
| `cost` | `float` | 예상 비용 (USD) |
| `duration_ms` | `int` | 실행 시간 (밀리초) |
| `metadata` | `dict[str, Any]` | 추가 메타데이터 (agent_name, model, provider, tool_rounds 등) |

---

## StreamChunk

스트리밍 LLM 응답의 청크입니다.

```python
async for chunk in agent.stream("시 한 편 써줘"):
    print(chunk.delta, end="", flush=True)  # 증분 텍스트 출력
    if chunk.finish_reason:
        print(f"\n완료 이유: {chunk.finish_reason}")
    if chunk.usage:
        print(f"총 토큰: {chunk.usage.total_tokens}")
```

**필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `content` | `str` | 지금까지 누적된 전체 텍스트 |
| `delta` | `str` | 이 청크에서 새롭게 추가된 텍스트 |
| `finish_reason` | `str \| None` | 완료 이유 (마지막 청크에서만 설정) |
| `usage` | `Usage \| None` | 토큰 사용량 (마지막 청크에서만 설정) |

---

## Agent

LLM 기반 작업을 수행하는 자율 에이전트입니다.

AgentChord의 핵심 구성 요소입니다. 각 에이전트는 이름, 역할, LLM을 가지며, 도구 호출과 메모리를 지원합니다.

```python
from agentchord import Agent
from agentchord.tools import tool

@tool(description="두 수를 더합니다")
def add(a: int, b: int) -> int:
    return a + b

agent = Agent(
    name="math-agent",
    role="수학 계산 전문가입니다.",
    model="gpt-4o-mini",
    tools=[add],
    temperature=0.3,
)

# 비동기 실행
result = await agent.run("3 더하기 5는?")
print(result.output)

# 동기 실행
result = agent.run_sync("3 더하기 5는?")

# 스트리밍
async for chunk in agent.stream("긴 설명을 써줘"):
    print(chunk.delta, end="")
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `name` | `str` | 필수 | 에이전트 고유 이름 |
| `role` | `str` | 필수 | 에이전트 역할/전문성 설명 |
| `model` | `str` | `"gpt-4o-mini"` | LLM 모델 식별자 |
| `temperature` | `float` | `0.7` | 샘플링 온도 (0.0~2.0) |
| `max_tokens` | `int` | `4096` | 생성할 최대 토큰 수 |
| `timeout` | `float` | `60.0` | LLM 요청 타임아웃 (초) |
| `system_prompt` | `str \| None` | `None` | 커스텀 시스템 프롬프트. None이면 기본값 사용 |
| `llm_provider` | `BaseLLMProvider \| None` | `None` | 커스텀 LLM 프로바이더. None이면 레지스트리에서 자동 감지 |
| `memory` | `BaseMemory \| None` | `None` | 대화 기록 메모리 인스턴스 |
| `cost_tracker` | `CostTracker \| None` | `None` | 비용 추적기 |
| `resilience` | `ResilienceConfig \| None` | `None` | 재시도/서킷브레이커 설정 |
| `tools` | `list[Tool] \| None` | `None` | 에이전트가 사용 가능한 도구 목록 |
| `callbacks` | `CallbackManager \| None` | `None` | 이벤트 콜백 매니저 |
| `mcp_client` | `MCPClient \| None` | `None` | MCP 외부 도구 클라이언트 |

**메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `run` | `async run(input: str, *, max_tool_rounds: int = 10, output_schema: OutputSchema \| None = None, **kwargs) -> AgentResult` | `AgentResult` | 에이전트를 비동기로 실행 |
| `run_sync` | `run_sync(input: str, **kwargs) -> AgentResult` | `AgentResult` | `run()`의 동기 래퍼 |
| `stream` | `async stream(input: str, *, max_tool_rounds: int = 10, **kwargs) -> AsyncIterator[StreamChunk]` | `AsyncIterator[StreamChunk]` | 응답을 스트리밍으로 반환 |
| `setup_mcp` | `async setup_mcp() -> list[str]` | `list[str]` | MCP 도구를 에이전트에 등록하고 도구 이름 목록 반환 |
| `close` | `async close() -> None` | `None` | 리소스를 정리 (멱등적) |
| `temporary_tools` | `async temporary_tools(tools: list[Tool])` | 컨텍스트 매니저 | 일시적으로 도구 추가 (전략에서 사용) |
| `with_extended_prompt` | `async with_extended_prompt(extension: str)` | 컨텍스트 매니저 | 시스템 프롬프트를 일시적으로 확장 |

**프로퍼티:**

| 프로퍼티 | 타입 | 설명 |
|----------|------|------|
| `name` | `str` | 에이전트 이름 |
| `role` | `str` | 에이전트 역할 설명 |
| `model` | `str` | LLM 모델 식별자 |
| `system_prompt` | `str` | 현재 시스템 프롬프트 전체 텍스트 |
| `memory` | `BaseMemory \| None` | 메모리 인스턴스 |
| `cost_tracker` | `CostTracker \| None` | 비용 추적기 |
| `tools` | `list[Tool]` | 등록된 도구 목록 |
| `mcp_client` | `MCPClient \| None` | MCP 클라이언트 |

**사용 예제:**

```python
# 기본 사용
agent = Agent(name="helper", role="유용한 어시스턴트")
result = await agent.run("파이썬 3.12의 새 기능은?")
print(result.output)

# 도구와 함께 사용
result = await agent.run("7 더하기 3은?", max_tool_rounds=3)

# 구조화된 출력
from pydantic import BaseModel
from agentchord.core import OutputSchema

class Summary(BaseModel):
    title: str
    points: list[str]

schema = OutputSchema(Summary)
result = await agent.run("파이썬의 장점 3가지", output_schema=schema)
print(result.parsed_output)  # {"title": "...", "points": [...]}

# 비동기 컨텍스트 매니저 (자동 정리)
async with Agent(name="agent", role="...", memory=memory) as agent:
    result = await agent.run("안녕!")
# close() 자동 호출 - 메모리 저장, MCP 연결 해제
```

---

## AgentConfig

에이전트 설정 값을 담는 Pydantic 모델입니다.

```python
from agentchord.core.config import AgentConfig

config = AgentConfig(
    model="gpt-4o",
    temperature=0.5,
    max_tokens=2048,
    timeout=30.0,
)
```

**필드:**

| 필드 | 타입 | 기본값 | 제약 | 설명 |
|------|------|--------|------|------|
| `model` | `str` | `"gpt-4o-mini"` | - | LLM 모델 식별자 |
| `temperature` | `float` | `0.7` | 0.0~2.0 | 샘플링 온도 |
| `max_tokens` | `int` | `4096` | > 0 | 최대 생성 토큰 수 |
| `timeout` | `float` | `60.0` | > 0 | 타임아웃 (초) |
| `top_p` | `float \| None` | `None` | 0.0~1.0 | 뉴클리어스 샘플링 파라미터 |
| `stop` | `list[str] \| None` | `None` | - | 생성 중단 시퀀스 목록 |

---

## OutputSchema

에이전트가 구조화된 JSON 출력을 반환하도록 강제하는 래퍼입니다.

```python
from pydantic import BaseModel
from agentchord.core.structured import OutputSchema

class Person(BaseModel):
    name: str
    age: int
    occupation: str

schema = OutputSchema(Person)

# OpenAI 응답 형식으로 변환
response_format = schema.to_openai_response_format()

# 시스템 프롬프트 지시문 생성
instruction = schema.to_system_prompt_instruction()

# 데이터 검증
person = schema.validate('{"name": "김민준", "age": 30, "occupation": "개발자"}')
print(person.name)  # 김민준

# 실패 시 None 반환
result = schema.validate_safe("잘못된 JSON")  # None
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `model` | `type[T]` | 필수 | Pydantic BaseModel 서브클래스 |
| `description` | `str \| None` | `None` | 스키마 설명. None이면 클래스 docstring 사용 |

**프로퍼티:**

| 프로퍼티 | 타입 | 설명 |
|----------|------|------|
| `model_class` | `type[T]` | Pydantic 모델 클래스 |
| `json_schema` | `dict[str, Any]` | JSON 스키마 딕셔너리 |
| `description` | `str` | 스키마 설명 텍스트 |

**메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `to_openai_response_format` | `() -> dict[str, Any]` | `dict` | OpenAI `response_format` 파라미터 형식 반환 |
| `to_system_prompt_instruction` | `() -> str` | `str` | 비-OpenAI 프로바이더용 시스템 프롬프트 지시문 반환 |
| `validate` | `(data: str \| dict) -> T` | `T` | 데이터를 파싱하고 검증. 실패 시 예외 발생 |
| `validate_safe` | `(data: str \| dict) -> T \| None` | `T \| None` | 데이터를 파싱하고 검증. 실패 시 `None` 반환 |

---

## Workflow

여러 에이전트를 정의된 실행 흐름으로 조율합니다.

```python
from agentchord import Agent, Workflow

researcher = Agent(name="researcher", role="정보 검색 전문가", model="gpt-4o-mini")
writer = Agent(name="writer", role="글쓰기 전문가", model="gpt-4o-mini")

# DSL로 흐름 정의
workflow = Workflow(
    agents=[researcher, writer],
    flow="researcher -> writer",
)
result = await workflow.run("AI 에이전트에 대해 작성해줘")
print(result.output)

# 병렬 실행
workflow = Workflow(
    agents=[researcher, writer],
    flow="[researcher, writer]",  # 동시 실행
)

# 혼합 패턴
workflow = Workflow(
    agents=[researcher, analyzer, writer],
    flow="researcher -> [analyzer, writer]",  # researcher 후 병렬
)
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `agents` | `list[Agent]` | 필수 | Agent 인스턴스 목록 |
| `flow` | `str \| None` | `None` | 흐름 DSL 문자열. None이면 입력 순서대로 순차 실행 |
| `merge_strategy` | `MergeStrategy` | `CONCAT_NEWLINE` | 병렬 실행 결과 병합 방식 |

**메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `run` | `async run(input: str) -> WorkflowResult` | `WorkflowResult` | 워크플로우를 비동기로 실행 |
| `run_sync` | `run_sync(input: str) -> WorkflowResult` | `WorkflowResult` | `run()`의 동기 래퍼 |
| `add_agent` | `add_agent(agent: Agent) -> Workflow` | `Workflow` | 에이전트를 추가하고 self 반환 (메서드 체이닝) |
| `set_flow` | `set_flow(flow: str) -> Workflow` | `Workflow` | 실행 흐름을 설정하고 self 반환 |
| `close` | `async close() -> None` | `None` | 모든 에이전트 리소스 정리 |

**프로퍼티:**

| 프로퍼티 | 타입 | 설명 |
|----------|------|------|
| `agents` | `dict[str, Agent]` | 이름으로 에이전트를 조회하는 딕셔너리 |
| `agent_names` | `list[str]` | 에이전트 이름 목록 |

**흐름 DSL 문법:**

| 패턴 | 예시 | 설명 |
|------|------|------|
| 순차 | `"A -> B -> C"` | A 완료 후 B, B 완료 후 C 실행 |
| 병렬 | `"[A, B]"` | A와 B 동시 실행 |
| 혼합 | `"A -> [B, C] -> D"` | A 후 B/C 병렬, 그 후 D |

---

## WorkflowState

워크플로우 실행 중 에이전트 간에 전달되는 불변 상태 객체입니다.

```python
from agentchord.core.state import WorkflowState

state = WorkflowState(input="입력 텍스트")

# 상태 업데이트 (새 객체 반환)
new_state = state.with_output("처리된 결과")
new_state = state.with_context("key", "value")
new_state = state.with_result(agent_result)
new_state = state.with_error("에러 메시지")
```

**필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `input` | `str` | 워크플로우의 원본 입력 |
| `output` | `str \| None` | 현재 출력 (에이전트들이 업데이트) |
| `history` | `list[AgentResult]` | 모든 에이전트 실행 기록 |
| `context` | `dict[str, Any]` | 에이전트 간 공유 컨텍스트 데이터 |
| `current_agent` | `str \| None` | 현재 실행 중인 에이전트 이름 |
| `status` | `WorkflowStatus` | 현재 워크플로우 상태 |
| `error` | `str \| None` | 실패 시 에러 메시지 |

**메서드:**

| 메서드 | 반환값 | 설명 |
|--------|--------|------|
| `with_output(output: str)` | `WorkflowState` | 출력이 업데이트된 새 상태 반환 |
| `with_result(result: AgentResult)` | `WorkflowState` | 에이전트 결과가 기록에 추가된 새 상태 반환 |
| `with_context(key: str, value: Any)` | `WorkflowState` | 컨텍스트가 업데이트된 새 상태 반환 |
| `with_status(status: WorkflowStatus)` | `WorkflowState` | 상태가 업데이트된 새 상태 반환 |
| `with_error(error: str)` | `WorkflowState` | 실패 상태와 에러 메시지가 설정된 새 상태 반환 |

**프로퍼티:**

| 프로퍼티 | 타입 | 설명 |
|----------|------|------|
| `last_result` | `AgentResult \| None` | 가장 최근 에이전트 결과 |
| `effective_input` | `str` | 다음 에이전트의 입력 (output이 있으면 output, 없으면 input) |

---

## WorkflowResult

워크플로우 실행의 최종 결과입니다.

```python
result = await workflow.run("입력 텍스트")

print(result.output)            # 최종 출력
print(result.status)            # WorkflowStatus.COMPLETED
print(result.total_cost)        # 총 비용 (USD)
print(result.total_tokens)      # 총 토큰 수
print(result.total_duration_ms) # 총 실행 시간 (밀리초)
print(result.is_success)        # True/False
print(result.error)             # 실패 시 에러 메시지

for agent_result in result.agent_results:
    print(agent_result.output)
```

**필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `output` | `str` | 워크플로우의 최종 출력 |
| `state` | `WorkflowState` | 최종 워크플로우 상태 |
| `status` | `WorkflowStatus` | 최종 실행 상태 |

**프로퍼티:**

| 프로퍼티 | 타입 | 설명 |
|----------|------|------|
| `total_cost` | `float` | 모든 에이전트 비용의 합계 (USD) |
| `total_tokens` | `int` | 모든 에이전트가 사용한 총 토큰 수 |
| `total_duration_ms` | `int` | 총 실행 시간 (밀리초) |
| `agent_results` | `list[AgentResult]` | 에이전트 실행 결과 목록 (순서대로) |
| `usage` | `Usage` | 집계된 토큰 사용량 |
| `is_success` | `bool` | 워크플로우가 성공적으로 완료된 경우 True |
| `error` | `str \| None` | 실패 시 에러 메시지 |

---

## WorkflowStatus

워크플로우 실행 상태를 나타내는 열거형입니다.

```python
from agentchord.core.state import WorkflowStatus

if result.status == WorkflowStatus.COMPLETED:
    print("성공!")
elif result.status == WorkflowStatus.FAILED:
    print(f"실패: {result.error}")
```

**값:**

| 값 | 문자열 | 설명 |
|----|--------|------|
| `PENDING` | `"pending"` | 아직 시작되지 않음 |
| `RUNNING` | `"running"` | 실행 중 |
| `COMPLETED` | `"completed"` | 성공적으로 완료 |
| `FAILED` | `"failed"` | 에러로 실패 |
| `CANCELLED` | `"cancelled"` | 취소됨 |
