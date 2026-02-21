# 스트리밍 가이드

AgentChord는 모든 LLM 프로바이더에서 스트리밍 응답을 지원합니다. 실시간으로 토큰을 전달하여 인터랙티브 애플리케이션을 구현할 수 있습니다.

## 빠른 시작

토큰 단위로 응답을 스트리밍합니다:

```python
from agentchord import Agent

agent = Agent(
    name="assistant",
    role="도움이 되는 AI",
    model="gpt-4o-mini"
)

# 응답 스트리밍
async for chunk in agent.stream("짧은 이야기 들려줘"):
    print(chunk.delta, end="", flush=True)
print()  # 스트림 후 줄바꿈
```

## StreamChunk

스트리밍된 각 응답은 `StreamChunk` 객체를 yield합니다:

```python
from agentchord.core.types import StreamChunk

# 각 청크는 다음을 포함:
chunk = StreamChunk(
    content="지금까지 누적된 전체 내용",  # 전체 누적 텍스트
    delta="이번 청크의 새 텍스트",         # 새로 추가된 텍스트만
    finish_reason=None,                    # 끝날 때까지 None
    usage=None                             # 마지막 청크에서만 사용량 통계
)

print(chunk.content)       # 누적된 전체 응답
print(chunk.delta)         # 이번 청크의 새 텍스트
print(chunk.finish_reason) # None (아직 완료되지 않음)
print(chunk.usage)         # None (마지막 청크가 아님)
```

### 속성

| 속성 | 타입 | 의미 |
|------|------|------|
| `content` | str | 지금까지 누적된 전체 응답 |
| `delta` | str | 이번 청크의 새 텍스트 |
| `finish_reason` | str or None | 마지막 청크에서 `"stop"`, 아니면 `None` |
| `usage` | Usage or None | 마지막 청크에서만 토큰 수 |

## 기본 스트리밍

도구 없이 스트리밍:

```python
agent = Agent(
    name="storyteller",
    role="창작 작가",
    model="gpt-4o-mini"
)

# 실시간으로 스트리밍하며 출력
async for chunk in agent.stream("고양이에 대한 짧은 시 써줘"):
    print(chunk.delta, end="", flush=True)

print()  # 마지막 줄바꿈
```

## 도구를 포함한 스트리밍

도구가 있는 에이전트는 하이브리드 방식을 사용합니다:

1. **도구 호출 단계**: 에이전트가 도구를 호출함 (스트리밍 없음)
2. **응답 단계**: 최종 응답이 스트리밍됨

```python
from agentchord import Agent, tool

@tool(description="현재 기온을 섭씨로 가져옴")
def get_temperature() -> float:
    return 22.5

@tool(description="섭씨를 화씨로 변환")
def celsius_to_fahrenheit(celsius: float) -> float:
    return (celsius * 9/5) + 32

agent = Agent(
    name="weather",
    role="날씨 어시스턴트",
    model="gpt-4o-mini",
    tools=[get_temperature, celsius_to_fahrenheit]
)

# 에이전트 실행 순서:
# 1. get_temperature() 호출 -> 22.5
# 2. celsius_to_fahrenheit(22.5) 호출 -> 72.5
# 3. 현재 기온에 대한 응답 스트리밍
async for chunk in agent.stream("화씨로 현재 기온은?"):
    print(chunk.delta, end="", flush=True)
```

실행 흐름:
```
사용자 쿼리
    ↓
에이전트가 도구 실행 (스트리밍 없음):
    - get_temperature() → 22.5
    - celsius_to_fahrenheit(22.5) → 72.5
    ↓
에이전트가 응답 생성 (스트리밍):
    - "현재 기온은 72.5 F..." [토큰 1]
    - "도로, 매우 쾌적한 날씨입니다." [토큰 2]
    ↓
사용자가 실시간 스트림 확인
```

도구 호출 단계는 조용히 진행되며 도구 결과가 준비된 후에야 청크가 시작됩니다.

## 스트리밍 아키텍처

### 도구 없는 경우

순수 스트리밍 모드:

```
LLM 프로바이더
    ↓ 토큰 스트리밍
StreamChunk 1: content="옛날"
StreamChunk 2: content="옛날 옛날"
StreamChunk 3: content="옛날 옛날에"
...
StreamChunk N: content="...", finish_reason="stop", usage=Usage(...)
```

### 도구가 있는 경우

하이브리드 모드 (도구에는 complete(), 최종 응답에는 stream()):

```
LLM 프로바이더
    ↓ complete()로 도구 호출 가져오기
도구 결과 준비
    ↓ 최종 응답을 stream()으로 스트리밍
StreamChunk 1: content="검색 결과에 따르면..."
StreamChunk 2: content="검색 결과에 따르면, AI는..."
...
StreamChunk N: content="...", finish_reason="stop"
```

## 사용량 통계

토큰 사용량은 마지막 청크에서만 확인 가능합니다:

```python
async for chunk in agent.stream("뭔가 알려줘"):
    if chunk.finish_reason == "stop":
        # 마지막 청크 - 사용량 정보 있음
        print(f"토큰: {chunk.usage.total_tokens}")
    else:
        # 마지막 청크가 아님 - 사용량 없음
        assert chunk.usage is None
```

스트리밍 후 마지막 결과 가져오기:

```python
last_chunk = None

async for chunk in agent.stream("쿼리"):
    last_chunk = chunk

if last_chunk and last_chunk.usage:
    print(f"최종 토큰 수: {last_chunk.usage.total_tokens}")
```

## 응답 구성

### 전체 응답 누적

```python
response_parts = []

async for chunk in agent.stream("안녕"):
    response_parts.append(chunk.delta)

full_response = "".join(response_parts)
print(f"전체 응답: {full_response}")
```

또는 이미 누적된 `content` 필드 사용:

```python
last_chunk = None

async for chunk in agent.stream("안녕"):
    last_chunk = chunk

full_response = last_chunk.content if last_chunk else ""
```

### 실시간 표시

```python
async for chunk in agent.stream("시 써줘"):
    # 토큰이 도착하는 즉시 출력
    print(chunk.delta, end="", flush=True)

print()  # 마지막 줄바꿈
```

### 버퍼링과 표시 혼합

```python
buffer = ""
buffer_size = 5  # 5글자가 될 때까지 버퍼링

async for chunk in agent.stream("이야기 들려줘"):
    buffer += chunk.delta

    if len(buffer) >= buffer_size or chunk.finish_reason:
        print(buffer, end="", flush=True)
        buffer = ""
```

## 에러 처리

스트리밍 중 예외가 발생할 수 있습니다:

```python
try:
    async for chunk in agent.stream("쿼리"):
        print(chunk.delta, end="", flush=True)
except asyncio.TimeoutError:
    print("\n스트림 타임아웃")
except Exception as e:
    print(f"\n스트림 에러: {e}")
```

스트림은 언제든지 실패할 수 있습니다:

```python
content = ""

try:
    async for chunk in agent.stream("쿼리"):
        content += chunk.delta
        print(chunk.delta, end="", flush=True)
except Exception as e:
    # 부분적인 내용은 사용 가능
    print(f"\n{len(content)}글자 후 에러 발생")
    print(f"부분 결과: {content}")
```

## 고급 사용법

### 커스텀 스트리밍 핸들러

```python
async def stream_with_handler(agent, prompt, handler):
    """커스텀 처리로 스트리밍."""
    async for chunk in agent.stream(prompt):
        await handler(chunk)

async def my_handler(chunk):
    if chunk.delta:
        print(f"[CHUNK] {chunk.delta}")
    if chunk.finish_reason:
        print(f"[DONE] usage={chunk.usage}")

# 사용
await stream_with_handler(agent, "이야기 들려줘", my_handler)
```

### 파일로 스트리밍

```python
with open("response.txt", "w") as f:
    async for chunk in agent.stream("에세이 써줘"):
        f.write(chunk.delta)
        f.flush()  # 각 청크 후 플러시
```

### WebSocket으로 스트리밍

```python
async def stream_to_websocket(agent, prompt, websocket):
    """WebSocket 클라이언트로 응답 스트리밍."""
    async for chunk in agent.stream(prompt):
        await websocket.send_json({
            "type": "chunk",
            "delta": chunk.delta,
            "finish_reason": chunk.finish_reason,
            "usage": chunk.usage.model_dump() if chunk.usage else None
        })
```

### 모든 청크 수집

```python
chunks = []

async for chunk in agent.stream("쿼리"):
    chunks.append(chunk)

print(f"총 청크: {len(chunks)}")
print(f"총 토큰: {chunks[-1].usage.total_tokens}")
print(f"평균 청크 크기: {sum(len(c.delta) for c in chunks) / len(chunks):.1f}글자")
```

## 프로바이더별 참고사항

모든 프로바이더는 동일한 스트리밍 인터페이스를 사용합니다:

```python
# OpenAI - 완전한 스트리밍 지원
agent = Agent(model="gpt-4o-mini")
async for chunk in agent.stream("안녕"):
    print(chunk.delta, end="", flush=True)

# Anthropic - 완전한 스트리밍 지원
agent = Agent(model="claude-3-5-sonnet")
async for chunk in agent.stream("안녕"):
    print(chunk.delta, end="", flush=True)

# Gemini - 완전한 스트리밍 지원
agent = Agent(model="gemini-2.0-flash")
async for chunk in agent.stream("안녕"):
    print(chunk.delta, end="", flush=True)

# Ollama - 완전한 스트리밍 지원
agent = Agent(model="ollama/llama3.2")
async for chunk in agent.stream("안녕"):
    print(chunk.delta, end="", flush=True)
```

## 성능 고려사항

### 토큰 효율성

스트리밍 여부와 상관없이 동일한 토큰 비용이 발생합니다:

```python
# 스트리밍 여부와 무관하게 동일한 비용
result1 = agent.run_sync("시 써줘")  # 150 토큰
# result2 스트리밍도 동일하게 150 토큰 사용
```

### 지연 시간

스트리밍은 더 나은 사용자 경험을 제공합니다. 전체 응답을 기다리지 않고 첫 토큰이 도착하는 즉시 표시됩니다:

```python
import time

# 스트리밍 없음: 전체 응답 대기
start = time.time()
result = agent.run_sync("쿼리")
elapsed = time.time() - start
# 사용자는 elapsed초 동안 아무것도 볼 수 없음

# 스트리밍: 콘텐츠를 즉시 표시
start = time.time()
first_chunk = True
async for chunk in agent.stream("쿼리"):
    if first_chunk:
        print(f"첫 토큰: {time.time() - start:.2f}초 후")
        first_chunk = False
    print(chunk.delta, end="", flush=True)
# 약 100-200ms 내에 콘텐츠가 표시되기 시작
```

## 베스트 프랙티스

### 1. 실시간 표시에는 항상 `flush=True`

```python
# 좋음: 즉시 콘텐츠 표시
async for chunk in agent.stream("쿼리"):
    print(chunk.delta, end="", flush=True)

# 나쁨: 콘텐츠가 버퍼링되어 일괄 표시될 수 있음
async for chunk in agent.stream("쿼리"):
    print(chunk.delta, end="")  # flush 없음
```

### 2. 에러를 우아하게 처리

```python
# 좋음: 중단 처리
try:
    async for chunk in agent.stream("쿼리"):
        print(chunk.delta, end="", flush=True)
except Exception as e:
    print(f"\n에러: {e}")
```

### 3. 완료 확인에 `finish_reason` 체크

```python
# 명시적 완료 확인
async for chunk in agent.stream("쿼리"):
    print(chunk.delta, end="", flush=True)
    if chunk.finish_reason == "stop":
        print("\n[완료]")
        break
```

### 4. 마지막 청크에서 사용량 수집

```python
# 좋음: 마지막 청크에서만 사용량 확인
final_chunk = None

async for chunk in agent.stream("쿼리"):
    final_chunk = chunk
    print(chunk.delta, end="", flush=True)

if final_chunk and final_chunk.usage:
    print(f"토큰: {final_chunk.usage.total_tokens}")
```

### 5. 긴 응답에 스트리밍 사용

```python
# 좋음: 인터랙티브한 경험을 위한 스트리밍
async for chunk in agent.stream("1000단어 에세이 써줘"):
    print(chunk.delta, end="", flush=True)

# 긴 응답에서는 덜 이상적: 전체 결과를 위한 오랜 대기
result = agent.run_sync("1000단어 에세이 써줘")
print(result.output)  # 출력 전 오랜 대기
```

## 완전한 예제

```python
import asyncio
from agentchord import Agent, tool

@tool(description="단어 수 계산")
def word_count(text: str) -> int:
    return len(text.split())

async def main():
    agent = Agent(
        name="writer",
        role="에세이 작가",
        model="gpt-4o-mini",
        tools=[word_count]
    )

    print("에세이:")
    print("-" * 40)

    total_chars = 0
    last_chunk = None

    async for chunk in agent.stream("AI에 대한 짧은 에세이 써줘"):
        print(chunk.delta, end="", flush=True)
        total_chars += len(chunk.delta)
        last_chunk = chunk

    print("\n" + "-" * 40)

    # 스트리밍 완료 후 사용량 확인 가능
    if last_chunk and last_chunk.finish_reason == "stop" and last_chunk.usage:
        print(f"\n사용 토큰: {last_chunk.usage.total_tokens}")
        print(f"총 글자 수: {total_chars}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 참고

- [도구 가이드](tools.md) - 스트리밍과 함께 도구 사용
- [프로바이더 가이드](providers.md) - 다양한 프로바이더로 스트리밍
- [Agent API](../api/core.md) - Agent API 상세 정보
- [예제](../examples.md) - 스트리밍 전체 예제
