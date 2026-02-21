# 멀티에이전트 오케스트레이션 가이드

AgentChord의 오케스트레이션 시스템은 여러 에이전트가 구조화된 조율 전략을 통해 복잡한 작업을 협력하여 수행할 수 있게 합니다. 단일 에이전트 워크플로우와 달리, 멀티에이전트 오케스트레이션은 에이전트 간 통신, 역할 전문화, 창발적 문제 해결 패턴을 도입합니다.

## 빠른 시작

coordinator 전략을 사용한 기본 멀티에이전트 팀:

```python
from agentchord import Agent, AgentTeam

# 전문 에이전트 정의
researcher = Agent(
    name="researcher",
    role="정보를 수집하고 분석하는 리서치 전문가",
    model="gpt-4o-mini",
)
writer = Agent(
    name="writer",
    role="매력적인 텍스트를 만드는 콘텐츠 작가",
    model="gpt-4o-mini",
)

# 조율된 팀 생성
team = AgentTeam(
    name="content-team",
    members=[researcher, writer],
    strategy="coordinator",
    max_rounds=5,
)

# 작업 실행
result = await team.run("AI 안전성에 대한 블로그 포스트 작성해줘")
print(result.output)  # 최종 합성 출력
print(f"비용: ${result.total_cost:.4f}")
print(f"라운드: {result.rounds}")
```

## 핵심 개념

### AgentTeam

`AgentTeam`은 여러 에이전트가 협력하는 오케스트레이션 컨테이너입니다. 제공하는 기능:

- **전략 선택**: coordinator, round_robin, debate, map_reduce 중 선택
- **메시지 라우팅**: `MessageBus`를 통한 구조화된 에이전트 간 통신
- **공유 상태**: 에이전트 간 교차 데이터 공유를 위한 스레드 안전한 `SharedContext`
- **비용 집계**: 모든 에이전트에 걸친 자동 토큰 및 비용 추적
- **라이프사이클 관리**: 리소스 정리를 위한 비동기 컨텍스트 관리자

```python
team = AgentTeam(
    name="research-team",
    members=[agent1, agent2, agent3],
    strategy="coordinator",
    max_rounds=10,
    enable_consult=False,     # 에이전트 간 컨설트 활성화 여부
    max_consult_depth=1,      # 컨설트 체인 최대 깊이
)

async with team:
    result = await team.run("시장 트렌드 분석해줘")
```

### TeamResult

`run()` 메서드는 `TeamResult`를 반환합니다:

| 속성 | 타입 | 설명 |
|------|------|------|
| `output` | str | 최종 합성 출력 |
| `agent_outputs` | dict[str, AgentOutput] | 에이전트별 개별 출력 |
| `messages` | list[AgentMessage] | 교환된 모든 메시지 |
| `total_cost` | float | 전체 비용 합계 |
| `total_tokens` | int | 전체 토큰 합계 |
| `rounds` | int | 실행된 라운드 수 |
| `duration_ms` | int | 전체 실행 시간 |
| `strategy` | str | 사용된 전략 이름 |

### TeamMember

팀 내 각 에이전트는 역할로 전문성을 정의합니다:

```python
from agentchord.orchestration.types import TeamMember, TeamRole

member = TeamMember(
    name="analyst",
    role=TeamRole.SPECIALIST,
    capabilities=["data_analysis", "visualization"],
    agent_config={"temperature": 0.2},
)
```

**역할:**
- `COORDINATOR`: 작업 위임을 조율
- `WORKER`: 할당된 작업 실행
- `REVIEWER`: 출력 검증
- `SPECIALIST`: 도메인별 전문성

### MessageBus

`MessageBus`는 에이전트 간 비동기 pub/sub 메시징을 제공합니다:

```python
from agentchord.orchestration.message_bus import MessageBus
from agentchord.orchestration.types import AgentMessage, MessageType

bus = MessageBus()
bus.register("agent-1")
bus.register("agent-2")

# 지향된 메시지 전송
msg = AgentMessage(
    sender="agent-1",
    recipient="agent-2",
    message_type=MessageType.TASK,
    content="이 데이터셋 분석해줘",
)
await bus.send(msg)

# 메시지 수신
received = await bus.receive("agent-2")

# 브로드캐스트 (모든 에이전트에게)
await bus.broadcast(sender="coordinator", content="작업 완료")

# 히스토리 조회
history = bus.get_history()
```

**메시지 타입:**
- `TASK`: 작업 할당
- `RESULT`: 작업 완료
- `RESPONSE`: 쿼리에 대한 답변
- `BROADCAST`: 모든 에이전트에게 알림

### SharedContext

동시 에이전트 접근을 위한 스레드 안전한 공유 상태:

```python
from agentchord.orchestration.shared_context import SharedContext

ctx = SharedContext(initial={"project": "AI Research"})

# 스레드 안전한 쓰기
await ctx.set("findings", research_data, agent="researcher")
await ctx.update({"status": "in_progress", "version": 2}, agent="coordinator")

# 스레드 안전한 읽기 (깊은 복사 반환)
findings = await ctx.get("findings")

# 존재 여부 확인
if await ctx.has("findings"):
    keys = await ctx.keys()

# 수정 히스토리 조회
history = ctx.get_history()
for update in history:
    print(f"{update.agent} {update.operation} {update.key} at {update.timestamp}")
```

## 오케스트레이션 전략

AgentChord는 다양한 협력 패턴에 최적화된 네 가지 전략을 제공합니다.

### Coordinator 전략

**패턴**: 중앙 코디네이터가 전문 워커에게 서브작업을 위임.

**적합한 경우**: 전문 지식이 필요한 복잡한 작업, 계층적 워크플로우.

**동작 방식**:
1. 코디네이터 에이전트가 작업을 분석
2. 도구 호출을 통해 적절한 전문가에게 서브작업 위임
3. 결과를 집계해 최종 출력 생성

```python
from agentchord import Agent, AgentTeam

# 코디네이터 정의
coordinator = Agent(
    name="coordinator",
    role="전문가에게 위임하는 작업 조율자",
    model="gpt-4o",
)

# 전문가 정의
data_analyst = Agent(
    name="analyst",
    role="데이터 분석 전문가",
    model="gpt-4o-mini",
)
report_writer = Agent(
    name="writer",
    role="보고서 작성 전문가",
    model="gpt-4o-mini",
)

team = AgentTeam(
    name="analysis-team",
    members=[data_analyst, report_writer],
    coordinator=coordinator,
    strategy="coordinator",
    max_rounds=8,
)

result = await team.run("4분기 매출 데이터 분석하고 임원 요약 작성해줘")
```

**핵심 혁신**: 도구로서의 위임(Delegation-as-tools) 패턴. 코디네이터가 각 전문가를 호출하는 도구 함수를 받아 자연어로 위임 결정을 내립니다.

### Round Robin 전략

**패턴**: 에이전트가 순서대로 작업을 처리.

**적합한 경우**: 반복적 개선, 조립 라인 워크플로우, 점진적 향상.

**동작 방식**:
1. 첫 번째 에이전트가 작업 시작
2. 각 에이전트가 이전 에이전트의 출력을 입력으로 받음
3. 마지막 에이전트가 최종 합성 생성

```python
team = AgentTeam(
    name="refinement-team",
    members=[drafter, editor, reviewer],
    strategy="round_robin",
    max_rounds=3,
)

result = await team.run("제품 공지 작성해줘")
# drafter → editor → reviewer → 최종 출력
```

**라운드**: 모든 에이전트를 통한 완전한 순환이 하나의 라운드입니다. `max_rounds=3`에 3명의 에이전트가 있으면 각 에이전트가 정확히 한 번 실행됩니다.

### Debate 전략

**패턴**: 에이전트가 반대 관점을 제시하고 합의를 합성.

**적합한 경우**: 의사결정 분석, 위험 평가, 다양한 관점을 가진 창의적 브레인스토밍.

**동작 방식**:
1. 각 에이전트가 작업을 독립적으로 분석
2. 에이전트가 관점을 동시에 제시
3. 관점이 균형 잡힌 결론으로 합성됨

```python
optimist = Agent(
    name="optimist",
    role="기회와 이점을 식별",
    model="gpt-4o-mini",
)
skeptic = Agent(
    name="skeptic",
    role="위험과 과제를 식별",
    model="gpt-4o-mini",
)

team = AgentTeam(
    name="decision-analysis",
    members=[optimist, skeptic],
    strategy="debate",
    max_rounds=2,
)

result = await team.run("공급망 추적에 블록체인을 도입해야 하나요?")
```

**라운드**: 각 라운드는 각 토론자로부터 하나의 기여로 구성됩니다. `max_rounds=2`이면 합성 전 2번의 교환이 이루어집니다.

### Map-Reduce 전략

**패턴**: 병렬 작업 분해(map) 후 결과 집계(reduce).

**적합한 경우**: 데이터 처리, 병렬 분석, 분할 정복 문제.

**동작 방식**:
1. 작업이 독립적인 서브작업으로 분할됨
2. 워커가 서브작업을 병렬로 처리 (map 단계)
3. 결과가 최종 출력으로 집계됨 (reduce 단계)

```python
workers = [
    Agent(name=f"worker-{i}", role=f"프로세서 {i}", model="gpt-4o-mini")
    for i in range(4)
]

team = AgentTeam(
    name="data-processors",
    members=workers,
    strategy="map_reduce",
    max_rounds=1,
)

result = await team.run("고객 리뷰 1000건 요약해줘")
# 각 워커가 약 250개씩 병렬 처리, 결과 병합
```

**성능**: map 단계가 병렬 실행되므로 독립적인 서브작업의 실제 시간이 크게 단축됩니다.

## 전략 비교

| 전략 | 통신 패턴 | 병렬화 | 최적 사용 사례 |
|------|----------|--------|--------------|
| **Coordinator** | 허브-스포크 (도구) | 코디네이터를 통해 순차 실행 | 전문성 라우팅이 필요한 복잡한 계층적 작업 |
| **Round Robin** | 순차 파이프라인 | 없음 (선형 체인) | 반복적 개선, 편집 워크플로우 |
| **Debate** | 피어-투-피어 | 에이전트 병렬 실행 | 의사결정 분석, 다관점 합성 |
| **Map-Reduce** | 분산-수집 | map 단계 완전 병렬 | 데이터 처리, 분할 정복 문제 |

## 도구로서의 위임 패턴

coordinator 전략은 **도구 호출**을 통한 위임을 구현합니다. 이는 자연어로 작업 라우팅을 가능하게 하는 핵심 혁신입니다.

**동작 방식:**

1. 코디네이터 에이전트가 각 전문가에 대한 도구를 받음:
   ```python
   def delegate_to_analyst(subtask: str) -> str:
       """데이터 분석 서브작업을 analyst 전문가에게 위임."""
       return analyst.run_sync(subtask)
   ```

2. 코디네이터가 LLM 추론으로 언제, 어떻게 위임할지 결정:
   ```
   사용자: "매출 분석하고 보고서 작성해줘"
   코디네이터: delegate_to_analyst()로 데이터를 분석하고,
               그 다음 delegate_to_writer()로 보고서를 작성하겠습니다.
   ```

3. 도구 실행이 서브작업을 자동으로 전문가에게 라우팅.

**장점:**
- 하드코딩된 라우팅 로직 없음
- 코디네이터가 작업 복잡성에 따라 위임 방식 적응
- 의존성의 자연스러운 처리 (작성 전 분석)
- 다단계 워크플로우의 창발적 생성

## 스트리밍 팀 실행

팀 실행 중 실시간 업데이트 스트리밍:

```python
async for event in team.stream("경쟁사 현황 분석해줘"):
    if event.type == "team_start":
        print(f"시작: {event.content}")
    elif event.type == "agent_message":
        print(f"[{event.sender} → {event.recipient}] {event.content}")
    elif event.type == "agent_result":
        print(f"[{event.sender}] 완료: {event.content[:100]}...")
    elif event.type == "team_complete":
        print(f"최종 출력: {event.content}")
        print(f"비용: ${event.metadata['total_cost']:.4f}")
```

**이벤트 타입:**
- `team_start`: 팀 실행 시작
- `agent_message`: 에이전트 간 통신
- `agent_result`: 개별 에이전트 완료
- `team_complete`: 최종 결과 사용 가능

## 비용 추적 및 예산

AgentTeam이 모든 에이전트 호출에 걸쳐 비용을 집계합니다:

```python
result = await team.run("AI 안전성 리서치해줘")

print(f"총 비용: ${result.total_cost:.4f}")
print(f"총 토큰: {result.total_tokens:,}")
print(f"에이전트별 비용:")
for name, output in result.agent_outputs.items():
    print(f"  {name}: ${output.cost:.4f} ({output.tokens:,} 토큰)")
```

## MessageBus 상세

`MessageBus`는 구조화된 에이전트 간 통신을 제공합니다.

### 등록

```python
from agentchord.orchestration.message_bus import MessageBus

bus = MessageBus()
bus.register("researcher")
bus.register("writer")
bus.register("reviewer")

# 등록 확인
print(bus.registered_agents)  # ["researcher", "writer", "reviewer"]
```

### 메시지 전송

```python
from agentchord.orchestration.types import AgentMessage, MessageType

# 지향된 메시지
msg = AgentMessage(
    sender="researcher",
    recipient="writer",
    message_type=MessageType.RESULT,
    content="리서치 결과: ...",
    metadata={"citations": ["source1", "source2"]},
)
await bus.send(msg)

# 브로드캐스트 (발신자 제외 모든 에이전트)
broadcast_msg = AgentMessage(
    sender="coordinator",
    recipient=None,
    message_type=MessageType.BROADCAST,
    content="작업 우선순위가 HIGH로 변경되었습니다",
)
await bus.send(broadcast_msg)
```

### 메시지 수신

```python
# 메시지가 올 때까지 대기 (기본 30초 타임아웃)
msg = await bus.receive("writer")

# 커스텀 타임아웃
msg = await bus.receive("writer", timeout=10.0)

# 논블로킹 확인
if bus.pending_count("writer") > 0:
    msg = await bus.receive("writer", timeout=0.1)
```

### 메시지 히스토리

```python
# 모든 메시지
all_messages = bus.get_history()

# 특정 에이전트의 메시지
writer_messages = bus.get_agent_messages("writer")
for msg in writer_messages:
    print(f"{msg.timestamp}: {msg.sender} → {msg.recipient}: {msg.content}")

# 총 메시지 수
print(f"교환된 메시지 수: {bus.message_count}")
```

## SharedContext 상세

동시 에이전트 작업을 위한 스레드 안전한 공유 상태.

### 기본 작업

```python
ctx = SharedContext(initial={"project": "AgentChord"})

# 값 설정
await ctx.set("status", "in_progress", agent="coordinator")
await ctx.set("findings", research_data, agent="researcher")

# 값 가져오기 (변이 방지를 위한 깊은 복사 반환)
status = await ctx.get("status")
findings = await ctx.get("findings", default={})

# 존재 여부 확인
if await ctx.has("findings"):
    keys = await ctx.keys()  # ["project", "status", "findings"]
```

### 일괄 업데이트

```python
# 원자적 멀티키 업데이트
await ctx.update({
    "status": "review",
    "version": 2,
}, agent="coordinator")
```

### 삭제

```python
existed = await ctx.delete("temporary_data", agent="cleanup")
# 키가 존재했으면 True, 아니면 False 반환
```

### 스냅샷과 히스토리

```python
# 현재 상태의 불변 스냅샷
snapshot = ctx.snapshot()  # dict 복사본, 수정 가능

# 수정 히스토리
history = ctx.get_history()
for update in history:
    print(f"{update.agent}: {update.operation} {update.key} = {update.value}")

# 에이전트별 히스토리
researcher_updates = ctx.get_agent_updates("researcher")

# 메트릭
print(f"키 수: {ctx.size}")
print(f"업데이트 수: {ctx.update_count}")
```

### 동시성 안전

`SharedContext`는 `asyncio.Lock`으로 경쟁 조건을 방지합니다:

```python
# 안전한 동시 쓰기
await asyncio.gather(
    ctx.set("metric_a", 100, agent="agent1"),
    ctx.set("metric_b", 200, agent="agent2"),
    ctx.set("metric_c", 300, agent="agent3"),
)

# 공유 컨텍스트의 변이를 방지하기 위한 깊은 복사 반환
data = await ctx.get("large_dict")
data["new_key"] = "value"  # 공유 컨텍스트는 변경되지 않음
```

## 고급 패턴

### 커스텀 코디네이터 로직

특정 위임 기준을 가진 코디네이터 정의:

```python
coordinator = Agent(
    name="coordinator",
    role="""당신은 작업 조율자입니다. 사용자의 요청을 분석하고 서브작업을 위임하세요:
    - 데이터 분석 작업에는 delegate_to_analyst() 사용
    - 콘텐츠 생성에는 delegate_to_writer() 사용
    - 품질 확인에는 delegate_to_reviewer() 사용

    항상 작성 전에 분석을 먼저 위임하세요. 항상 최종 출력을 검토하세요.""",
    model="gpt-4o",
)
```

### 동적 팀 구성

작업 요구사항에 따라 에이전트 추가/제거:

```python
from agentchord.orchestration.types import TeamRole

base_members = [researcher, writer]

# 필요한 경우 전문가 추가
if task_requires_legal_review:
    base_members.append(
        Agent(name="legal", role="법률 검토자", model="gpt-4o")
    )

team = AgentTeam(name="team", members=base_members, strategy="coordinator")
```

### Worker Consult 기능

에이전트가 작업 중 동료에게 컨설트할 수 있도록 활성화:

```python
team = AgentTeam(
    name="team",
    members=[agent1, agent2, agent3],
    strategy="round_robin",
    enable_consult=True,    # 컨설트 활성화
    max_consult_depth=1,    # 컨설트 체인 최대 깊이
)
```

컨설트가 활성화되면 각 에이전트가 실행 중 동료에게 `consult_{peer_name}` 도구를 사용해 질문할 수 있습니다.

## 베스트 프랙티스

### 1. 올바른 전략 선택

```python
# 복잡한 계층적 작업 → Coordinator
team = AgentTeam(members=[...], strategy="coordinator")

# 반복적 개선 → Round Robin
team = AgentTeam(members=[drafter, editor, proofreader], strategy="round_robin")

# 관점 다양성 → Debate
team = AgentTeam(members=[optimist, skeptic], strategy="debate")

# 병렬 데이터 처리 → Map-Reduce
team = AgentTeam(members=workers, strategy="map_reduce")
```

### 2. 비용 제어를 위한 라운드 제한

```python
# 비용 폭주 방지
team = AgentTeam(
    name="team",
    members=[...],
    strategy="coordinator",
    max_rounds=5,  # 코디네이터 반복 제한
)
```

### 3. 라이프사이클 관리 사용

```python
# 항상 비동기 컨텍스트 관리자 사용
async with AgentTeam(...) as team:
    result = await team.run(task)
# 자동 정리: 메시지 버스 초기화, 리소스 해제
```

### 4. 메시지 패턴 모니터링

```python
result = await team.run(task)

# 통신 패턴 디버깅
print(f"교환된 메시지: {len(result.messages)}")
for msg in result.messages:
    print(f"{msg.sender} → {msg.recipient}: {msg.message_type.value}")
```

### 5. 모델 비용 균형

```python
# 비싼 코디네이터, 저렴한 워커
coordinator = Agent(name="coord", model="gpt-4o")  # 스마트 라우팅
workers = [
    Agent(name=f"w{i}", model="gpt-4o-mini")  # 빠른 실행
    for i in range(3)
]

team = AgentTeam(
    members=workers,
    coordinator=coordinator,
    strategy="coordinator",
)
```

### 6. 출력 검증 에이전트 추가

```python
# reviewer 에이전트로 출력 품질 확인
reviewer = Agent(
    name="reviewer",
    role="출력이 품질 기준을 충족하는지 검증",
    model="gpt-4o-mini",
)

team = AgentTeam(
    members=[researcher, writer, reviewer],
    strategy="round_robin",  # reviewer가 마지막에 실행됨
)
```

## 트러블슈팅

### 높은 비용

**증상**: `total_cost`가 예상보다 높음

**해결책**:
- `max_rounds` 줄이기
- 더 저렴한 모델 사용 (gpt-4o-mini)
- map-reduce에서 워커 에이전트 수 제한

### 잘못된 조율

**증상**: 코디네이터가 올바르게 위임하지 않음

**해결책**:
- 코디네이터에 더 강력한 모델 사용 (gpt-4o)
- 명시적인 위임 규칙으로 코디네이터 역할 설명 개선
- 위임 도구가 코디네이터에 전달되는지 확인
- 각 전문가의 역량을 명확히 설명하는 도구 설명 확인

### 메시지 타임아웃

**증상**: `bus.receive()`가 None 반환

**해결책**:
- 타임아웃 증가: `await bus.receive("agent", timeout=60.0)`
- 에이전트 등록 확인: `bus.registered_agents`
- 메시지가 올바른 수신자에게 전송됐는지 확인
- `bus.get_history()`로 디버깅

## 참고

- [Agent API](../api/core.md) - 핵심 Agent API
- [도구 가이드](tools.md) - 도구 호출과 위임 도구
- [예제](../examples.md) - 오케스트레이션 전체 예제
