# 추적 API 레퍼런스

토큰 사용량, 비용 추적, 콜백 이벤트, 실행 트레이스에 대한 완전한 API 레퍼런스입니다.

---

## TokenUsage

단일 LLM 호출의 토큰 사용량입니다.

```python
from agentchord.tracking.models import TokenUsage

usage = TokenUsage(prompt_tokens=100, completion_tokens=50)
print(usage.total_tokens)  # 150

# 덧셈 지원
usage1 = TokenUsage(prompt_tokens=100, completion_tokens=50)
usage2 = TokenUsage(prompt_tokens=200, completion_tokens=80)
total = usage1 + usage2
print(total.total_tokens)  # 430
```

**필드:**

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `prompt_tokens` | `int` | `0` | 프롬프트 토큰 수 |
| `completion_tokens` | `int` | `0` | 컴플리션 토큰 수 |

**프로퍼티:**

| 프로퍼티 | 타입 | 설명 |
|----------|------|------|
| `total_tokens` | `int` | 프롬프트 + 컴플리션 토큰 합계 |

**연산자:**

| 연산자 | 설명 |
|--------|------|
| `+` | 두 `TokenUsage`의 각 필드를 합산하여 새 `TokenUsage` 반환 |

---

## CostEntry

단일 LLM 호출에 대한 비용 추적 항목입니다.

```python
from agentchord.tracking.models import CostEntry, TokenUsage

entry = CostEntry(
    model="gpt-4o-mini",
    usage=TokenUsage(prompt_tokens=100, completion_tokens=50),
    cost_usd=0.0000225,
    agent_name="researcher",
    metadata={"task": "search"},
)
```

**필드:**

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `timestamp` | `datetime` | 현재 시각 | 기록 시각 |
| `model` | `str` | 필수 | 사용된 모델 이름 |
| `usage` | `TokenUsage` | 필수 | 토큰 사용량 |
| `cost_usd` | `float` | 필수 | 비용 (USD) |
| `agent_name` | `str \| None` | `None` | 비용을 발생시킨 에이전트 이름 |
| `request_id` | `str \| None` | `None` | 요청 ID |
| `metadata` | `dict[str, Any]` | `{}` | 추가 메타데이터 |

---

## CostSummary

비용 항목들의 집계 요약입니다.

```python
from agentchord.tracking.models import CostSummary

# 항목 목록에서 생성
summary = CostSummary.from_entries(entries)
print(summary.total_cost_usd)  # 총 비용
print(summary.total_tokens)    # 총 토큰
print(summary.request_count)   # 요청 수
print(summary.by_model)        # {"gpt-4o-mini": 0.01, ...}
print(summary.by_agent)        # {"researcher": 0.005, ...}
```

**필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `total_cost_usd` | `float` | 총 비용 (USD) |
| `total_tokens` | `int` | 총 토큰 수 |
| `prompt_tokens` | `int` | 총 프롬프트 토큰 수 |
| `completion_tokens` | `int` | 총 컴플리션 토큰 수 |
| `request_count` | `int` | 총 요청 수 |
| `by_model` | `dict[str, float]` | 모델별 비용 합계 |
| `by_agent` | `dict[str, float]` | 에이전트별 비용 합계 |

**클래스 메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `from_entries` | `from_entries(entries: list[CostEntry]) -> CostSummary` | `CostSummary` | 항목 목록에서 집계 요약 생성 |

---

## CostTracker

LLM API 사용량과 비용을 추적하는 스레드 안전 클래스입니다.

```python
from agentchord.tracking.cost import CostTracker
from agentchord.tracking.models import CostEntry, TokenUsage, CostSummary

# 예산 제한 없이
tracker = CostTracker()

# 예산 제한과 콜백
def on_warning(summary: CostSummary, threshold: float):
    print(f"경고: 예산의 {threshold*100:.0f}% 사용됨 (${summary.total_cost_usd:.4f})")

def on_exceeded(summary: CostSummary):
    print(f"예산 초과! 총 비용: ${summary.total_cost_usd:.4f}")

tracker = CostTracker(
    budget_limit=5.0,                 # $5.00 예산
    warning_threshold=0.8,            # 80%에서 경고
    on_budget_warning=on_warning,
    on_budget_exceeded=on_exceeded,
    raise_on_exceed=False,            # 예외 미발생 (콜백만)
)

# 직접 기록
entry = CostEntry(
    model="gpt-4o-mini",
    usage=TokenUsage(prompt_tokens=100, completion_tokens=50),
    cost_usd=0.0000225,
)
tracker.track(entry)

# 자동 비용 계산 후 기록
entry = tracker.track_usage(
    model="gpt-4o-mini",
    usage=TokenUsage(prompt_tokens=200, completion_tokens=100),
    agent_name="researcher",
)

# 조회
print(tracker.total_cost)          # 총 비용
print(tracker.remaining_budget)    # 남은 예산
print(tracker.is_over_budget)      # 예산 초과 여부

summary = tracker.get_summary()    # CostSummary
by_model = tracker.get_by_model("gpt-4o-mini")
by_agent = tracker.get_by_agent("researcher")

# 초기화
final_summary = tracker.reset()

# 에이전트에 연결
from agentchord import Agent
agent = Agent(name="agent", role="...", cost_tracker=tracker)
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `budget_limit` | `float \| None` | `None` | 최대 예산 (USD). None이면 무제한 |
| `on_budget_warning` | `Callable[[CostSummary, float], None] \| None` | `None` | 경고 임계값 도달 시 콜백 |
| `warning_threshold` | `float` | `0.8` | 경고 임계값 (예산의 비율, 0~1) |
| `on_budget_exceeded` | `Callable[[CostSummary], None] \| None` | `None` | 예산 초과 시 콜백 |
| `raise_on_exceed` | `bool` | `False` | 예산 초과 시 `CostLimitExceededError` 발생 여부 |

**메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `track` | `track(entry: CostEntry) -> None` | `None` | 비용 항목 기록. 예산 임계값 체크 |
| `track_usage` | `track_usage(model: str, usage: TokenUsage, agent_name: str \| None = None, **metadata) -> CostEntry` | `CostEntry` | 비용을 자동 계산하여 기록 |
| `get_summary` | `get_summary() -> CostSummary` | `CostSummary` | 집계 비용 요약 반환 |
| `get_entries` | `get_entries() -> list[CostEntry]` | `list[CostEntry]` | 모든 기록 항목 반환 |
| `get_by_model` | `get_by_model(model: str) -> CostSummary` | `CostSummary` | 특정 모델의 비용 요약 반환 |
| `get_by_agent` | `get_by_agent(agent_name: str) -> CostSummary` | `CostSummary` | 특정 에이전트의 비용 요약 반환 |
| `reset` | `reset() -> CostSummary` | `CostSummary` | 추적기 초기화 후 마지막 요약 반환 |

**프로퍼티:**

| 프로퍼티 | 타입 | 설명 |
|----------|------|------|
| `budget_limit` | `float \| None` | 예산 한도 (USD) |
| `total_cost` | `float` | 현재까지 총 비용 (USD) |
| `remaining_budget` | `float \| None` | 남은 예산. 무제한이면 None |
| `is_over_budget` | `bool` | 예산 초과 여부 |

---

## CallbackEvent

콜백을 트리거하는 이벤트를 나타내는 열거형입니다.

```python
from agentchord.tracking.callbacks import CallbackEvent

# 에이전트 라이프사이클
CallbackEvent.AGENT_START   # 에이전트 실행 시작
CallbackEvent.AGENT_END     # 에이전트 실행 완료
CallbackEvent.AGENT_ERROR   # 에이전트 실행 오류

# LLM 상호작용
CallbackEvent.LLM_START     # LLM 호출 시작
CallbackEvent.LLM_END       # LLM 호출 완료
CallbackEvent.LLM_ERROR     # LLM 호출 오류

# 도구 사용
CallbackEvent.TOOL_START    # 도구 실행 시작
CallbackEvent.TOOL_END      # 도구 실행 완료
CallbackEvent.TOOL_ERROR    # 도구 실행 오류

# 워크플로우
CallbackEvent.WORKFLOW_START # 워크플로우 시작
CallbackEvent.WORKFLOW_END   # 워크플로우 완료
CallbackEvent.WORKFLOW_STEP  # 워크플로우 단계 완료

# 비용
CallbackEvent.COST_TRACKED   # 비용 기록됨
CallbackEvent.BUDGET_WARNING # 예산 경고
CallbackEvent.BUDGET_EXCEEDED # 예산 초과

# 오케스트레이션
CallbackEvent.ORCHESTRATION_START  # 팀 오케스트레이션 시작
CallbackEvent.ORCHESTRATION_END    # 팀 오케스트레이션 완료
CallbackEvent.AGENT_DELEGATED      # 작업 위임됨
CallbackEvent.AGENT_COMPLETED      # 에이전트 작업 완료
```

---

## CallbackContext

콜백에 전달되는 컨텍스트 데이터입니다.

```python
from agentchord.tracking.callbacks import CallbackContext, CallbackEvent
from datetime import datetime

def my_callback(ctx: CallbackContext) -> None:
    print(f"이벤트: {ctx.event}")            # CallbackEvent.AGENT_START
    print(f"시각: {ctx.timestamp}")          # datetime 객체
    print(f"에이전트: {ctx.agent_name}")     # "researcher"
    print(f"데이터: {ctx.data}")             # {"input": "쿼리", ...}
```

**필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `event` | `CallbackEvent` | 발생한 이벤트 타입 |
| `timestamp` | `datetime` | 이벤트 발생 시각 |
| `agent_name` | `str \| None` | 이벤트를 발생시킨 에이전트 이름 |
| `data` | `dict[str, Any]` | 이벤트별 추가 데이터 |

---

## CallbackManager

이벤트 콜백을 관리하는 매니저입니다. 동기/비동기 콜백을 모두 지원합니다.

```python
from agentchord.tracking.callbacks import CallbackManager, CallbackEvent, CallbackContext

manager = CallbackManager()

# 동기 콜백 등록
def on_agent_start(ctx: CallbackContext) -> None:
    print(f"에이전트 '{ctx.agent_name}' 시작. 입력: {ctx.data.get('input', '')[:50]}")

# 비동기 콜백 등록
async def on_llm_end(ctx: CallbackContext) -> None:
    tokens = ctx.data.get("tokens", 0)
    print(f"LLM 완료. 토큰 사용: {tokens}")

manager.register(CallbackEvent.AGENT_START, on_agent_start)
manager.register(CallbackEvent.LLM_END, on_llm_end)

# 모든 이벤트에 대한 글로벌 콜백
def log_all(ctx: CallbackContext) -> None:
    print(f"[{ctx.timestamp}] {ctx.event.value}")

manager.register_global(log_all)

# 콜백 해제
manager.unregister(CallbackEvent.LLM_END, on_llm_end)

# 이벤트 발생
await manager.emit(
    CallbackEvent.AGENT_START,
    agent_name="researcher",
    input="AI 트렌드 검색",
)

# 동기 발생 (sync 콜백만 호출)
manager.emit_sync(CallbackEvent.AGENT_START, agent_name="researcher")

# 정리
manager.clear()                               # 모든 콜백 해제
manager.clear(CallbackEvent.AGENT_START)      # 특정 이벤트 콜백만 해제

# 에이전트에 연결
from agentchord import Agent
agent = Agent(name="agent", role="...", callbacks=manager)
```

**메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `register` | `register(event: CallbackEvent, callback: AnyCallback) -> None` | `None` | 특정 이벤트에 콜백 등록 |
| `register_global` | `register_global(callback: AnyCallback) -> None` | `None` | 모든 이벤트에 대한 글로벌 콜백 등록 |
| `unregister` | `unregister(event: CallbackEvent, callback: AnyCallback) -> bool` | `bool` | 콜백 등록 해제. 성공 시 True |
| `unregister_global` | `unregister_global(callback: AnyCallback) -> bool` | `bool` | 글로벌 콜백 등록 해제. 성공 시 True |
| `emit` | `async emit(event: CallbackEvent, agent_name: str \| None = None, **data) -> None` | `None` | 이벤트를 발생시키고 등록된 모든 콜백 호출 |
| `emit_sync` | `emit_sync(event: CallbackEvent, agent_name: str \| None = None, **data) -> None` | `None` | 동기 방식으로 이벤트 발생 (sync 콜백만 호출) |
| `clear` | `clear(event: CallbackEvent \| None = None) -> None` | `None` | 콜백 정리. None이면 모든 콜백 해제 |

---

## TraceSpan

실행 트레이스의 단일 스팬입니다. 하나의 작업 단위(에이전트 실행, LLM 호출, 도구 실행 등)를 나타냅니다.

```python
from agentchord.telemetry.collector import TraceSpan
import time

span = TraceSpan(
    name="agent.researcher",
    kind="agent",
    attributes={"model": "gpt-4o-mini", "input": "검색 쿼리"},
)

span.add_event("tool_called", tool_name="search", args={"query": "AI"})
span.end(status="ok")  # 또는 "error"

print(span.duration_ms)  # 실행 시간 (밀리초)
print(span.to_dict())    # 딕셔너리로 변환
```

**필드 (데이터클래스):**

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `id` | `str` | 자동 UUID | 스팬 고유 ID |
| `parent_id` | `str \| None` | `None` | 부모 스팬 ID |
| `name` | `str` | `""` | 스팬 이름 |
| `kind` | `str` | `""` | 스팬 종류 ("agent", "llm", "tool", "workflow") |
| `start_time` | `float` | 현재 시각 | 시작 시각 (Unix 타임스탬프) |
| `end_time` | `float \| None` | `None` | 종료 시각 |
| `status` | `str` | `"running"` | 상태 ("running", "ok", "error") |
| `attributes` | `dict[str, Any]` | `{}` | 스팬 속성 |
| `events` | `list[dict]` | `[]` | 스팬 내 이벤트 목록 |

**프로퍼티:**

| 프로퍼티 | 타입 | 설명 |
|----------|------|------|
| `duration_ms` | `float \| None` | 실행 시간 (밀리초). 완료 전이면 None |

**메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `end` | `end(status: str = "ok") -> None` | `None` | 스팬을 완료로 표시 |
| `add_event` | `add_event(name: str, **attrs) -> None` | `None` | 스팬에 이벤트 추가 |
| `to_dict` | `to_dict() -> dict[str, Any]` | `dict` | 딕셔너리로 변환 |

---

## ExecutionTrace

에이전트 또는 워크플로우 실행의 완전한 트레이스입니다.

```python
from agentchord.telemetry.collector import ExecutionTrace, TraceSpan

trace = ExecutionTrace(name="researcher-run")

span = TraceSpan(name="agent.researcher", kind="agent")
trace.add_span(span)
trace.end()

print(trace.duration_ms)   # 총 실행 시간
print(trace.span_count)    # 스팬 수
print(trace.error_count)   # 에러 스팬 수

# JSON으로 변환
json_str = trace.to_json(indent=2)

# 파일로 저장/불러오기
trace.save("trace.json")
loaded = ExecutionTrace.load("trace.json")

# 딕셔너리로 변환/복원
data = trace.to_dict()
restored = ExecutionTrace.from_dict(data)
```

**필드 (데이터클래스):**

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `id` | `str` | 자동 UUID | 트레이스 고유 ID |
| `name` | `str` | `""` | 트레이스 이름 |
| `start_time` | `float` | 현재 시각 | 시작 시각 (Unix 타임스탬프) |
| `end_time` | `float \| None` | `None` | 종료 시각 |
| `spans` | `list[TraceSpan]` | `[]` | 모든 스팬 목록 |
| `metadata` | `dict[str, Any]` | `{}` | 추가 메타데이터 |

**프로퍼티:**

| 프로퍼티 | 타입 | 설명 |
|----------|------|------|
| `duration_ms` | `float \| None` | 총 실행 시간 (밀리초) |
| `span_count` | `int` | 총 스팬 수 |
| `error_count` | `int` | 에러 상태인 스팬 수 |

**메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `end` | `end() -> None` | `None` | 트레이스를 완료로 표시 |
| `add_span` | `add_span(span: TraceSpan) -> None` | `None` | 스팬 추가 |
| `to_dict` | `to_dict() -> dict[str, Any]` | `dict` | 딕셔너리로 변환 |
| `to_json` | `to_json(indent: int = 2) -> str` | `str` | JSON 문자열로 변환 |
| `save` | `save(path: str \| Path) -> None` | `None` | JSON 파일로 저장 |
| `from_dict` | `from_dict(data: dict) -> ExecutionTrace` | `ExecutionTrace` | 딕셔너리에서 복원 (클래스 메서드) |
| `load` | `load(path: str \| Path) -> ExecutionTrace` | `ExecutionTrace` | JSON 파일에서 로드 (클래스 메서드) |

---

## TraceCollector

Agent와 Workflow 실행에서 트레이스를 자동으로 수집하는 클래스입니다. 콜백 리스너로 등록되어 실행 이벤트를 캡처합니다.

```python
from agentchord.telemetry.collector import TraceCollector, export_traces_jsonl
from agentchord import Agent

# 트레이스 수집기 생성
collector = TraceCollector()

# 에이전트에 연결 (callback_manager 사용)
agent = Agent(
    name="researcher",
    role="...",
    callbacks=collector.callback_manager,
)

# 에이전트 실행
result = await agent.run("AI 트렌드 분석해줘")

# 트레이스 조회
trace = collector.get_last_trace()
print(f"실행 시간: {trace.duration_ms:.1f}ms")
print(f"스팬 수: {trace.span_count}")
print(f"에러 수: {trace.error_count}")

# 파일로 저장
trace.save("trace.json")

# 모든 트레이스 조회
all_traces = collector.traces
print(f"총 트레이스 수: {len(all_traces)}")

# JSONL로 내보내기 (여러 트레이스)
export_traces_jsonl(all_traces, "all_traces.jsonl")

# 초기화
collector.clear()
```

**프로퍼티:**

| 프로퍼티 | 타입 | 설명 |
|----------|------|------|
| `callback_manager` | `CallbackManager` | 에이전트/워크플로우에 연결할 콜백 매니저 |
| `traces` | `list[ExecutionTrace]` | 수집된 모든 트레이스 복사본 |

**메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `get_last_trace` | `get_last_trace() -> ExecutionTrace \| None` | `ExecutionTrace \| None` | 가장 최근 트레이스 반환 |
| `clear` | `clear() -> None` | `None` | 수집된 모든 트레이스 삭제 |

---

## export_traces_jsonl

여러 트레이스를 JSONL 형식으로 파일에 내보내는 유틸리티 함수입니다.

```python
from agentchord.telemetry.collector import export_traces_jsonl

traces = collector.traces
export_traces_jsonl(traces, "traces.jsonl")
# 결과: 각 줄이 하나의 트레이스 JSON 객체
```

**파라미터:**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `traces` | `list[ExecutionTrace]` | 내보낼 트레이스 목록 |
| `path` | `str \| Path` | 출력 파일 경로 |
