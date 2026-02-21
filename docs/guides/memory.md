# 메모리 가이드

AgentChord는 용도가 다른 세 가지 메모리 시스템을 제공합니다: 대화 히스토리를 위한 ConversationMemory, 지식 검색을 위한 SemanticMemory, 임시 상태를 위한 WorkingMemory. 그리고 영속성을 위한 JSONFileStore와 SQLiteStore를 제공합니다.

## 빠른 시작

최소한의 설정으로 대화 히스토리를 저장합니다:

```python
from agentchord import Agent
from agentchord.memory import ConversationMemory

memory = ConversationMemory(max_entries=100)

agent = Agent(
    name="assistant",
    role="도움이 되는 챗봇",
    model="gpt-4o-mini",
    memory=memory
)

# 각 대화 턴이 자동으로 저장됨
result = agent.run_sync("프랑스의 수도는?")
print(result.output)  # "프랑스의 수도는 파리입니다."

# 이후 호출에서 이전 컨텍스트 참조 가능
result = agent.run_sync("거기 유명한 명소 알려줘")
# 에이전트가 이전 대화를 기억하며 "거기"가 파리를 가리킨다는 걸 이해
```

## MemoryEntry

모든 메모리 시스템은 `MemoryEntry` 객체를 사용합니다:

```python
from agentchord.memory import MemoryEntry
from datetime import datetime

entry = MemoryEntry(
    content="Python은 프로그래밍 언어입니다",
    role="system",  # "user", "assistant", "system"
    metadata={"source": "documentation", "confidence": 0.95}
)

print(entry.id)         # 자동 생성된 UUID
print(entry.timestamp)  # 자동 생성된 현재 시간
print(entry.content)
print(entry.metadata)
```

### 엔트리 역할

- `user` - 사용자의 메시지
- `assistant` - 에이전트의 응답
- `system` - 시스템 지시 또는 지식

## ConversationMemory

슬라이딩 윈도우로 최근 대화 히스토리를 저장합니다.

### 기본 사용법

```python
from agentchord.memory import ConversationMemory, MemoryEntry

memory = ConversationMemory(max_entries=100)

# 엔트리 추가
memory.add(MemoryEntry(content="안녕하세요", role="user"))
memory.add(MemoryEntry(content="안녕하세요!", role="assistant"))
memory.add(MemoryEntry(content="잘 지내세요?", role="user"))
memory.add(MemoryEntry(content="네, 잘 지냅니다!", role="assistant"))

print(len(memory))  # 4
```

### 최근 메시지 가져오기

```python
# 가장 최근 2개 메시지 가져오기
recent = memory.get_recent(limit=2)
for entry in recent:
    print(f"{entry.role}: {entry.content}")
# 출력:
# user: 잘 지내세요?
# assistant: 네, 잘 지냅니다!
```

### 히스토리 검색

대화에서 단순 부분 문자열 검색:

```python
# "Python"이 포함된 메시지 검색
results = memory.search("Python", limit=5)
for entry in results:
    print(f"{entry.role}: {entry.content}")
```

가장 최근 메시지부터 역순으로 검색합니다.

### LLM 포맷으로 변환

LLM API에 필요한 포맷으로 메시지를 가져옵니다:

```python
messages = memory.to_messages()
# 반환값: [
#   {"role": "user", "content": "안녕하세요"},
#   {"role": "assistant", "content": "안녕하세요!"},
#   ...
# ]
```

### 속성

```python
memory = ConversationMemory(max_entries=100)

print(memory.max_entries)  # 오래된 것이 제거되기 전 최대 엔트리 수
print(len(memory))         # 현재 엔트리 수

# 시간순으로 모든 엔트리 순회
for entry in memory:
    print(f"{entry.timestamp}: {entry.role} - {entry.content}")
```

### 메모리 초기화

```python
memory.clear()
print(len(memory))  # 0
```

## SemanticMemory

임베딩을 사용해 의미적 유사성을 기반으로 지식을 검색합니다.

### 임베딩 함수로 설정

```python
from agentchord.memory import SemanticMemory, MemoryEntry

# 임베딩 함수 제공 필요
# 이 예제는 데모용 간단한 임베딩
def simple_embed(text: str) -> list[float]:
    vec = [0.0] * 100
    for char in text[:100]:
        vec[ord(char) % 100] += 1.0
    magnitude = sum(x*x for x in vec) ** 0.5
    if magnitude > 0:
        vec = [x / magnitude for x in vec]
    return vec

memory = SemanticMemory(
    embedding_func=simple_embed,
    similarity_threshold=0.3,
    max_entries=1000
)
```

### 실제 임베딩 사용

프로덕션에서는 실제 임베딩 서비스를 사용합니다:

```python
from agentchord.memory import SemanticMemory
import httpx
import os

async def openai_embed(text: str) -> list[float]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/embeddings",
            json={"input": text, "model": "text-embedding-3-small"},
            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"}
        )
        data = response.json()
        return data["data"][0]["embedding"]

memory = SemanticMemory(
    embedding_func=openai_embed,
    similarity_threshold=0.5
)
```

### 지식 추가

```python
facts = [
    "Python은 고수준 프로그래밍 언어입니다",
    "머신러닝은 신경망을 사용합니다",
    "데이터베이스는 구조화된 데이터를 저장합니다",
    "API는 소프트웨어 간 통신을 가능하게 합니다",
]

for fact in facts:
    memory.add(MemoryEntry(content=fact))

print(len(memory))  # 4
```

### 의미 검색

키워드가 정확히 일치하지 않아도 의미로 검색합니다:

```python
results = memory.search("코딩 언어", limit=2)
# 정확한 키워드가 없어도 Python 관련 엔트리가 반환될 수 있음

for entry in results:
    print(f"Match: {entry.content} (score: {entry.metadata.get('similarity')})")
```

### 속성

```python
print(memory.similarity_threshold)  # 결과 포함 최소 점수
print(len(memory))                   # 저장된 엔트리 수
```

## WorkingMemory

TTL(Time-To-Live)이 있는 세션 상태용 임시 키-값 저장소입니다.

### 기본 사용법

```python
from agentchord.memory import WorkingMemory

memory = WorkingMemory(
    default_ttl=300,  # 기본 만료 시간: 5분
    max_items=100
)

# 값 저장
memory.set("user_id", "alice_123")
memory.set("session_step", 1)
memory.set("context", {"task": "analysis", "data": [1, 2, 3]})

# 값 가져오기
user_id = memory.get_value("user_id")  # "alice_123"
step = memory.get_value("session_step")  # 1
context = memory.get_value("context")  # {"task": "analysis", "data": [1, 2, 3]}

# 존재하지 않는 키는 None 반환
missing = memory.get_value("nonexistent")  # None
```

### 커스텀 TTL

값의 만료 시간을 제어합니다:

```python
# 30초 후 만료
memory.set("otp_code", "123456", ttl=30)

# 1시간 후 만료
memory.set("user_token", "xyz", ttl=3600)

# 만료 없음 (주의해서 사용)
memory.set("permanent", "value", ttl=None)
```

### 우선순위

항목에 우선순위를 부여합니다:

```python
# 높은 우선순위 항목이 더 오래 유지됨
memory.set("critical_flag", True, priority=1)
memory.set("debug_info", "...", priority=0)

# max_items에 도달하면 낮은 우선순위 항목부터 제거됨
```

### 값 증가

카운터에 편리합니다:

```python
memory.set("attempts", 0)
memory.increment("attempts")
memory.increment("attempts", 2)

value = memory.get_value("attempts")  # 3
```

### 순회

```python
for key, value in memory.items():
    print(f"{key}: {value}")
```

### 속성

```python
print(memory.default_ttl)  # 기본 만료 시간 (초)
print(len(memory))         # 현재 항목 수
print(memory.max_items)    # 제거 전 최대 항목 수
```

## 에이전트에서 메모리 사용

### ConversationMemory와 함께 사용

에이전트는 연결된 메모리에 자동으로 메시지를 추가합니다:

```python
from agentchord import Agent
from agentchord.memory import ConversationMemory

memory = ConversationMemory(max_entries=50)

agent = Agent(
    name="assistant",
    role="도움이 되는 챗봇",
    model="gpt-4o-mini",
    memory=memory
)

# 각 run이 사용자 입력과 에이전트 응답을 메모리에 추가
agent.run_sync("AI란 무엇인가요?")
agent.run_sync("더 자세히 알려줘")

# 메모리에 대화 히스토리가 쌓임
print(len(memory))  # 4 엔트리 (사용자 2, 어시스턴트 2)

recent = memory.get_recent(limit=10)
```

### 멀티턴 대화

```python
from agentchord import Agent
from agentchord.memory import ConversationMemory

memory = ConversationMemory(max_entries=100)

agent = Agent(
    name="researcher",
    role="리서치 어시스턴트",
    model="gpt-4o-mini",
    memory=memory
)

# 1번째 턴
result1 = agent.run_sync("Python 프로그래밍 역사를 요약해줘")
print(f"Turn 1: {result1.output[:100]}...")

# 2번째 턴 - 1번째 턴 컨텍스트가 있음
result2 = agent.run_sync("최근 5년간 어떻게 발전했나요?")
print(f"Turn 2: {result2.output[:100]}...")

# 3번째 턴 - 이전 두 턴을 모두 참조 가능
result3 = agent.run_sync("다음은 어디로 갈 것 같나요?")
print(f"Turn 3: {result3.output[:100]}...")

# 전체 메모리 검사
messages = memory.to_messages()
print(f"총 대화 턴: {len(messages) // 2}")
```

## 메모리 영속성

### JSONFileStore

JSON 파일 기반 영속 스토리지:

```python
from agentchord.memory.stores.json_file import JSONFileStore
from agentchord.memory import ConversationMemory, MemoryEntry

# JSONFileStore로 영속성 제공
store = JSONFileStore("./memory_data")

# 엔트리 저장
entry = MemoryEntry(content="중요한 정보", role="system")
await store.save("my_agent", entry)

# 엔트리 불러오기
entries = await store.load("my_agent")
for e in entries:
    print(f"{e.role}: {e.content}")

# 엔트리 삭제
deleted = await store.delete("my_agent", entry.id)  # True if existed

# 전체 삭제
await store.clear("my_agent")

# 카운트 확인
count = await store.count("my_agent")
```

JSONFileStore 디렉토리 구조:
```
memory_data/
    my_agent/
        entries.json
    another_agent/
        entries.json
```

### SQLiteStore

SQLite 기반 비동기 스토리지 (aiosqlite 필요):

```python
from agentchord.memory.stores.sqlite import SQLiteStore
from agentchord.memory import MemoryEntry

# 파일 기반 DB
store = SQLiteStore("memory.db")

# 인메모리 DB (테스트용)
store = SQLiteStore(":memory:")

# 엔트리 저장
entry = MemoryEntry(content="분석 결과", role="assistant")
await store.save("session_1", entry)

# 불러오기
entries = await store.load("session_1")

# 삭제
await store.delete("session_1", entry.id)

# 전체 초기화
await store.clear("session_1")
```

SQLiteStore 스키마:
```sql
CREATE TABLE entries (
    id TEXT PRIMARY KEY,
    namespace TEXT NOT NULL,
    content TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    timestamp TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}'
)
```

aiosqlite 설치:
```bash
pip install aiosqlite
```

### JSON으로 수동 저장

```python
import json
from agentchord.memory import ConversationMemory

memory = ConversationMemory()
# ... 엔트리 추가 ...

# 직렬화 가능한 포맷으로 변환
messages = memory.to_messages()
with open("conversation.json", "w") as f:
    json.dump(messages, f)
```

### JSON에서 복원

```python
from agentchord.memory import ConversationMemory, MemoryEntry
import json

memory = ConversationMemory()

with open("conversation.json", "r") as f:
    messages = json.load(f)

# 저장된 메시지 복원
for msg in messages:
    memory.add(MemoryEntry(
        content=msg["content"],
        role=msg["role"]
    ))
```

## 베스트 프랙티스

### 1. 올바른 메모리 타입 선택

- **ConversationMemory**: 챗 애플리케이션, 멀티턴 상호작용
- **SemanticMemory**: 지식 베이스, 사실 검색, RAG
- **WorkingMemory**: 세션 상태, 카운터, 임시 컨텍스트

### 2. 적절한 한도 설정

```python
# 장기 실행 챗봇
memory = ConversationMemory(max_entries=200)

# 빠른 상호작용
memory = ConversationMemory(max_entries=20)
```

### 3. 만료된 WorkingMemory 정리

```python
memory = WorkingMemory(default_ttl=600, max_items=100)

# 만료된 항목은 접근 시 자동 제거됨
# 주기적으로 상태 확인
if len(memory) > memory.max_items * 0.8:
    print("작업 메모리가 거의 가득 찼습니다")
```

### 4. 메모리 타입 조합

```python
from agentchord import Agent
from agentchord.memory import ConversationMemory, WorkingMemory

conv_memory = ConversationMemory(max_entries=50)
work_memory = WorkingMemory(default_ttl=600)

# 에이전트에는 ConversationMemory만 연결
agent = Agent(
    name="assistant",
    role="어시스턴트",
    model="gpt-4o-mini",
    memory=conv_memory
)

# WorkingMemory는 별도로 상태 관리에 사용
work_memory.set("user_preference", "verbose")
work_memory.set("interaction_count", 0)
```

### 5. 영속성 필요 시 Store 사용

```python
from agentchord.memory.stores.json_file import JSONFileStore
from agentchord.memory import MemoryEntry

store = JSONFileStore("./sessions")

# 세션 저장
entry = MemoryEntry(content=important_info, role="system")
await store.save(f"session_{user_id}", entry)

# 다음 세션에서 복원
entries = await store.load(f"session_{user_id}")
```

## 완전한 예제

```python
from agentchord import Agent
from agentchord.memory import ConversationMemory, WorkingMemory

async def main():
    # 대화 메모리 설정
    conv_memory = ConversationMemory(max_entries=100)

    # 세션 상태용 작업 메모리 설정
    work_memory = WorkingMemory(default_ttl=3600)

    # 대화 메모리를 가진 에이전트 생성
    agent = Agent(
        name="support_bot",
        role="고객 지원 담당자",
        model="gpt-4o-mini",
        memory=conv_memory
    )

    # 상호작용 횟수 추적
    work_memory.set("interaction_count", 0)

    # 멀티턴 대화
    queries = [
        "계정 문제가 있어요",
        "비밀번호를 잊었어요",
        "초기화 해주실 수 있나요?"
    ]

    for query in queries:
        count = work_memory.get_value("interaction_count") or 0
        work_memory.set("interaction_count", count + 1)

        # 에이전트 실행 - 대화 메모리 자동 사용
        result = agent.run_sync(query)
        print(f"Turn {count + 1}: {result.output}\n")

    # 저장된 대화 검사
    messages = conv_memory.to_messages()
    print(f"대화 히스토리: {len(messages)} 메시지")
    for msg in messages[:3]:
        print(f"  {msg['role']}: {msg['content'][:50]}...")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## 참고

- [도구 가이드](tools.md) - 도구 호출과 함께 메모리 사용
- [Agent API](../api/core.md) - Agent API 상세 정보
- [예제](../examples.md) - 메모리 전체 예제
