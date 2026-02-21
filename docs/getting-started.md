# 시작하기

AgentChord를 몇 분 안에 설치하고 첫 번째 에이전트를 실행합니다.

## 설치

```bash
# 로컬 개발 환경 (전체 extras 포함)
pip install -e ".[all]"

# 특정 프로바이더만 설치
pip install agentchord[openai]       # OpenAI (GPT 모델)
pip install agentchord[anthropic]    # Anthropic (Claude 모델)
pip install agentchord[all]          # 모든 프로바이더 + 프로토콜
```

**extras 목록:**

| extra | 포함 내용 |
|-------|----------|
| `openai` | openai 패키지 |
| `anthropic` | anthropic 패키지 |
| `rag` | RAG 파이프라인 (기본) |
| `rag-full` | RAG + ChromaDB + FAISS + sentence-transformers |
| `storage` | 영속 메모리 스토어 (JSON, SQLite) |
| `telemetry` | OpenTelemetry 추적·메트릭 |
| `mcp` | MCP 프로토콜 클라이언트 |
| `a2a` | A2A 프로토콜 서버 |
| `all` | 위 전체 포함 |

Gemini와 Ollama는 `httpx`(기본 포함)를 사용하므로 별도 extras가 필요 없습니다.

## 환경 변수 설정

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Google Gemini
export GEMINI_API_KEY="..."

# Ollama (로컬 실행 - API 키 불필요)
# 설치: https://ollama.ai
# 실행: ollama serve
export OLLAMA_BASE_URL="http://localhost:11434"  # 기본값
```

## 첫 번째 에이전트

```python
from agentchord import Agent

agent = Agent(
    name="assistant",
    role="도움이 되는 AI 어시스턴트",
    model="gpt-4o-mini",
)

result = agent.run_sync("양자 컴퓨팅이란 무엇인가요?")
print(result.output)
print(f"토큰: {result.usage.total_tokens}, 비용: ${result.cost:.4f}")
```

async 환경에서는 `await agent.run()`을 사용합니다:

```python
import asyncio
from agentchord import Agent

async def main():
    agent = Agent(name="assistant", role="AI 어시스턴트", model="gpt-4o-mini")
    result = await agent.run("머신러닝을 설명해줘")
    print(result.output)

asyncio.run(main())
```

## 도구 추가

`@tool` 데코레이터로 Python 함수를 에이전트에 바인딩합니다:

```python
from agentchord import Agent, tool

@tool(description="도시의 현재 날씨를 조회합니다")
def get_weather(city: str) -> str:
    return f"{city} 날씨: 22°C, 맑음"

@tool(description="수학 수식을 계산합니다")
def calculate(expression: str) -> str:
    return str(eval(expression))  # 간략화된 예제

agent = Agent(
    name="helper",
    role="도구를 사용하는 어시스턴트",
    model="gpt-4o-mini",
    tools=[get_weather, calculate],
)

# 에이전트가 필요에 따라 도구를 자동 호출합니다
result = agent.run_sync("서울 날씨와 15 곱하기 7은?")
print(result.output)
```

## 첫 번째 워크플로우

Flow DSL로 여러 에이전트를 연결합니다:

```python
from agentchord import Agent, Workflow

researcher = Agent(name="researcher", role="리서치 전문가", model="gpt-4o-mini")
writer = Agent(name="writer", role="콘텐츠 작성자", model="gpt-4o-mini")
reviewer = Agent(name="reviewer", role="품질 검토자", model="gpt-4o-mini")

# 순차 실행: 각 에이전트가 이전 에이전트의 출력을 입력으로 받음
workflow = Workflow(
    agents=[researcher, writer, reviewer],
    flow="researcher -> writer -> reviewer",
)

result = workflow.run_sync("2025년 AI 트렌드에 대해 작성해줘")
print(result.output)
print(f"총 비용: ${result.total_cost:.4f}")
```

### 병렬 실행

대괄호로 에이전트를 병렬 실행합니다:

```python
from agentchord import Agent, Workflow, MergeStrategy

analyst1 = Agent(name="technical", role="기술 분석가", model="gpt-4o-mini")
analyst2 = Agent(name="business", role="비즈니스 분석가", model="gpt-4o-mini")
synthesizer = Agent(name="synthesizer", role="보고서 종합자", model="gpt-4o-mini")

# 병렬 실행 후 순차 처리
workflow = Workflow(
    agents=[analyst1, analyst2, synthesizer],
    flow="[technical, business] -> synthesizer",
    merge_strategy=MergeStrategy.CONCAT_NEWLINE,
)

result = workflow.run_sync("LLM이 산업에 미치는 영향을 분석해줘")
```

### 혼합 패턴

```python
# A -> [B, C] -> D 패턴
workflow = Workflow(
    agents=[researcher, analyst1, analyst2, writer],
    flow="researcher -> [technical, business] -> writer",
)
```

## 메모리

에이전트가 이전 대화를 기억하게 합니다:

```python
from agentchord import Agent, ConversationMemory

memory = ConversationMemory()
agent = Agent(
    name="chatbot",
    role="대화형 어시스턴트",
    model="gpt-4o-mini",
    memory=memory,
)

await agent.run("내 이름은 Alice야")
result = await agent.run("내 이름이 뭐야?")
print(result.output)  # Alice를 기억합니다
```

## 비용 추적

에이전트 전반의 사용량을 모니터링합니다:

```python
from agentchord import Agent, CostTracker

tracker = CostTracker()
agent = Agent(
    name="tracked",
    role="어시스턴트",
    model="gpt-4o-mini",
    cost_tracker=tracker,
)

await agent.run("안녕!")
await agent.run("잘 지내?")

summary = tracker.get_summary()
print(f"총 비용: ${summary.total_cost:.4f}")
print(f"총 토큰: {summary.total_tokens:,}")
print(f"요청 횟수: {summary.request_count}")
```

## 스트리밍

실시간으로 응답을 스트리밍합니다:

```python
async for chunk in agent.stream("이야기를 들려줘"):
    print(chunk.delta, end="", flush=True)
print()
```

## 복원력

재시도, 서킷 브레이커, 타임아웃을 설정합니다:

```python
from agentchord import Agent, ResilienceConfig, RetryPolicy

agent = Agent(
    name="robust",
    role="안정적인 어시스턴트",
    model="gpt-4o-mini",
    resilience=ResilienceConfig(
        retry_policy=RetryPolicy(max_retries=3),
    ),
)
```

## 프로바이더 전환

모델 이름만 바꿔서 프로바이더를 전환합니다:

```python
# OpenAI
agent = Agent(name="a", role="도우미", model="gpt-4o-mini")

# Anthropic
agent = Agent(name="a", role="도우미", model="claude-3-5-sonnet")

# Google Gemini (별도 패키지 불필요)
agent = Agent(name="a", role="도우미", model="gemini-2.0-flash")

# Ollama 로컬 (API 키 불필요)
agent = Agent(name="a", role="도우미", model="ollama/llama3.2")
```

## 에러 처리

```python
from agentchord import Agent
from agentchord.errors.exceptions import (
    AgentExecutionError,
    MissingAPIKeyError,
    RateLimitError,
)

try:
    result = agent.run_sync("안녕")
except MissingAPIKeyError:
    print("API 키를 먼저 설정하세요")
except RateLimitError as e:
    print(f"요청 한도 초과, {e.retry_after}초 후 재시도")
except AgentExecutionError as e:
    print(f"실행 실패: {e}")
```

## 다음 단계

- [핵심 개념](guides/core-concepts.md) - Agent, Workflow, State 심화 학습
- [도구 가이드](guides/tools.md) - 고급 도구 생성 및 MCP 통합
- [프로바이더 가이드](guides/providers.md) - LLM 프로바이더 설정 및 커스터마이즈
- [복원력 가이드](guides/resilience.md) - 프로덕션용 에러 처리
- [API 레퍼런스](api/core.md) - 전체 API 문서
- [예제](examples.md) - 18개 실행 가능한 예제
