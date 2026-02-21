# LLM 프로바이더 API 레퍼런스

AgentChord의 LLM 프로바이더에 대한 완전한 API 레퍼런스입니다. OpenAI, Anthropic, Gemini, Ollama 및 커스텀 프로바이더를 다룹니다.

---

## BaseLLMProvider

모든 LLM 프로바이더가 구현해야 하는 추상 기본 클래스입니다.

```python
from agentchord.llm.base import BaseLLMProvider
from agentchord.core.types import LLMResponse, Message, StreamChunk

class MyProvider(BaseLLMProvider):
    @property
    def model(self) -> str:
        return "my-model-v1"

    @property
    def provider_name(self) -> str:
        return "my-provider"

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return 0.001

    @property
    def cost_per_1k_output_tokens(self) -> float:
        return 0.002

    async def complete(self, messages, *, temperature=0.7, max_tokens=4096, **kwargs):
        # 구현
        ...

    async def stream(self, messages, *, temperature=0.7, max_tokens=4096, **kwargs):
        # 구현
        ...
```

**추상 프로퍼티:**

| 프로퍼티 | 타입 | 설명 |
|----------|------|------|
| `model` | `str` | 모델 식별자 반환 |
| `provider_name` | `str` | 프로바이더 이름 반환 (예: "openai", "anthropic") |
| `cost_per_1k_input_tokens` | `float` | 입력 1,000 토큰당 USD 비용 |
| `cost_per_1k_output_tokens` | `float` | 출력 1,000 토큰당 USD 비용 |

**추상 메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `complete` | `async complete(messages: list[Message], *, temperature: float = 0.7, max_tokens: int = 4096, **kwargs) -> LLMResponse` | `LLMResponse` | 메시지 목록에 대한 컴플리션 생성 |
| `stream` | `async stream(messages: list[Message], *, temperature: float = 0.7, max_tokens: int = 4096, **kwargs) -> AsyncIterator[StreamChunk]` | `AsyncIterator[StreamChunk]` | 응답을 스트리밍으로 생성 |

**구체적 메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `calculate_cost` | `calculate_cost(input_tokens: int, output_tokens: int) -> float` | `float` | 토큰 사용량에 대한 예상 비용 계산 (USD) |

---

## OpenAIProvider

OpenAI API를 사용하는 LLM 프로바이더입니다.

```python
from agentchord.llm.openai import OpenAIProvider
from agentchord.core.types import Message

# API 키는 OPENAI_API_KEY 환경 변수에서 자동 로드
provider = OpenAIProvider(model="gpt-4o-mini")
response = await provider.complete([Message.user("안녕하세요!")])
print(response.content)

# 커스텀 설정
provider = OpenAIProvider(
    model="gpt-4o",
    api_key="sk-...",
    base_url="https://my-proxy.example.com/v1",
    timeout=30.0,
)
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `model` | `str` | `"gpt-4o-mini"` | 모델 식별자 |
| `api_key` | `str \| None` | `None` | OpenAI API 키. None이면 `OPENAI_API_KEY` 환경 변수 사용 |
| `base_url` | `str \| None` | `None` | 커스텀 API 기본 URL (프록시 서버용) |
| `timeout` | `float` | `60.0` | 요청 타임아웃 (초) |

**지원 모델 및 가격 (2025년 기준):**

| 모델 | 입력 ($/1K 토큰) | 출력 ($/1K 토큰) |
|------|----------------|----------------|
| `gpt-4o` | $0.0025 | $0.0100 |
| `gpt-4o-mini` | $0.00015 | $0.0006 |
| `gpt-4-turbo` | $0.0100 | $0.0300 |
| `gpt-4.1` | $0.0020 | $0.0080 |
| `gpt-4.1-mini` | $0.0004 | $0.0016 |
| `o1` | $0.0150 | $0.0600 |
| `o1-mini` | $0.0030 | $0.0120 |

**발생 가능한 예외:**

| 예외 | 설명 |
|------|------|
| `MissingAPIKeyError` | API 키가 설정되지 않음 |
| `AuthenticationError` | API 키가 유효하지 않음 |
| `RateLimitError` | 속도 제한 초과 (재시도 가능) |
| `TimeoutError` | 요청 타임아웃 (재시도 가능) |
| `APIError` | 기타 API 오류 |

---

## AnthropicProvider

Anthropic Claude API를 사용하는 LLM 프로바이더입니다.

```python
from agentchord.llm.anthropic import AnthropicProvider
from agentchord.core.types import Message

# API 키는 ANTHROPIC_API_KEY 환경 변수에서 자동 로드
provider = AnthropicProvider(model="claude-3-5-sonnet-latest")
response = await provider.complete([Message.user("안녕하세요!")])
print(response.content)

# 커스텀 설정
provider = AnthropicProvider(
    model="claude-opus-4-6",
    api_key="sk-ant-...",
    timeout=120.0,
)
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `model` | `str` | `"claude-sonnet-4-5-20250929"` | 모델 식별자 |
| `api_key` | `str \| None` | `None` | Anthropic API 키. None이면 `ANTHROPIC_API_KEY` 환경 변수 사용 |
| `base_url` | `str \| None` | `None` | 커스텀 API 기본 URL |
| `timeout` | `float` | `60.0` | 요청 타임아웃 (초) |

**지원 모델 및 가격 (2025년 기준):**

| 모델 | 입력 ($/1K 토큰) | 출력 ($/1K 토큰) |
|------|----------------|----------------|
| `claude-opus-4-6` | $0.0050 | $0.0250 |
| `claude-sonnet-4-5-20250929` | $0.0030 | $0.0150 |
| `claude-haiku-4-5-20251001` | $0.0010 | $0.0050 |
| `claude-3-5-sonnet-20241022` | $0.0030 | $0.0150 |
| `claude-3-5-haiku-20241022` | $0.0008 | $0.0040 |
| `claude-3-opus-20240229` | $0.0150 | $0.0750 |
| `claude-3-haiku-20240307` | $0.00025 | $0.00125 |

> **주의:** Claude는 최대 temperature가 1.0입니다. 더 높은 값을 지정하면 자동으로 1.0으로 제한됩니다.

---

## GeminiProvider

Google Gemini API를 사용하는 LLM 프로바이더입니다. OpenAI 호환 엔드포인트를 httpx로 직접 통신합니다.

- **엔드포인트:** `https://generativelanguage.googleapis.com/v1beta/openai/`

```python
from agentchord.llm.gemini import GeminiProvider
from agentchord.core.types import Message

# API 키는 GOOGLE_API_KEY 환경 변수에서 자동 로드
provider = GeminiProvider(model="gemini-2.0-flash")
response = await provider.complete([Message.user("안녕하세요!")])
print(response.content)

# 스트리밍
async for chunk in provider.stream([Message.user("긴 글 써줘")]):
    print(chunk.delta, end="")
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `model` | `str` | `"gemini-2.0-flash"` | 모델 식별자 |
| `api_key` | `str \| None` | `None` | Google API 키. None이면 `GOOGLE_API_KEY` 환경 변수 사용 |
| `timeout` | `float` | `60.0` | 요청 타임아웃 (초) |

**지원 모델 및 가격 (2025년 기준):**

| 모델 | 입력 ($/1K 토큰) | 출력 ($/1K 토큰) |
|------|----------------|----------------|
| `gemini-2.5-pro` | $0.00125 | $0.00500 |
| `gemini-2.0-flash` | $0.0001 | $0.0004 |
| `gemini-2.0-flash-lite` | $0.0 | $0.0 |
| `gemini-1.5-flash` | $0.000075 | $0.0003 |
| `gemini-1.5-pro` | $0.00125 | $0.0050 |

> **API 키 발급:** [Google AI Studio](https://aistudio.google.com/app/apikey)에서 무료로 발급합니다.

---

## OllamaProvider

로컬 또는 원격 Ollama 서버를 사용하는 LLM 프로바이더입니다. 완전 무료 (로컬 실행).

```python
from agentchord.llm.ollama import OllamaProvider
from agentchord.core.types import Message

# 로컬 기본 서버 (http://localhost:11434)
provider = OllamaProvider(model="ollama/llama3.2")
response = await provider.complete([Message.user("안녕하세요!")])
print(response.content)

# 원격 서버
provider = OllamaProvider(
    model="ollama/mistral",
    base_url="http://my-ollama-server:11434",
    timeout=180.0,
)
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `model` | `str` | 필수 | `"ollama/"` 접두사를 포함한 모델 이름 (예: `"ollama/llama3.2"`) |
| `base_url` | `str` | `"http://localhost:11434"` | Ollama 서버 URL |
| `timeout` | `float` | `120.0` | 요청 타임아웃 (초). 로컬 모델 특성상 기본값이 큼 |

> **특이사항:**
> - 비용은 항상 $0.0 (로컬 실행)
> - API 호출 시 `"ollama/"` 접두사를 자동으로 제거
> - Ollama 설치 및 실행이 필요: [https://ollama.com/](https://ollama.com/)
> - 모델 풀 필요: `ollama pull llama3.2`

---

## ProviderRegistry

LLM 프로바이더 등록 및 모델명 기반 자동 감지를 관리하는 레지스트리입니다.

```python
from agentchord.llm.registry import ProviderRegistry, get_registry

# 전역 기본 레지스트리 (최초 호출 시 기본 프로바이더 자동 등록)
registry = get_registry()

# 등록된 프로바이더 목록
print(registry.list_providers())  # ["openai", "anthropic", "ollama", "gemini"]

# 모델명으로 프로바이더 감지
name = registry.detect_provider("gpt-4o")         # "openai"
name = registry.detect_provider("claude-3-5-sonnet") # "anthropic"
name = registry.detect_provider("ollama/llama3.2") # "ollama"
name = registry.detect_provider("gemini-2.0-flash") # "gemini"

# 프로바이더 인스턴스 생성
provider = registry.create_provider("gpt-4o-mini")
```

**`get_registry()` 함수:**

전역 기본 레지스트리를 지연 초기화로 반환합니다. 최초 호출 시 OpenAI, Anthropic, Ollama, Gemini를 자동 등록합니다.

**메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `register` | `register(name: str, factory: Callable, prefixes: list[str], default_cost_input: float = 0.0, default_cost_output: float = 0.0) -> None` | `None` | 프로바이더 등록 |
| `unregister` | `unregister(name: str) -> bool` | `bool` | 프로바이더 등록 해제. 성공 시 True 반환 |
| `detect_provider` | `detect_provider(model: str) -> str` | `str` | 모델명으로 프로바이더 이름 감지. 실패 시 `ModelNotFoundError` |
| `create_provider` | `create_provider(model: str, **kwargs) -> BaseLLMProvider` | `BaseLLMProvider` | 모델명에 맞는 프로바이더 인스턴스 생성 |
| `list_providers` | `list_providers() -> list[str]` | `list[str]` | 등록된 프로바이더 이름 목록 반환 |
| `get_provider_info` | `get_provider_info(name: str) -> ProviderInfo \| None` | `ProviderInfo \| None` | 프로바이더 메타데이터 반환 |

**기본 등록 프리픽스:**

| 프로바이더 | 감지 프리픽스 |
|-----------|------------|
| `openai` | `"gpt-"`, `"o1"`, `"text-"` |
| `anthropic` | `"claude-"` |
| `ollama` | `"ollama/"` |
| `gemini` | `"gemini-"` |

**커스텀 프로바이더 등록 예제:**

```python
from agentchord.llm.registry import get_registry

def my_factory(model: str, **kwargs):
    return MyCustomProvider(model=model)

registry = get_registry()
registry.register(
    name="my-provider",
    factory=my_factory,
    prefixes=["mymodel-"],  # "mymodel-v1", "mymodel-v2" 등을 자동 감지
    default_cost_input=0.001,
    default_cost_output=0.002,
)

# 이후 Agent에서 자동으로 사용
from agentchord import Agent
agent = Agent(name="agent", role="...", model="mymodel-v1")
```
