# 도구 가이드

도구는 에이전트가 행동을 취하고 정보를 가져올 수 있게 합니다. AgentChord는 모든 LLM 프로바이더와 호환되는 도구 시스템을 제공합니다.

## 빠른 시작

`@tool` 데코레이터로 Python 함수를 도구로 변환합니다:

```python
from agentchord import tool, Agent

@tool(description="두 숫자를 더함")
def add(a: int, b: int) -> int:
    return a + b

agent = Agent(
    name="calculator",
    role="수학 도우미",
    model="gpt-4o-mini",
    tools=[add]
)

result = agent.run_sync("5 + 3은?")
print(result.output)  # "The answer is 8"
```

## @tool 데코레이터로 도구 만들기

`@tool` 데코레이터는 함수 시그니처를 추출해 LLM 호환 도구 정의로 변환합니다.

### 기본 도구

```python
@tool(description="텍스트를 대문자로 변환")
def uppercase(text: str) -> str:
    return text.upper()
```

데코레이터가 추출하는 항목:
- **name**: 함수 이름 (또는 `name=` 파라미터로 커스텀 지정)
- **description**: 필수; LLM에게 도구가 무엇을 하는지 알려줌
- **parameters**: 타입 힌트를 가진 함수 시그니처에서 추출
- **return type**: 함수의 반환 타입 어노테이션

### 커스텀 도구 이름

```python
@tool(name="uppercase_converter", description="텍스트를 대문자로 변환")
def uppercase(text: str) -> str:
    return text.upper()
```

### 비동기 도구

도구는 비동기 함수도 가능합니다:

```python
import httpx

@tool(description="URL에서 콘텐츠를 가져옴")
async def fetch_url(url: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text
```

AgentChord가 비동기 함수를 자동으로 감지하고 올바르게 처리합니다.

### 파라미터 타입

AgentChord가 지원하는 Python 타입:

```python
@tool(description="여러 데이터 포인트 처리")
def process(
    name: str,
    count: int,
    ratio: float,
    enabled: bool,
    tags: list = None,
    metadata: dict = None
) -> dict:
    return {
        "name": name,
        "count": count,
        "ratio": ratio,
        "enabled": enabled,
        "tags": tags or [],
        "metadata": metadata or {}
    }
```

지원 타입:
- `str` - 텍스트
- `int` - 정수
- `float` - 소수
- `bool` - 참/거짓
- `list` - 배열
- `dict` - 객체
- Optional 타입 (`Optional[T]` 또는 `T | None`)

### 선택적 파라미터

기본값이 있는 파라미터는 선택 사항입니다:

```python
@tool(description="필터로 검색")
def search(
    query: str,
    max_results: int = 10,
    sort_by: str = "relevance"
) -> list:
    return []
```

LLM은 `max_results`와 `sort_by`를 생략 가능한 파라미터로 인식합니다.

## Tool 클래스

`@tool`은 내부적으로 `Tool` 인스턴스를 반환합니다:

```python
from agentchord.tools.base import Tool, ToolParameter

# @tool 데코레이터와 동일
tool_instance = Tool(
    name="add",
    description="두 숫자를 더함",
    parameters=[
        ToolParameter(name="a", type="integer", required=True),
        ToolParameter(name="b", type="integer", required=True),
    ],
    func=lambda a, b: a + b
)
```

### Tool 속성

```python
@tool(description="숫자를 나눔")
def divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("0으로 나눌 수 없음")
    return a / b

print(divide.name)           # "divide"
print(divide.description)    # "숫자를 나눔"
print(divide.parameters)     # ToolParameter 객체 목록
print(divide.is_async)       # False (비동기면 True)
```

### 도구 직접 실행

에이전트 없이 도구를 직접 실행합니다:

```python
# 비동기 실행
result = await divide.execute(a=10, b=2)
print(result.success)    # True
print(result.result)     # 5.0
print(result.tool_name)  # "divide"

# 에러 처리
result = await divide.execute(a=10, b=0)
print(result.success)  # False
print(result.error)    # "0으로 나눌 수 없음"
```

## 도구 스키마

도구는 LLM 프로바이더 스키마로 자동 변환됩니다.

### OpenAI 스키마

```python
openai_schema = divide.to_openai_schema()
# {
#   "type": "function",
#   "function": {
#     "name": "divide",
#     "description": "숫자를 나눔",
#     "parameters": {
#       "type": "object",
#       "properties": {
#         "a": {"type": "number"},
#         "b": {"type": "number"}
#       },
#       "required": ["a", "b"]
#     }
#   }
# }
```

### Anthropic 스키마

```python
anthropic_schema = divide.to_anthropic_schema()
# {
#   "name": "divide",
#   "description": "숫자를 나눔",
#   "input_schema": {
#     "type": "object",
#     "properties": {
#       "a": {"type": "number"},
#       "b": {"type": "number"}
#     },
#     "required": ["a", "b"]
#   }
# }
```

## 에이전트에서 도구 사용

### 단일 도구

```python
@tool(description="현재 기온을 섭씨로 가져옴")
def get_temp() -> float:
    return 22.5

agent = Agent(
    name="weather",
    role="날씨 도우미",
    model="gpt-4o-mini",
    tools=[get_temp]
)

result = agent.run_sync("현재 기온은?")
```

### 여러 도구

```python
@tool(description="두 숫자를 더함")
def add(a: int, b: int) -> int:
    return a + b

@tool(description="두 숫자를 뺌")
def subtract(a: int, b: int) -> int:
    return a - b

@tool(description="두 숫자를 곱함")
def multiply(a: int, b: int) -> int:
    return a * b

agent = Agent(
    name="calculator",
    role="수학 도우미",
    model="gpt-4o-mini",
    tools=[add, subtract, multiply]
)

result = agent.run_sync("(10 + 5) * 2 계산해줘")
# LLM이 add(10, 5) -> 15, multiply(15, 2) -> 30 순서로 호출
```

## ToolExecutor

고급 사용 사례에서 도구를 직접 관리합니다:

```python
from agentchord.tools.executor import ToolExecutor

@tool(description="두 숫자를 더함")
def add(a: int, b: int) -> int:
    return a + b

@tool(description="두 숫자를 뺌")
def subtract(a: int, b: int) -> int:
    return a - b

executor = ToolExecutor([add, subtract])

# 사용 가능한 도구 목록
print(executor.tool_names)  # ["add", "subtract"]

# 이름으로 도구 실행
result = await executor.execute("add", a=5, b=3)
print(result.success)  # True
print(result.result)   # 8

# 존재하지 않는 도구
result = await executor.execute("divide", a=10, b=2)
print(result.success)  # False
print(result.error)    # "Tool 'divide' not found"

# LLM 스키마로 변환
tools_for_openai = executor.to_openai_schemas()
tools_for_anthropic = executor.to_anthropic_schemas()
```

## 멀티라운드 도구 호출

에이전트는 도구를 순차적으로 여러 번 사용할 수 있습니다:

```python
@tool(description="웹 검색")
def web_search(query: str) -> str:
    return "Results for: " + query

@tool(description="텍스트 감성 분석")
def analyze_sentiment(text: str) -> str:
    return "positive" if len(text) > 5 else "neutral"

agent = Agent(
    name="analyst",
    role="리서치 분석가",
    model="gpt-4o-mini",
    tools=[web_search, analyze_sentiment],
    max_tool_rounds=10  # 최대 10번 도구 호출 허용
)

result = agent.run_sync(
    "'AI 트렌드 2025' 검색하고 결과 감성 분석해줘"
)
# LLM 실행 순서:
# 1. web_search("AI 트렌드 2025") 호출
# 2. 검색 결과 수신
# 3. analyze_sentiment(results) 호출
# 4. 감성 결과 수신
# 5. 최종 분석 제공
```

`max_tool_rounds` 파라미터(기본값: 10)는 무한 루프를 방지하고 도구 호출 횟수를 제한합니다.

## MCP 도구 통합

AgentChord는 MCP(Model Context Protocol) 도구를 에이전트 시스템에 연결합니다:

```python
# agent에 mcp_client를 전달하면 setup_mcp()로 도구 자동 등록
mcp_tools = await agent.setup_mcp()
# MCP 도구가 에이전트에 자동으로 추가됨
```

`setup_mcp()` 메서드:
1. MCP 서버에 연결
2. 사용 가능한 도구 탐색
3. MCPTool → AgentChord Tool 변환
4. 에이전트에 등록

## 에러 처리

도구는 에러 시 예외를 발생시키면 AgentChord가 처리합니다:

```python
@tool(description="제곱근 계산")
def sqrt(x: float) -> float:
    if x < 0:
        raise ValueError("음수의 제곱근은 구할 수 없음")
    return x ** 0.5

# 도구가 예외를 발생시키면 ToolResult가 포착
result = await sqrt.execute(x=-1)
print(result.success)  # False
print(result.error)    # "음수의 제곱근은 구할 수 없음"

# 에이전트는 계속 실행하며 다른 방법을 시도할 수 있음
```

## 베스트 프랙티스

### 1. 명확한 설명 작성

LLM이 도구를 이해할 수 있도록 명확한 설명을 작성합니다:

```python
# 좋음
@tool(description="양의 정수의 팩토리얼 계산")
def factorial(n: int) -> int:
    ...

# 덜 좋음
@tool(description="수학 함수")
def factorial(n: int) -> int:
    ...
```

### 2. 타입 힌트 사용

파라미터에 항상 타입 힌트를 포함합니다:

```python
# 좋음
@tool(description="온도 변환")
def celsius_to_fahrenheit(celsius: float) -> float:
    return (celsius * 9/5) + 32

# 타입 체크가 어려움
@tool(description="온도 변환")
def celsius_to_fahrenheit(celsius):
    ...
```

### 3. 단순한 반환 값

직렬화 가능한 단순한 값을 반환합니다:

```python
# 좋음
@tool(description="사용자 데이터 가져오기")
def get_user(user_id: int) -> dict:
    return {"id": user_id, "name": "Alice", "age": 30}

# 복잡한 객체는 직렬화가 어려움
@tool(description="사용자 데이터 가져오기")
def get_user(user_id: int) -> User:
    return User(user_id)
```

### 4. 에러를 예외로 처리

예외를 발생시키면 AgentChord가 처리합니다:

```python
# 좋음: 예외를 발생시킴
@tool(description="숫자 나누기")
def divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("0으로 나누기")
    return a / b

# 피해야 할 패턴: 에러 문자열 반환
@tool(description="숫자 나누기")
def divide(a: float, b: float) -> dict:
    try:
        return {"result": a / b, "error": None}
    except:
        return {"result": None, "error": "failed"}
```

### 5. 도구는 단일 책임

하나의 도구 = 하나의 책임:

```python
# 좋음: 관심사 분리
@tool(description="웹 검색")
def web_search(query: str) -> str:
    ...

@tool(description="텍스트에서 핵심 정보 추출")
def extract_key_info(text: str) -> dict:
    ...

# 덜 좋음: 하나의 도구에 여러 책임
@tool(description="웹 검색 후 정보 추출")
def search_and_extract(query: str) -> dict:
    ...
```

## 완전한 예제

```python
import asyncio
from agentchord import Agent, tool

@tool(description="현재 기온을 섭씨로 가져옴")
def get_temperature() -> float:
    return 22.5

@tool(description="섭씨를 화씨로 변환")
def celsius_to_fahrenheit(celsius: float) -> float:
    return (celsius * 9/5) + 32

@tool(description="기온이 쾌적한지 확인 (15-25도)")
def is_comfortable(celsius: float) -> bool:
    return 15 <= celsius <= 25

async def main():
    agent = Agent(
        name="weather_bot",
        role="날씨 도우미",
        model="gpt-4o-mini",
        tools=[get_temperature, celsius_to_fahrenheit, is_comfortable]
    )

    result = agent.run_sync(
        "현재 기온을 화씨로 알려주고 쾌적한지도 알려줘"
    )
    print(result.output)

if __name__ == "__main__":
    asyncio.run(main())
```

## 참고

- [메모리 가이드](memory.md) - 도구 호출 전반에 걸쳐 컨텍스트 유지
- [Agent API](../api/core.md) - Agent API 상세 정보
- [예제](../examples.md) - 도구 전체 예제
