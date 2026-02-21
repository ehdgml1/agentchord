# 도구 API 레퍼런스

에이전트가 함수를 실행할 수 있게 해주는 도구 시스템에 대한 완전한 API 레퍼런스입니다.

---

## @tool 데코레이터

함수를 에이전트가 사용할 수 있는 `Tool` 객체로 변환하는 데코레이터입니다. 함수 시그니처에서 파라미터 타입과 이름을 자동으로 추출합니다.

```python
from agentchord.tools import tool

# 기본 사용
@tool(description="두 수를 더합니다")
def add(a: int, b: int) -> int:
    return a + b

# 비동기 함수도 지원
@tool(name="web_search", description="웹에서 정보를 검색합니다")
async def search(query: str, max_results: int = 5) -> str:
    # 구현
    return f"{query} 검색 결과..."

# 에이전트에 등록
from agentchord import Agent
agent = Agent(name="helper", role="...", tools=[add, search])
```

**파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `name` | `str \| None` | `None` | 도구 이름. None이면 함수 이름 사용 |
| `description` | `str \| None` | `None` | 도구 설명. None이면 함수 docstring 사용 |

**반환값:** `Tool` 객체

**파라미터 타입 매핑:**

데코레이터는 Python 타입 힌트를 JSON Schema 타입으로 자동 변환합니다.

| Python 타입 | JSON Schema 타입 |
|------------|----------------|
| `str` | `"string"` |
| `int` | `"integer"` |
| `float` | `"number"` |
| `bool` | `"boolean"` |
| `list` | `"array"` |
| `dict` | `"object"` |
| `Optional[X]` | X의 타입 (required=False) |

> **주의:** 기본값이 있는 파라미터는 `required=False`로 설정됩니다.

---

## Tool

에이전트가 호출할 수 있는 도구를 나타내는 Pydantic 모델입니다.

```python
from agentchord.tools.base import Tool, ToolParameter

# 직접 생성
tool = Tool(
    name="get_weather",
    description="특정 도시의 날씨를 조회합니다",
    parameters=[
        ToolParameter(name="city", type="string", description="도시 이름", required=True),
        ToolParameter(name="unit", type="string", description="온도 단위", required=False, default="celsius"),
    ],
    func=get_weather_func,
)

# 실행
result = await tool.execute(city="서울", unit="celsius")
print(result.result)   # 성공 시 결과
print(result.success)  # True/False
print(result.error)    # 실패 시 에러 메시지
```

**필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `name` | `str` | 도구 이름 |
| `description` | `str` | 도구 설명 |
| `parameters` | `list[ToolParameter]` | 파라미터 정의 목록 |
| `func` | `Callable` | 실행할 함수 (동기/비동기 모두 가능) |

**프로퍼티:**

| 프로퍼티 | 타입 | 설명 |
|----------|------|------|
| `is_async` | `bool` | 함수가 비동기(coroutine)인지 여부 |

**메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `execute` | `async execute(**kwargs) -> ToolResult` | `ToolResult` | 도구 실행. 예외를 캐치하여 `ToolResult.error`에 저장 |
| `to_openai_schema` | `to_openai_schema() -> dict[str, Any]` | `dict` | OpenAI 함수 호출 스키마로 변환 |
| `to_anthropic_schema` | `to_anthropic_schema() -> dict[str, Any]` | `dict` | Anthropic 도구 스키마로 변환 |

---

## ToolParameter

도구의 파라미터 정의입니다.

```python
from agentchord.tools.base import ToolParameter

param = ToolParameter(
    name="query",
    type="string",
    description="검색할 쿼리",
    required=True,
    default=None,
    enum=None,
)
```

**필드:**

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `name` | `str` | 필수 | 파라미터 이름 |
| `type` | `str` | 필수 | JSON Schema 타입 ("string", "integer", "number", "boolean", "array", "object") |
| `description` | `str` | `""` | 파라미터 설명 |
| `required` | `bool` | `True` | 필수 파라미터 여부 |
| `default` | `Any` | `None` | 기본값 |
| `enum` | `list[Any] \| None` | `None` | 허용 값 목록 (열거형) |

---

## ToolResult

도구 실행 결과입니다.

```python
from agentchord.tools.base import ToolResult

# 성공 결과 생성
result = ToolResult.success_result("search", data={"results": [...]})
print(result.success)   # True
print(result.result)    # {"results": [...]}

# 실패 결과 생성
result = ToolResult.error_result("search", "연결 실패")
print(result.success)   # False
print(result.error)     # "연결 실패"
```

**필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `tool_call_id` | `str` | 이 실행의 고유 ID (자동 생성 UUID) |
| `tool_name` | `str` | 실행된 도구 이름 |
| `success` | `bool` | 실행 성공 여부 |
| `result` | `Any` | 성공 시 반환 값 |
| `error` | `str \| None` | 실패 시 에러 메시지 |

**클래스 메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `success_result` | `success_result(tool_name: str, result: Any, tool_call_id: str \| None = None) -> ToolResult` | `ToolResult` | 성공 결과 생성 |
| `error_result` | `error_result(tool_name: str, error: str, tool_call_id: str \| None = None) -> ToolResult` | `ToolResult` | 실패 결과 생성 |

---

## ToolExecutor

도구를 관리하고 실행하는 매니저입니다.

```python
from agentchord.tools.executor import ToolExecutor
from agentchord.tools import tool

@tool(description="덧셈")
def add(a: int, b: int) -> int:
    return a + b

@tool(description="곱셈")
def multiply(a: int, b: int) -> int:
    return a * b

# 초기 도구 목록으로 생성
executor = ToolExecutor([add, multiply])

# 도구 추가/제거
executor.register(another_tool)
executor.unregister("add")

# 실행
result = await executor.execute("multiply", tool_call_id="call_1", a=3, b=4)
print(result.result)  # 12

# 도구 목록 조회
print(executor.tool_names)   # ["multiply"]
print(len(executor))          # 1
print("multiply" in executor) # True
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `tools` | `list[Tool] \| None` | `None` | 초기 도구 목록 |

**메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `register` | `register(tool: Tool) -> None` | `None` | 도구 등록 |
| `unregister` | `unregister(name: str) -> bool` | `bool` | 이름으로 도구 등록 해제. 성공 시 True 반환 |
| `get` | `get(name: str) -> Tool \| None` | `Tool \| None` | 이름으로 도구 조회 |
| `list_tools` | `list_tools() -> list[Tool]` | `list[Tool]` | 등록된 모든 도구 목록 반환 |
| `execute` | `async execute(name: str, tool_call_id: str \| None = None, **arguments) -> ToolResult` | `ToolResult` | 이름으로 도구 실행 |
| `to_openai_tools` | `to_openai_tools() -> list[dict]` | `list[dict]` | 모든 도구를 OpenAI 형식으로 변환 |
| `to_anthropic_tools` | `to_anthropic_tools() -> list[dict]` | `list[dict]` | 모든 도구를 Anthropic 형식으로 변환 |

**프로퍼티:**

| 프로퍼티 | 타입 | 설명 |
|----------|------|------|
| `tool_names` | `list[str]` | 등록된 모든 도구 이름 목록 |

---

## 종합 사용 예제

```python
from agentchord import Agent
from agentchord.tools import tool
import httpx

# 도구 정의
@tool(description="지정한 도시의 현재 날씨를 조회합니다")
async def get_weather(city: str, unit: str = "celsius") -> str:
    """날씨 조회 도구"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://wttr.in/{city}?format=3",
            params={"city": city}
        )
        return response.text

@tool(description="두 숫자를 더합니다")
def add_numbers(a: float, b: float) -> float:
    return a + b

# 에이전트에 도구 등록
agent = Agent(
    name="tool-agent",
    role="다양한 도구를 활용하는 어시스턴트",
    model="gpt-4o-mini",
    tools=[get_weather, add_numbers],
)

# 도구가 자동으로 호출됨
result = await agent.run("서울의 날씨를 알려주고, 3 더하기 7도 계산해줘")
print(result.output)
```
