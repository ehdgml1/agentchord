# 오케스트레이션 API 레퍼런스

AgentChord 멀티 에이전트 오케스트레이션에 대한 완전한 API 레퍼런스입니다. 팀 조율, 에이전트 간 메시징, 공유 상태 관리, 오케스트레이션 전략을 다룹니다.

---

## 타입

### MessageType

에이전트 간 교환되는 메시지 타입을 나타내는 Enum입니다.

```python
from agentchord.orchestration.types import MessageType

print(MessageType.TASK)      # "task"
print(MessageType.RESULT)    # "result"
print(MessageType.RESPONSE)  # "response"
print(MessageType.BROADCAST) # "broadcast"
```

| 값 | 설명 |
|----|------|
| `TASK` | 작업 할당 메시지 |
| `RESULT` | 작업 결과 메시지 |
| `RESPONSE` | 응답 메시지 |
| `BROADCAST` | 전체 에이전트에 전달되는 브로드캐스트 메시지 |

---

### TeamRole

팀 내 에이전트의 역할을 나타내는 Enum입니다.

```python
from agentchord.orchestration.types import TeamRole

print(TeamRole.COORDINATOR) # "coordinator"
print(TeamRole.WORKER)      # "worker"
print(TeamRole.REVIEWER)    # "reviewer"
print(TeamRole.SPECIALIST)  # "specialist"
```

| 값 | 설명 |
|----|------|
| `COORDINATOR` | 다른 에이전트를 조율하는 코디네이터 |
| `WORKER` | 일반 작업을 수행하는 워커 |
| `REVIEWER` | 결과를 검토하는 리뷰어 |
| `SPECIALIST` | 특정 분야 전문 에이전트 |

---

### OrchestrationStrategy

멀티 에이전트 오케스트레이션 전략을 나타내는 Enum입니다.

```python
from agentchord.orchestration.types import OrchestrationStrategy

print(OrchestrationStrategy.COORDINATOR)  # "coordinator"
print(OrchestrationStrategy.ROUND_ROBIN)  # "round_robin"
print(OrchestrationStrategy.DEBATE)       # "debate"
print(OrchestrationStrategy.MAP_REDUCE)   # "map_reduce"
```

| 값 | 설명 |
|----|------|
| `COORDINATOR` | 코디네이터가 도구 호출로 워커에게 위임 |
| `ROUND_ROBIN` | 모든 에이전트가 순차적으로 실행됨 |
| `DEBATE` | 에이전트들이 토론하며 합의 도달 |
| `MAP_REDUCE` | 작업을 병렬 처리 후 축약 |
| `SEQUENTIAL` | ⚠️ Deprecated. `ROUND_ROBIN` 사용 권장 |

---

### AgentMessage

에이전트 간 교환되는 구조화된 메시지입니다. Pydantic 모델입니다.

```python
from agentchord.orchestration.types import AgentMessage, MessageType

msg = AgentMessage(
    sender="researcher",
    recipient="writer",
    message_type=MessageType.TASK,
    content="다음 데이터를 분석해주세요: ...",
    metadata={"priority": "high"},
)

print(msg.id)        # 자동 생성 UUID
print(msg.timestamp) # 생성 시각 (UTC)
```

**필드:**

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `id` | `str` | 자동 UUID | 메시지 고유 ID |
| `sender` | `str` | 필수 | 발신자 에이전트 이름 |
| `recipient` | `str \| None` | `None` | 수신자 에이전트 이름. None이면 브로드캐스트 |
| `message_type` | `MessageType` | 필수 | 메시지 타입 |
| `content` | `str` | 필수 | 메시지 내용 |
| `metadata` | `dict[str, Any]` | `{}` | 추가 메타데이터 |
| `parent_id` | `str \| None` | `None` | 부모 메시지 ID (스레드 추적용) |
| `timestamp` | `datetime` | 현재 UTC | 메시지 생성 시각 |

---

### TeamMember

팀 내 에이전트의 역할과 능력을 정의하는 Pydantic 모델입니다.

```python
from agentchord.orchestration.types import TeamMember, TeamRole

member = TeamMember(
    name="research-agent",
    role=TeamRole.SPECIALIST,
    capabilities=["web_search", "summarization"],
)
```

**필드:**

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `name` | `str` | 필수 | 에이전트 이름 |
| `role` | `TeamRole` | `TeamRole.WORKER` | 팀 내 역할 |
| `capabilities` | `list[str]` | `[]` | 에이전트 능력 목록 (코디네이터 힌트용) |
| `agent_config` | `dict[str, Any]` | `{}` | 추가 설정 |

---

### TeamEvent

팀 실행 중 스트리밍을 위해 발생하는 이벤트 Pydantic 모델입니다.

```python
from agentchord.orchestration.types import TeamEvent

event = TeamEvent(
    type="agent_start",
    sender="coordinator",
    recipient="worker-1",
    content="작업 시작",
    round=1,
)
```

**필드:**

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `type` | `str` | 필수 | 이벤트 타입 (`"team_start"`, `"agent_message"`, `"agent_result"`, `"team_complete"` 등) |
| `sender` | `str \| None` | `None` | 발신자 |
| `recipient` | `str \| None` | `None` | 수신자 |
| `content` | `str` | `""` | 이벤트 내용 |
| `round` | `int` | `0` | 현재 라운드 번호 |
| `timestamp` | `datetime` | 현재 UTC | 이벤트 발생 시각 |
| `metadata` | `dict[str, Any]` | `{}` | 추가 메타데이터 |

---

### AgentOutput

팀 실행 내 단일 에이전트의 출력 결과 Pydantic 모델입니다.

**필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `agent_name` | `str` | 에이전트 이름 |
| `role` | `TeamRole` | 에이전트 역할 |
| `output` | `str` | 에이전트 출력 텍스트 |
| `tokens` | `int` | 사용된 토큰 수 |
| `cost` | `float` | 비용 (USD) |
| `duration_ms` | `int` | 실행 시간 (밀리초) |

---

### TeamResult

멀티 에이전트 팀 실행의 최종 결과 Pydantic 모델입니다.

```python
result = await team.run("블로그 글을 작성해줘")

print(result.output)        # 최종 합성된 출력
print(result.total_cost)    # 총 비용 (USD)
print(result.total_tokens)  # 총 토큰 수
print(result.rounds)        # 총 라운드 수
print(result.strategy)      # 사용된 전략 이름
print(result.duration_ms)   # 총 실행 시간 (ms)

# 에이전트별 출력
for name, output in result.agent_outputs.items():
    print(f"{name}: {output.output[:100]}...")
```

**필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `output` | `str` | 최종 합성 출력 |
| `agent_outputs` | `dict[str, AgentOutput]` | 에이전트별 출력 (이름 → AgentOutput) |
| `messages` | `list[AgentMessage]` | 전체 메시지 히스토리 |
| `total_cost` | `float` | 총 비용 (USD) |
| `total_tokens` | `int` | 총 토큰 수 |
| `rounds` | `int` | 총 라운드 수 |
| `duration_ms` | `int` | 총 실행 시간 (밀리초) |
| `strategy` | `str` | 사용된 전략 이름 |
| `team_name` | `str` | 팀 이름 |

---

## AgentTeam

다양한 전략으로 여러 에이전트를 협력시키는 팀 클래스입니다.

```python
from agentchord import Agent
from agentchord.orchestration import AgentTeam

researcher = Agent(name="researcher", role="리서치 전문가", model="gpt-4o")
writer = Agent(name="writer", role="콘텐츠 작성자", model="gpt-4o")

team = AgentTeam(
    name="content-team",
    members=[researcher, writer],
    strategy="coordinator",
    max_rounds=10,
)

result = await team.run("AI 에이전트에 관한 블로그 글을 작성해줘")
print(result.output)
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `name` | `str` | 필수 | 팀 이름 |
| `members` | `list[Agent \| TeamMember]` | 필수 | 팀 멤버 목록 (Agent 인스턴스 또는 TeamMember) |
| `coordinator` | `Agent \| None` | `None` | 전용 코디네이터 에이전트 (coordinator 전략용) |
| `strategy` | `str \| OrchestrationStrategy` | `"coordinator"` | 오케스트레이션 전략 |
| `shared_context` | `SharedContext \| None` | `None` | 에이전트 간 공유 상태 (None이면 자동 생성) |
| `message_bus` | `MessageBus \| None` | `None` | 에이전트 간 메시지 버스 (None이면 자동 생성) |
| `max_rounds` | `int` | `10` | 최대 오케스트레이션 라운드 수 |
| `callbacks` | `CallbackManager \| None` | `None` | 이벤트 알림용 콜백 매니저 |
| `enable_consult` | `bool` | `False` | 워커가 실행 중 동료에게 협의 요청 가능 여부 |
| `max_consult_depth` | `int` | `1` | 협의 체인의 최대 깊이 |

**프로퍼티:**

| 프로퍼티 | 타입 | 설명 |
|----------|------|------|
| `members` | `list[TeamMember]` | 팀 멤버 목록 |
| `agents` | `dict[str, Agent]` | 에이전트 이름 → Agent 인스턴스 딕셔너리 |
| `strategy` | `str` | 현재 전략 이름 |
| `shared_context` | `SharedContext` | 팀의 공유 컨텍스트 |
| `message_bus` | `MessageBus` | 팀의 메시지 버스 |

**메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `run` | `async run(task: str) -> TeamResult` | `TeamResult` | 팀을 실행하여 작업을 처리 |
| `stream` | `async stream(task: str) -> AsyncIterator[TeamEvent]` | `AsyncIterator[TeamEvent]` | 실행 후 이벤트를 순차적으로 yield (완료 후 재생 방식) |
| `run_sync` | `run_sync(task: str) -> TeamResult` | `TeamResult` | 동기 컨텍스트에서 실행하기 위한 편의 메서드 |
| `close` | `async close() -> None` | `None` | 팀과 모든 멤버 에이전트 종료 (멱등성 보장) |

**비동기 컨텍스트 매니저 지원:**

```python
async with AgentTeam(name="team", members=[...]) as team:
    result = await team.run("작업...")
# 자동으로 team.close() 호출
```

---

## 오케스트레이션 전략

### coordinator 전략

코디네이터가 도구 호출을 통해 워커에게 작업을 위임하는 전략입니다. 코디네이터는 동적으로 생성된 도구(`delegate_to_{worker}`)를 통해 자연스럽게 위임합니다.

```python
coordinator = Agent(name="coordinator", role="팀 조율자", model="gpt-4o")
worker1 = Agent(name="researcher", role="리서처", model="gpt-4o-mini")
worker2 = Agent(name="writer", role="작성자", model="gpt-4o-mini")

team = AgentTeam(
    name="team",
    members=[worker1, worker2],
    coordinator=coordinator,
    strategy="coordinator",
)
```

- 코디네이터가 별도 제공되지 않으면 첫 번째 멤버가 코디네이터 역할
- 코디네이터는 LLM이 자연스럽게 도구 호출로 위임하는 방식
- 복잡한 작업 분배에 적합

---

### round_robin 전략

모든 에이전트가 순차적으로 작업을 수행하는 전략입니다.

```python
team = AgentTeam(
    name="team",
    members=[agent1, agent2, agent3],
    strategy="round_robin",
    max_rounds=3,  # 각 에이전트가 3번씩 실행
)
```

- 각 에이전트가 이전 에이전트의 출력을 입력으로 받음
- 순서가 중요한 파이프라인 작업에 적합

---

### debate 전략

에이전트들이 토론을 통해 합의에 도달하는 전략입니다.

```python
pro_agent = Agent(name="pro", role="찬성 입장 전문가", model="gpt-4o")
con_agent = Agent(name="con", role="반대 입장 전문가", model="gpt-4o")
moderator = Agent(name="moderator", role="진행자 및 합성자", model="gpt-4o")

team = AgentTeam(
    name="debate-team",
    members=[pro_agent, con_agent],
    coordinator=moderator,
    strategy="debate",
    max_rounds=3,
)
```

- 에이전트들이 서로의 입장을 반박하며 토론
- 입장이 수렴되면 조기 종료
- 진행자가 최종 합성 담당

---

### map_reduce 전략

작업을 분할 처리(map) 후 결과를 통합(reduce)하는 전략입니다.

```python
team = AgentTeam(
    name="analysis-team",
    members=[agent1, agent2, agent3],
    strategy="map_reduce",
)
```

- map 단계: 각 에이전트가 병렬로 작업 처리
- reduce 단계: 코디네이터가 결과를 합성
- 대용량 데이터 처리, 병렬 리서치에 적합

---

## MessageBus

에이전트 간 비동기 메시지 라우팅을 담당합니다. 각 등록된 에이전트는 전용 `asyncio.Queue`를 가집니다.

```python
from agentchord.orchestration import MessageBus
from agentchord.orchestration.types import AgentMessage, MessageType

bus = MessageBus(max_history=10000)

# 에이전트 등록
bus.register("researcher")
bus.register("writer")

# 메시지 전송
await bus.send(AgentMessage(
    sender="researcher",
    recipient="writer",
    message_type=MessageType.TASK,
    content="이 데이터를 처리해줘",
))

# 메시지 수신
msg = await bus.receive("writer", timeout=5.0)

# 브로드캐스트
await bus.broadcast("coordinator", "모든 에이전트에게 공지합니다")
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `callbacks` | `CallbackManager \| None` | `None` | 메시지 추적용 콜백 매니저 |
| `max_history` | `int` | `10000` | 보관할 최대 메시지 수. 0이면 무제한 |

**프로퍼티:**

| 프로퍼티 | 타입 | 설명 |
|----------|------|------|
| `registered_agents` | `list[str]` | 등록된 에이전트 이름 목록 |
| `message_count` | `int` | 전송된 총 메시지 수 |
| `max_history` | `int` | 최대 히스토리 수 |

**메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `register` | `register(agent_name: str) -> None` | `None` | 메시지 수신을 위한 에이전트 등록 |
| `unregister` | `unregister(agent_name: str) -> None` | `None` | 에이전트 등록 해제 |
| `send` | `async send(message: AgentMessage) -> None` | `None` | 특정 에이전트 또는 브로드캐스트로 전송 |
| `receive` | `async receive(agent_name: str, timeout: float \| None = None) -> AgentMessage \| None` | `AgentMessage \| None` | 다음 메시지 수신. timeout 기본값 30.0초 |
| `broadcast` | `async broadcast(sender: str, content: str, metadata: dict \| None = None) -> AgentMessage` | `AgentMessage` | 모든 에이전트에 브로드캐스트 전송 |
| `get_history` | `get_history() -> list[AgentMessage]` | `list[AgentMessage]` | 전체 메시지 히스토리 반환 |
| `get_agent_messages` | `get_agent_messages(agent_name: str) -> list[AgentMessage]` | `list[AgentMessage]` | 특정 에이전트 관련 메시지 반환 |
| `pending_count` | `pending_count(agent_name: str) -> int` | `int` | 에이전트의 미수신 메시지 수 |
| `clear` | `clear() -> None` | `None` | 모든 히스토리와 큐 초기화 |

---

## SharedContext

멀티 에이전트 협업을 위한 스레드 안전 공유 상태 관리 클래스입니다.

```python
from agentchord.orchestration import SharedContext

ctx = SharedContext(initial={"topic": "AI 에이전트"}, max_history=10000)

# 읽기/쓰기 (asyncio.Lock으로 보호)
await ctx.set("findings", "분석 결과...", agent="researcher")
value = await ctx.get("findings")

# 다중 업데이트
await ctx.update({"key1": "val1", "key2": "val2"}, agent="worker")

# 삭제
deleted = await ctx.delete("findings", agent="coordinator")  # True/False 반환

# 스냅샷
snapshot = await ctx.snapshot_async()  # 동시성 안전
snapshot = ctx.snapshot()              # ⚠️ 비동기 안전하지 않음 (편의용)

# 히스토리
history = await ctx.get_history()         # 전체 업데이트 히스토리
my_updates = await ctx.get_agent_updates("researcher")
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `initial` | `dict[str, Any] \| None` | `None` | 초기 데이터 |
| `max_history` | `int` | `10000` | 최대 히스토리 항목 수. 0이면 무제한 |

**프로퍼티:**

| 프로퍼티 | 타입 | 설명 |
|----------|------|------|
| `size` | `int` | 현재 키 수 |
| `update_count` | `int` | 총 업데이트 수 |
| `max_history` | `int` | 최대 히스토리 항목 수 |

**메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `get` | `async get(key: str, default: Any = None) -> Any` | `Any` | 값 조회 (딥 카피 반환) |
| `set` | `async set(key: str, value: Any, agent: str = "") -> None` | `None` | 값 설정 |
| `update` | `async update(data: dict[str, Any], agent: str = "") -> None` | `None` | 다중 값 업데이트 |
| `delete` | `async delete(key: str, agent: str = "") -> bool` | `bool` | 키 삭제. 성공 시 True |
| `has` | `async has(key: str) -> bool` | `bool` | 키 존재 여부 확인 |
| `keys` | `async keys() -> list[str]` | `list[str]` | 모든 키 목록 반환 |
| `snapshot` | `snapshot() -> dict[str, Any]` | `dict` | 현재 상태의 딥 카피 반환 (비동기 안전하지 않음) |
| `snapshot_async` | `async snapshot_async() -> dict[str, Any]` | `dict` | 동시성 안전한 딥 카피 반환 |
| `get_history` | `async get_history() -> list[ContextUpdate]` | `list[ContextUpdate]` | 전체 업데이트 히스토리 반환 |
| `get_agent_updates` | `async get_agent_updates(agent: str) -> list[ContextUpdate]` | `list[ContextUpdate]` | 특정 에이전트의 업데이트 히스토리 반환 |
| `clear` | `async clear() -> None` | `None` | 모든 데이터와 히스토리 초기화 |

### ContextUpdate

컨텍스트 변경 기록 Pydantic 모델입니다.

**필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `key` | `str` | 변경된 키 |
| `value` | `Any` | 설정된 값 (삭제 시 `None`) |
| `agent` | `str` | 변경을 수행한 에이전트 이름 |
| `timestamp` | `datetime` | 변경 시각 (UTC) |
| `operation` | `str` | 작업 종류 (`"set"` 또는 `"delete"`) |

---

## 워커 협의(Consult) 기능

`enable_consult=True`로 설정하면 워커 에이전트가 실행 중 동료에게 협의를 요청할 수 있습니다.

```python
team = AgentTeam(
    name="consult-team",
    members=[agent1, agent2, agent3],
    strategy="round_robin",
    enable_consult=True,
    max_consult_depth=1,  # 협의 체인 최대 깊이
)
```

- `enable_consult=True`: 각 에이전트에 `consult_{peer}` 도구가 동적으로 주입됨
- `max_consult_depth`: 협의 체인 깊이 제한 (depth > 1은 현재 비작동)
- round_robin, debate, map_reduce 전략에서 지원

---

## 종합 사용 예제

### 코디네이터 전략

```python
import asyncio
from agentchord import Agent
from agentchord.orchestration import AgentTeam

async def main():
    # 팀 멤버 정의
    coordinator = Agent(
        name="coordinator",
        role="팀 리더. 작업을 분석하고 적절한 전문가에게 위임합니다.",
        model="gpt-4o",
    )
    researcher = Agent(
        name="researcher",
        role="웹 검색 및 데이터 수집 전문가",
        model="gpt-4o-mini",
    )
    analyst = Agent(
        name="analyst",
        role="데이터 분석 및 인사이트 도출 전문가",
        model="gpt-4o-mini",
    )

    # 팀 구성
    async with AgentTeam(
        name="research-team",
        members=[researcher, analyst],
        coordinator=coordinator,
        strategy="coordinator",
        max_rounds=5,
    ) as team:
        result = await team.run("2025년 AI 에이전트 시장 동향을 분석해주세요")

    print(f"출력: {result.output}")
    print(f"총 비용: ${result.total_cost:.4f}")
    print(f"총 토큰: {result.total_tokens}")
    print(f"라운드: {result.rounds}")

asyncio.run(main())
```

### 토론 전략 + 스트리밍

```python
from agentchord import Agent
from agentchord.orchestration import AgentTeam

pro = Agent(name="pro", role="기술 낙관론자 - AI의 긍정적 영향을 주장", model="gpt-4o")
con = Agent(name="con", role="기술 비판론자 - AI의 위험성을 경고", model="gpt-4o")
moderator = Agent(name="moderator", role="공정한 진행자 - 논점을 합성", model="gpt-4o")

team = AgentTeam(
    name="debate-team",
    members=[pro, con],
    coordinator=moderator,
    strategy="debate",
    max_rounds=3,
)

# 스트리밍으로 이벤트 수신
async for event in team.stream("AI가 일자리를 빼앗을까요?"):
    print(f"[{event.type}] {event.sender}: {event.content[:100]}")
```

### Map-Reduce 전략

```python
from agentchord import Agent
from agentchord.orchestration import AgentTeam

# 병렬 리서처들
agents = [
    Agent(name=f"researcher-{i}", role=f"리서처 {i}", model="gpt-4o-mini")
    for i in range(3)
]
synthesizer = Agent(name="synthesizer", role="결과 통합 전문가", model="gpt-4o")

team = AgentTeam(
    name="parallel-research",
    members=agents,
    coordinator=synthesizer,
    strategy="map_reduce",
)

result = await team.run("삼성, LG, SK의 2025년 AI 전략을 각각 분석해주세요")
```

### 공유 컨텍스트 활용

```python
from agentchord.orchestration import AgentTeam, SharedContext

# 초기 데이터로 컨텍스트 설정
shared = SharedContext(initial={
    "research_topic": "양자 컴퓨팅",
    "depth": "중급",
})

team = AgentTeam(
    name="team",
    members=[agent1, agent2],
    shared_context=shared,
    strategy="round_robin",
)

result = await team.run("주어진 주제로 보고서 작성")

# 에이전트가 설정한 컨텍스트 조회
findings = await shared.get("findings")
history = await shared.get_history()
```
