# AgentChord

> **Python asyncio 기반 멀티에이전트 프레임워크**
>
> MCP/A2A 프로토콜 네이티브 지원, 풀스택 RAG, 멀티에이전트 오케스트레이션, 내장 복원력 -- 래퍼가 아닌 프레임워크 수준의 엔지니어링.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-2%2C500%2B%20passed-brightgreen.svg)]()
[![Coverage](https://img.shields.io/badge/coverage-82%25-brightgreen.svg)]()
[![Typed](https://img.shields.io/badge/typing-mypy%20strict-blue.svg)]()
[![AsyncIO](https://img.shields.io/badge/async-first-purple.svg)]()

AgentChord는 [MCP](https://modelcontextprotocol.io/) (Model Context Protocol)와 [A2A](https://google.github.io/A2A/) (Agent-to-Agent)를 네이티브로 지원하는 async-first Python 멀티에이전트 프레임워크입니다. LLM 추상화부터 RAG 평가까지 모든 계층이 처음부터 설계, 구현, 테스트되었습니다.

---

## 왜 AgentChord인가?

대부분의 에이전트 프레임워크는 기존 API 위에 편의 계층을 씌웁니다. AgentChord는 다른 접근 방식을 취합니다: **프로토콜 수준의 추상화에서부터 위로 구축하여** 각 계층에 대한 완전한 제어와 깊은 이해를 제공합니다.

| | AgentChord | LangChain / LangGraph | CrewAI | AutoGen |
|---|---|---|---|---|
| **아키텍처** | 프로토콜 중심 (MCP + A2A 네이티브) | Chain / Graph 추상화 | 역할 기반 Crew | 대화 패턴 |
| **LLM 프로바이더** | 4개 내장 + `BaseLLMProvider` ABC | 80+ (통합 패키지) | LiteLLM 래퍼 | OpenAI 중심 |
| **RAG** | 풀스택 내장 (BM25 + Vector + RRF + RAGAS 평가) | 외부 (LangSmith) | 플러그인 | 없음 |
| **워크플로우** | Flow DSL (순차 / 병렬 / 복합) | Graph (노드 + 엣지) | Task 위임 | 멀티턴 대화 |
| **비용 추적** | 에이전트/워크플로우별 내장 (예산 한도) | 콜백 기반 | 내장 텔레메트리 | 없음 |
| **복원력** | CircuitBreaker + Retry + Timeout (Pydantic 설정) | LangSmith 경유 | 없음 | 없음 |
| **관측성** | OpenTelemetry 네이티브 + TraceCollector | LangSmith (SaaS) | 내장 | 없음 |
| **타입 안전성** | Pydantic v2 + mypy strict + `py.typed` (PEP 561) | 부분적 | 부분적 | 부분적 |

---

## 빠른 시작

### 설치

```bash
pip install agentchord

# 프로바이더별 설치
pip install agentchord[openai]
pip install agentchord[anthropic]
pip install agentchord[all]       # 전체

# RAG 지원
pip install agentchord[rag]       # ChromaDB
pip install agentchord[rag-full]  # ChromaDB + FAISS + SentenceTransformers + PDF
```

### 3줄 에이전트

```python
from agentchord import Agent

agent = Agent(name="assistant", role="AI 도우미", model="gpt-4o-mini")
result = agent.run_sync("AgentChord가 뭔가요?")
print(result.output)
# Tokens: 152, Cost: $0.0002
```

---

## 핵심 기능

### Agent

`run()` (async), `run_sync()` (동기), `stream()` (스트리밍)을 지원합니다. 도구 호출, 메모리, 비용 추적, 복원력 설정을 조합할 수 있습니다.

```python
from agentchord import Agent

agent = Agent(
    name="assistant",
    role="AI 도우미",
    model="gpt-4o-mini",
)
result = await agent.run("안녕하세요")
print(f"Tokens: {result.usage.total_tokens}, Cost: ${result.cost:.4f}")
```

### Workflow (Flow DSL)

`->` 는 순차 실행, `[]` 는 병렬 실행입니다. `MergeStrategy` 로 병렬 결과를 병합합니다.

```python
from agentchord import Agent, Workflow

researcher = Agent(name="researcher", role="조사 전문가", model="gpt-4o-mini")
writer = Agent(name="writer", role="작성자", model="gpt-4o-mini")
reviewer = Agent(name="reviewer", role="검토자", model="gpt-4o-mini")

# 순차: researcher -> writer -> reviewer
workflow = Workflow(
    agents=[researcher, writer, reviewer],
    flow="researcher -> writer -> reviewer",
)
result = workflow.run_sync("AI 트렌드에 대해 작성해주세요")

# 병렬 + 순차: 두 분석가 동시 실행 후 요약
workflow = Workflow(
    agents=[analyst1, analyst2, summarizer],
    flow="[analyst1, analyst2] -> summarizer",
)
```

### 도구

`@tool` 데코레이터로 함수를 도구로 변환합니다. 타입 힌트에서 JSON Schema가 자동 생성됩니다.

```python
from agentchord import Agent, tool

@tool(description="현재 날씨 조회")
def get_weather(city: str) -> str:
    return f"{city}: 22도, 맑음"

agent = Agent(
    name="weather-bot",
    role="날씨 도우미",
    model="gpt-4o-mini",
    tools=[get_weather],
)
result = await agent.run("서울 날씨 알려줘")
```

### 메모리

`ConversationMemory` (대화 이력), `SemanticMemory` (임베딩 기반 검색), `WorkingMemory` (키-값 스크래치패드)를 지원합니다. `JSONFileStore` 또는 `SQLiteStore` 로 영속화할 수 있습니다.

```python
from agentchord import Agent, ConversationMemory

memory = ConversationMemory()
agent = Agent(name="chatbot", role="대화 도우미", model="gpt-4o-mini", memory=memory)

await agent.run("제 이름은 Alice입니다")
await agent.run("제 이름이 뭐였죠?")  # Alice를 기억합니다
```

### LLM 프로바이더

OpenAI, Anthropic, Gemini, Ollama 4개 프로바이더를 내장합니다. 모두 동일한 `BaseLLMProvider` ABC를 구현하므로 한 줄 변경으로 교체할 수 있습니다.

```python
# OpenAI
agent = Agent(name="gpt", role="도우미", model="gpt-4o")

# Anthropic
agent = Agent(name="claude", role="도우미", model="claude-3-5-sonnet")

# Google Gemini (httpx 기반, OpenAI 호환 API)
agent = Agent(name="gemini", role="도우미", model="gemini-2.0-flash")

# Ollama (로컬, httpx 기반)
agent = Agent(name="local", role="도우미", model="ollama/llama3.2")
```

### 복원력

`RetryPolicy` (지수 백오프 + 지터), `CircuitBreaker` (장애 임계값 + half-open), `TimeoutManager` 를 `ResilienceConfig` 로 조합합니다.

```python
from agentchord import Agent, ResilienceConfig, RetryPolicy, CircuitBreaker

agent = Agent(
    name="robust",
    role="안정적인 도우미",
    model="gpt-4o-mini",
    resilience=ResilienceConfig(
        retry_policy=RetryPolicy(max_retries=3),
        circuit_breaker_enabled=True,
        circuit_breaker=CircuitBreaker(failure_threshold=5),
    ),
)
```

### 비용 추적

에이전트/워크플로우별 토큰 사용량과 비용을 추적합니다. 예산 한도를 설정할 수 있습니다.

```python
from agentchord import Agent, CostTracker

tracker = CostTracker(budget_limit=10.0)  # $10 예산
agent = Agent(name="tracked", role="도우미", model="gpt-4o-mini", cost_tracker=tracker)

await agent.run("안녕하세요!")
summary = tracker.get_summary()
print(f"총 비용: ${summary.total_cost:.4f}, 토큰: {summary.total_tokens:,}")
```

### 스트리밍

`agent.stream()` 으로 실시간 토큰 스트리밍을 합니다. 도구 호출이 필요한 경우 자동으로 hybrid 모드 (complete + stream)로 전환됩니다.

```python
async for chunk in agent.stream("이야기 하나 해주세요"):
    print(chunk.delta, end="", flush=True)
```

### 구조화된 출력

Pydantic 모델을 JSON Schema로 변환하여 LLM에 전달하고, 응답을 자동 검증합니다.

```python
from pydantic import BaseModel
from agentchord import Agent, OutputSchema

class MovieReview(BaseModel):
    title: str
    rating: float
    summary: str
    pros: list[str]
    cons: list[str]

agent = Agent(name="critic", role="영화 평론가", model="gpt-4o-mini")
result = await agent.run(
    "인셉션 리뷰해줘",
    output_schema=OutputSchema(MovieReview),
)
review = result.structured_output  # 검증된 MovieReview 인스턴스
```

### RAG

`RAGPipeline` 으로 문서 수집 -> 검색 -> 생성을 처리합니다. BM25 + Vector 하이브리드 검색 (RRF fusion, k=60)과 RAGAS 스타일 평가 (Faithfulness, Answer Relevancy, Context Relevancy)를 내장합니다.

```python
from agentchord import RAGPipeline, Document
from agentchord.rag.embeddings.openai import OpenAIEmbeddings
from agentchord.llm.openai import OpenAIProvider

pipeline = RAGPipeline(
    llm=OpenAIProvider(model="gpt-4o-mini"),
    embedding_provider=OpenAIEmbeddings(),
)

# 문서 수집
docs = [Document(id="doc1", content="AgentChord는 멀티에이전트 프레임워크입니다...")]
await pipeline.ingest_documents(docs)

# 하이브리드 검색 + 생성
response = await pipeline.query("AgentChord가 뭔가요?")
print(response.answer)
```

**RAG 구성 요소:**

| 계층 | 구현체 |
|------|--------|
| 문서 로더 | Text, PDF, Web, Directory |
| 청킹 | Recursive, Semantic, Parent-Child |
| 임베딩 | OpenAI, Ollama, Gemini, SentenceTransformer |
| 벡터 스토어 | InMemory, ChromaDB, FAISS |
| 검색 | BM25 (Okapi), Vector, Hybrid (RRF) |
| 리랭킹 | CrossEncoder, LLM 기반 |
| 평가 | Faithfulness, Answer Relevancy, Context Relevancy |

### 멀티에이전트 오케스트레이션

`AgentTeam` 으로 여러 에이전트를 조율합니다. 4가지 전략을 지원하며, `consult` 기능으로 에이전트 간 상호 참조가 가능합니다.

```python
from agentchord import Agent, AgentTeam

researcher = Agent(name="researcher", role="조사 전문가", model="gpt-4o-mini")
writer = Agent(name="writer", role="작성자", model="gpt-4o-mini")
reviewer = Agent(name="reviewer", role="검토자", model="gpt-4o-mini")

team = AgentTeam(
    name="content-team",
    members=[researcher, writer, reviewer],
    strategy="coordinator",  # coordinator, round_robin, debate, map_reduce
    max_rounds=5,
)

result = await team.run("AI 안전에 대한 블로그 글을 작성하세요")
print(f"비용: ${result.total_cost:.4f}, 라운드: {result.rounds}")
```

**오케스트레이션 전략:**

| 전략 | 패턴 | 적합한 작업 |
|------|------|-------------|
| `coordinator` | 도구 기반 위임 | 계층적 복잡 작업 |
| `round_robin` | 순차 파이프라인 | 반복 개선 워크플로우 |
| `debate` | 다관점 합성 | 의사결정, 브레인스토밍 |
| `map_reduce` | 병렬 분해 + 집계 | 데이터 처리, 분할 정복 |

### MCP / A2A 프로토콜

MCP 클라이언트로 외부 도구 서버에 연결하고, A2A 서버/클라이언트로 에이전트 간 통신을 합니다.

```python
from agentchord import Agent, MCPClient

async with MCPClient() as mcp:
    await mcp.connect("npx", ["-y", "@anthropic/mcp-server-github"])
    agent = Agent(name="dev", role="개발자", model="gpt-4o", mcp_client=mcp)
    await agent.setup_mcp()
    result = await agent.run("최근 이슈 목록 보여줘")
```

---

## 설치 옵션

| Extra | 포함 패키지 | 용도 |
|-------|-------------|------|
| `openai` | openai | OpenAI 프로바이더 |
| `anthropic` | anthropic | Anthropic 프로바이더 |
| `mcp` | mcp | MCP 클라이언트 |
| `a2a` | starlette, uvicorn | A2A 서버 |
| `storage` | aiosqlite | SQLiteStore 영속 메모리 |
| `telemetry` | opentelemetry-api, opentelemetry-sdk | OpenTelemetry 추적 |
| `rag` | chromadb | ChromaDB 벡터 스토어 |
| `rag-full` | chromadb, faiss-cpu, numpy, sentence-transformers, pypdf | RAG 전체 기능 |
| `all` | 위 모든 패키지 | 전체 설치 |

코어 의존성은 4개뿐입니다: `pydantic`, `httpx`, `rich`, `tenacity`.

Gemini와 Ollama는 추가 패키지 없이 httpx로 직접 통신합니다.

---

## 예제

[examples/](examples/) 디렉토리에 18개의 예제가 있습니다:

| # | 파일 | 설명 |
|---|------|------|
| 01 | hello_world.py | 기본 Agent 사용법 |
| 02 | multi_model.py | 여러 LLM 프로바이더 |
| 03 | workflow_sequential.py | 순차 워크플로우 |
| 04 | workflow_parallel.py | 병렬 워크플로우 |
| 05 | with_mcp.py | MCP 통합 |
| 06 | a2a_server.py | A2A 프로토콜 |
| 07 | memory_system.py | 메모리 시스템 |
| 08 | cost_tracking.py | 비용 추적 |
| 09 | tools.py | 도구 시스템 |
| 10 | streaming.py | 스트리밍 + 도구 호출 |
| 11 | full_agent.py | 전체 기능 통합 |
| 12 | memory_persistence.py | 영속 메모리 (JSON, SQLite) |
| 12 | lifecycle_management.py | async 컨텍스트 매니저 |
| 12 | trace_collector.py | 실행 추적 + 내보내기 |
| 13 | structured_output.py | Pydantic 구조화된 출력 |
| 14 | rag_pipeline.py | RAG 파이프라인 |
| 15 | multi_agent_team.py | 멀티에이전트 팀 |
| 16 | debate_strategy.py | 토론 전략 |

---

## 문서

전체 문서는 [agentchord.github.io/agentchord](https://agentchord.github.io/agentchord)에서 확인할 수 있습니다.

- [시작하기](https://agentchord.github.io/agentchord/getting-started/)
- [핵심 개념](https://agentchord.github.io/agentchord/core-concepts/)
- 가이드: [도구](https://agentchord.github.io/agentchord/guides/tools/) / [메모리](https://agentchord.github.io/agentchord/guides/memory/) / [프로바이더](https://agentchord.github.io/agentchord/guides/providers/) / [복원력](https://agentchord.github.io/agentchord/guides/resilience/) / [스트리밍](https://agentchord.github.io/agentchord/guides/streaming/) / [RAG](https://agentchord.github.io/agentchord/guides/rag/) / [오케스트레이션](https://agentchord.github.io/agentchord/guides/orchestration/)
- [API 레퍼런스](https://agentchord.github.io/agentchord/api/)

---

## 개발

```bash
# 개발 환경 설치
pip install -e ".[all]"
pip install pytest pytest-asyncio pytest-cov ruff mypy

# 테스트
make test              # 전체 테스트
make test-unit         # 단위 테스트
make test-integration  # 통합 테스트
make test-cov          # 커버리지 리포트

# 코드 품질
make lint              # Ruff 린터
make format            # Ruff 포매터
make typecheck         # mypy strict 모드
make bench             # 23개 벤치마크

make all               # 전체 체크
```

**CI/CD**: GitHub Actions (Python 3.10 / 3.11 / 3.12 매트릭스), pre-commit hooks (ruff), 커버리지 임계값 75%, OIDC trusted publisher를 통한 PyPI 배포.

---

## 라이선스

MIT License -- 자세한 내용은 [LICENSE](LICENSE)를 참고하세요.
