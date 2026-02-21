# 메모리 API 레퍼런스

에이전트가 컨텍스트를 보관하고 검색할 수 있게 해주는 메모리 시스템에 대한 완전한 API 레퍼런스입니다.

---

## MemoryEntry

메모리에 저장되는 단일 항목입니다.

```python
from agentchord.memory.base import MemoryEntry
from datetime import datetime

entry = MemoryEntry(
    content="파이썬은 범용 프로그래밍 언어입니다.",
    role="assistant",
    metadata={"source": "wiki", "confidence": 0.95},
)

print(entry.id)        # 자동 생성된 UUID
print(entry.timestamp) # 생성 시각
```

**필드:**

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `id` | `str` | 자동 UUID | 항목 고유 식별자 |
| `content` | `str` | 필수 | 메모리 내용 |
| `role` | `str` | `"user"` | 발신자 역할 (`"user"`, `"assistant"`, `"system"`) |
| `timestamp` | `datetime` | 현재 시각 | 생성 시각 |
| `metadata` | `dict[str, Any]` | `{}` | 추가 메타데이터 |

---

## BaseMemory

모든 메모리 구현이 따라야 하는 추상 기본 클래스입니다.

```python
from agentchord.memory.base import BaseMemory, MemoryEntry

class MyMemory(BaseMemory):
    def add(self, entry: MemoryEntry) -> None:
        ...
    def get(self, entry_id: str) -> MemoryEntry | None:
        ...
    def get_recent(self, limit: int = 10) -> list[MemoryEntry]:
        ...
    def search(self, query: str, limit: int = 5) -> list[MemoryEntry]:
        ...
    def clear(self) -> None:
        ...
    def __len__(self) -> int:
        ...
```

**추상 메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `add` | `add(entry: MemoryEntry) -> None` | `None` | 항목 추가 |
| `get` | `get(entry_id: str) -> MemoryEntry \| None` | `MemoryEntry \| None` | ID로 항목 조회 |
| `get_recent` | `get_recent(limit: int = 10) -> list[MemoryEntry]` | `list[MemoryEntry]` | 최근 항목 목록 반환 |
| `search` | `search(query: str, limit: int = 5) -> list[MemoryEntry]` | `list[MemoryEntry]` | 쿼리로 항목 검색 |
| `clear` | `clear() -> None` | `None` | 모든 항목 삭제 |
| `__len__` | `__len__() -> int` | `int` | 저장된 항목 수 반환 |

---

## ConversationMemory

슬라이딩 윈도우 방식의 대화 기록 메모리입니다. 가장 오래된 항목부터 자동으로 제거합니다.

```python
from agentchord.memory.conversation import ConversationMemory
from agentchord.memory.base import MemoryEntry
from agentchord import Agent

# 기본 사용
memory = ConversationMemory(max_entries=100)

memory.add(MemoryEntry(content="파이썬이 뭔가요?", role="user"))
memory.add(MemoryEntry(content="파이썬은 범용 언어입니다.", role="assistant"))

print(len(memory))          # 2
recent = memory.get_recent(5)  # 최근 5개
results = memory.search("파이썬")  # 키워드 검색

# 영속 저장소와 함께 사용
from agentchord.memory.stores import SQLiteStore
store = SQLiteStore("memory.db")
memory = ConversationMemory(max_entries=1000, store=store, namespace="user_123")

await memory.load_from_store()  # 저장소에서 불러오기
# ... 에이전트 사용 ...
await memory.save_to_store()    # 저장소에 저장

# 에이전트에 연결
agent = Agent(name="bot", role="...", memory=memory)
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `max_entries` | `int` | `1000` | 최대 저장 항목 수. 초과 시 가장 오래된 항목 삭제 |
| `store` | `MemoryStore \| None` | `None` | 영속 저장소 백엔드 |
| `namespace` | `str` | `"default"` | 영속 저장소에서 사용할 네임스페이스 (에이전트 ID, 세션 ID 등) |

**메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `add` | `add(entry: MemoryEntry) -> None` | `None` | 대화 기록에 항목 추가. 저장소가 있으면 자동 저장 |
| `get` | `get(entry_id: str) -> MemoryEntry \| None` | `MemoryEntry \| None` | ID로 항목 조회 |
| `get_recent` | `get_recent(limit: int = 10) -> list[MemoryEntry]` | `list[MemoryEntry]` | 최근 항목을 시간 순서로 반환 |
| `search` | `search(query: str, limit: int = 5) -> list[MemoryEntry]` | `list[MemoryEntry]` | 내용에서 부분 문자열 검색 (대소문자 무시) |
| `clear` | `clear() -> None` | `None` | 모든 대화 기록 삭제 |
| `to_messages` | `to_messages() -> list[dict[str, str]]` | `list[dict]` | LLM 메시지 형식으로 변환 (`{"role": ..., "content": ...}` 목록) |
| `load_from_store` | `async load_from_store() -> int` | `int` | 영속 저장소에서 항목 로드. 로드된 항목 수 반환 |
| `save_to_store` | `async save_to_store() -> int` | `int` | 현재 항목을 영속 저장소에 저장. 저장된 항목 수 반환 |

**프로퍼티:**

| 프로퍼티 | 타입 | 설명 |
|----------|------|------|
| `max_entries` | `int` | 최대 저장 항목 수 |

---

## SemanticMemory

벡터 유사도 검색을 사용하는 시맨틱 메모리입니다. 임베딩 함수를 통해 의미적으로 유사한 항목을 검색합니다.

```python
from agentchord.memory.semantic import SemanticMemory
from agentchord.memory.base import MemoryEntry
import openai

# 임베딩 함수 정의
client = openai.AsyncOpenAI()

def embed(text: str) -> list[float]:
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

# 메모리 생성
memory = SemanticMemory(
    embedding_func=embed,
    similarity_threshold=0.7,
)

memory.add(MemoryEntry(content="파리는 프랑스의 수도입니다."))
memory.add(MemoryEntry(content="도쿄는 일본의 수도입니다."))

# 의미 검색
results = memory.search("유럽의 수도 도시", limit=3)
for entry in results:
    print(entry.content)
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `embedding_func` | `Callable[[str], list[float]]` | 필수 | 텍스트를 임베딩 벡터로 변환하는 함수 |
| `similarity_threshold` | `float` | `0.5` | 검색 결과 최소 유사도 (0~1). 낮을수록 더 많은 결과 반환 |

**메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `add` | `add(entry: MemoryEntry) -> None` | `None` | 임베딩을 계산하여 항목 추가 |
| `add_with_embedding` | `add_with_embedding(entry: MemoryEntry, embedding: list[float]) -> None` | `None` | 미리 계산된 임베딩으로 항목 추가 (재계산 방지) |
| `get` | `get(entry_id: str) -> MemoryEntry \| None` | `MemoryEntry \| None` | ID로 항목 조회 |
| `get_embedding` | `get_embedding(entry_id: str) -> list[float] \| None` | `list[float] \| None` | 항목의 임베딩 벡터 반환 |
| `get_recent` | `get_recent(limit: int = 10) -> list[MemoryEntry]` | `list[MemoryEntry]` | 최근 항목을 타임스탬프 순서로 반환 |
| `search` | `search(query: str, limit: int = 5) -> list[MemoryEntry]` | `list[MemoryEntry]` | 의미적으로 유사한 항목 검색 (유사도 높은 순) |
| `search_by_embedding` | `search_by_embedding(query_embedding: list[float], limit: int = 5) -> list[MemoryEntry]` | `list[MemoryEntry]` | 미리 계산된 임베딩으로 검색 |
| `remove` | `remove(entry_id: str) -> bool` | `bool` | ID로 항목 삭제. 성공 시 True |
| `clear` | `clear() -> None` | `None` | 모든 항목과 임베딩 삭제 |

**프로퍼티:**

| 프로퍼티 | 타입 | 설명 |
|----------|------|------|
| `similarity_threshold` | `float` | 검색 결과 최소 유사도 임계값 |

---

## WorkingMemory

TTL(만료 시간)이 있는 임시 키-값 저장소입니다. 다단계 작업에서 중간 결과나 컨텍스트를 저장하는 데 유용합니다.

```python
from agentchord.memory.working import WorkingMemory

memory = WorkingMemory(default_ttl=300, max_items=50)  # 5분 TTL, 최대 50개

# 값 저장
memory.set("current_step", 1)
memory.set("result", {"data": [1, 2, 3]})
memory.set("temp_value", "임시 데이터", ttl=60)  # 개별 TTL 60초

# 값 조회
step = memory.get_value("current_step")       # 1
missing = memory.get_value("missing", "기본값") # "기본값"

# 키 존재 확인
if memory.has("current_step"):
    print("존재함")

# 숫자 증가
memory.set("counter", 0)
new_val = memory.increment("counter")      # 1
new_val = memory.increment("counter", 5)   # 6

# 목록 조회
print(memory.keys())    # 만료되지 않은 키 목록
print(memory.items())   # [(key, value), ...] 목록

# 삭제
memory.remove("temp_value")
memory.clear()
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `default_ttl` | `float \| None` | `None` | 기본 만료 시간 (초). None이면 만료 없음 |
| `max_items` | `int` | `100` | 최대 저장 항목 수. 초과 시 우선순위가 낮고 오래된 항목부터 제거 |

**메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `set` | `set(key: str, value: Any, ttl: float \| None = None, priority: int = 0) -> None` | `None` | 값 저장. `ttl` 미지정 시 `default_ttl` 사용 |
| `get_value` | `get_value(key: str, default: Any = None) -> Any` | `Any` | 값 조회. 없거나 만료된 경우 default 반환 |
| `has` | `has(key: str) -> bool` | `bool` | 키가 존재하고 만료되지 않았는지 확인 |
| `remove` | `remove(key: str) -> bool` | `bool` | 키 삭제. 성공 시 True 반환 |
| `increment` | `increment(key: str, amount: int = 1) -> int` | `int` | 숫자 값 증가. 비숫자 값이면 `TypeError` |
| `keys` | `keys() -> list[str]` | `list[str]` | 만료되지 않은 모든 키 목록 |
| `values` | `values() -> list[Any]` | `list[Any]` | 만료되지 않은 모든 값 목록 |
| `items` | `items() -> list[tuple[str, Any]]` | `list[tuple]` | 만료되지 않은 모든 (키, 값) 쌍 목록 |
| `clear` | `clear() -> None` | `None` | 모든 항목 삭제 |

---

## MemoryStore

메모리 영속 저장소의 추상 기본 클래스입니다.

```python
from agentchord.memory.stores.base import MemoryStore
from agentchord.memory.base import MemoryEntry

class MyStore(MemoryStore):
    async def save(self, namespace: str, entry: MemoryEntry) -> None: ...
    async def save_many(self, namespace: str, entries: list[MemoryEntry]) -> None: ...
    async def load(self, namespace: str) -> list[MemoryEntry]: ...
    async def delete(self, namespace: str, entry_id: str) -> bool: ...
    async def clear(self, namespace: str) -> None: ...
    async def count(self, namespace: str) -> int: ...
```

**추상 메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `save` | `async save(namespace: str, entry: MemoryEntry) -> None` | `None` | 단일 항목 저장 |
| `save_many` | `async save_many(namespace: str, entries: list[MemoryEntry]) -> None` | `None` | 여러 항목 원자적으로 저장 (기존 항목 교체) |
| `load` | `async load(namespace: str) -> list[MemoryEntry]` | `list[MemoryEntry]` | 네임스페이스의 모든 항목 로드 |
| `delete` | `async delete(namespace: str, entry_id: str) -> bool` | `bool` | 특정 항목 삭제. 성공 시 True |
| `clear` | `async clear(namespace: str) -> None` | `None` | 네임스페이스의 모든 항목 삭제 |
| `count` | `async count(namespace: str) -> int` | `int` | 네임스페이스의 항목 수 반환 |

---

## JSONFileStore

JSON 파일 기반 메모리 저장소입니다.

디렉토리 구조:
```
base_dir/
  namespace1/
    entries.json
  namespace2/
    entries.json
```

```python
from agentchord.memory.stores.json_file import JSONFileStore
from agentchord.memory.conversation import ConversationMemory

store = JSONFileStore("./memory_data")

# ConversationMemory와 함께 사용
memory = ConversationMemory(max_entries=500, store=store, namespace="agent_1")
await memory.load_from_store()

# 직접 사용
entries = await store.load("agent_1")
await store.save("agent_1", entry)
await store.clear("agent_1")
count = await store.count("agent_1")
```

**생성자 파라미터:**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `base_dir` | `str \| Path` | 네임스페이스 폴더를 저장할 기본 디렉토리 |

> **보안 주의:** 네임스페이스에 `..`이나 `/`가 포함된 경우 경로 탐색 공격을 방지하기 위해 `ValueError`가 발생합니다.

---

## SQLiteStore

SQLite 기반 비동기 메모리 저장소입니다. `aiosqlite` 패키지가 필요합니다.

```python
from agentchord.memory.stores.sqlite import SQLiteStore
from agentchord.memory.conversation import ConversationMemory

# 파일 기반 DB
store = SQLiteStore("memory.db")

# 인메모리 DB (테스트용)
store = SQLiteStore(":memory:")

# ConversationMemory와 함께 사용
memory = ConversationMemory(max_entries=1000, store=store, namespace="session_abc")
await memory.load_from_store()

# 컨텍스트 매니저 지원
async with SQLiteStore("memory.db") as store:
    entries = await store.load("agent_1")
    # ... 사용 ...
# close() 자동 호출

# 직접 사용
await store.save("session_1", entry)
await store.save_many("session_1", entries_list)
entries = await store.load("session_1")
deleted = await store.delete("session_1", entry_id)
await store.clear("session_1")
count = await store.count("session_1")
await store.close()
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `db_path` | `str \| Path` | `":memory:"` | SQLite DB 파일 경로. `":memory:"`이면 인메모리 DB |

**DB 스키마:**

```sql
CREATE TABLE memory_entries (
    id TEXT PRIMARY KEY,
    namespace TEXT NOT NULL,
    content TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    timestamp TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}',
    UNIQUE(namespace, id)
);
```

> **의존성:** `pip install aiosqlite`
>
> **인메모리 DB:** 동일한 SQLiteStore 인스턴스 내에서만 데이터가 유지됩니다. `close()` 호출 시 데이터가 사라집니다.
