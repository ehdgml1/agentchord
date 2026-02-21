# LLM 프로바이더 가이드

AgentChord는 통합 인터페이스를 통해 여러 LLM 프로바이더를 지원합니다. 모델 이름을 기반으로 적절한 프로바이더를 자동으로 감지하고 생성합니다.

## 빠른 시작

모델 문자열만 바꾸면 프로바이더가 전환됩니다:

```python
from agentchord import Agent

# OpenAI
agent = Agent(name="ai", role="도우미", model="gpt-4o")

# Anthropic
agent = Agent(name="ai", role="도우미", model="claude-3-5-sonnet")

# Google Gemini
agent = Agent(name="ai", role="도우미", model="gemini-2.0-flash")

# Ollama (로컬)
agent = Agent(name="ai", role="도우미", model="ollama/llama3.2")
```

코드 변경 없이 모델 이름만 바꾸면 됩니다.

## Provider Registry

AgentChord는 레지스트리 시스템으로 프로바이더를 관리합니다:

```python
from agentchord.llm.registry import get_registry

registry = get_registry()

# 등록된 프로바이더 목록
providers = registry.list_providers()
print(providers)  # ["openai", "anthropic", "gemini", "ollama"]

# 모델 이름에서 프로바이더 감지
provider_name = registry.detect_provider("gpt-4o")
print(provider_name)  # "openai"

# 프로바이더 생성
provider = registry.create_provider("claude-3-5-sonnet")
```

### 자동 프로바이더 감지

모델 접두사가 프로바이더로 매핑됩니다:

| 프로바이더 | 모델 접두사 | 예시 |
|-----------|------------|------|
| OpenAI | `gpt-`, `o1`, `text-` | `gpt-4o`, `gpt-4o-mini`, `o1` |
| Anthropic | `claude-` | `claude-3-5-sonnet`, `claude-3-haiku` |
| Gemini | `gemini-` | `gemini-2.0-flash`, `gemini-1.5-pro` |
| Ollama | `ollama/` | `ollama/llama3.2`, `ollama/mistral` |

## OpenAI

공식 OpenAI API를 통한 GPT 모델.

### 사용 가능한 모델

- `gpt-4o` - 최신 플래그십 모델 (권장)
- `gpt-4o-mini` - 더 빠르고 저렴한 버전
- `gpt-4-turbo` - 이전 세대
- `gpt-3.5-turbo` - 오래된 버전, 매우 저렴
- `o1` - 추론 모델

### 설정

```python
import os
from agentchord import Agent

# 환경 변수로 API 키 설정
os.environ["OPENAI_API_KEY"] = "sk-..."

# 에이전트 생성 - API 키 자동 감지
agent = Agent(
    name="assistant",
    role="도움이 되는 AI",
    model="gpt-4o",
    temperature=0.7,
    max_tokens=4096
)

result = agent.run_sync("양자 컴퓨팅 설명해줘")
print(result.output)
```

### 커스텀 프로바이더

```python
from agentchord.llm.openai import OpenAIProvider
from agentchord import Agent

provider = OpenAIProvider(
    model="gpt-4o",
    api_key="sk-..."
)

agent = Agent(
    name="assistant",
    role="도움이 되는 AI",
    llm_provider=provider
)
```

### 비용 추적

OpenAI 비용이 자동으로 계산됩니다:

```python
result = agent.run_sync("안녕")
print(f"비용: ${result.cost:.4f}")
print(f"토큰: {result.usage.total_tokens}")
```

## Anthropic

Anthropic API를 통한 Claude 모델.

### 사용 가능한 모델

- `claude-3-5-sonnet-20241022` - 최신, 가장 균형적
- `claude-3-5-haiku-20241022` - 빠르고 효율적
- `claude-3-opus-20250219` - 가장 강력
- `claude-3-haiku` - 이전 버전

### 설정

```python
import os
from agentchord import Agent

# API 키 설정
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."

agent = Agent(
    name="assistant",
    role="전문 분석가",
    model="claude-3-5-sonnet-20241022",
    temperature=0.7
)

result = agent.run_sync("이 트렌드 분석해줘")
print(result.output)
```

### 커스텀 프로바이더

```python
from agentchord.llm.anthropic import AnthropicProvider
from agentchord import Agent

provider = AnthropicProvider(
    model="claude-3-5-sonnet-20241022",
    api_key="sk-ant-..."
)

agent = Agent(
    name="assistant",
    role="전문 분석가",
    llm_provider=provider
)
```

## Google Gemini

Google Gemini API를 통한 Gemini 모델.

### 사용 가능한 모델

- `gemini-2.0-flash` - 최신, 매우 빠름
- `gemini-1.5-pro` - 가장 강력
- `gemini-1.5-flash` - 빠른 변형
- `gemini-pro` - 이전 세대

### 설정

```python
import os
from agentchord import Agent

# API 키 설정
os.environ["GOOGLE_API_KEY"] = "AIza..."

agent = Agent(
    name="assistant",
    role="리서치 도우미",
    model="gemini-2.0-flash",
    temperature=0.5
)

result = agent.run_sync("최근 AI 발전 요약해줘")
print(result.output)
```

### 커스텀 프로바이더

```python
from agentchord.llm.gemini import GeminiProvider
from agentchord import Agent

provider = GeminiProvider(
    model="gemini-2.0-flash",
    api_key="AIza...",
    base_url="https://generativelanguage.googleapis.com/v1beta"  # 선택사항
)

agent = Agent(
    name="assistant",
    role="리서치 도우미",
    llm_provider=provider
)
```

## Ollama (로컬)

Ollama로 오픈 소스 모델을 로컬에서 실행합니다.

### 설치

```bash
# Ollama 설치
curl https://ollama.ai/install.sh | sh

# 모델 다운로드
ollama pull llama3.2
ollama pull mistral
```

### 사용 가능한 모델

- `ollama/llama3.2` - Meta의 Llama 3.2
- `ollama/mistral` - Mistral 7B
- `ollama/neural-chat` - Intel Neural Chat
- `ollama/openchat` - OpenChat
- ollama.com에서 사용 가능한 모든 모델

### 설정

```python
from agentchord import Agent

# Ollama는 기본적으로 포트 11434에서 로컬 실행
agent = Agent(
    name="local_assistant",
    role="로컬 도우미",
    model="ollama/llama3.2",
    temperature=0.7
)

result = agent.run_sync("당신은 무엇입니까?")
print(result.output)
```

### 커스텀 Ollama 서버

```python
from agentchord.llm.ollama import OllamaProvider
from agentchord import Agent

provider = OllamaProvider(
    model="llama3.2",
    base_url="http://192.168.1.100:11434"  # 다른 호스트
)

agent = Agent(
    name="remote_assistant",
    role="도우미",
    llm_provider=provider
)
```

### 하드웨어별 권장 모델

| 하드웨어 | 권장 모델 | 비고 |
|---------|---------|------|
| 8GB RAM | `llama3.2:1b` | 가장 작고 빠름 |
| 16GB RAM | `llama3.2:3b` 또는 `mistral` | 균형 잡힌 선택 |
| 32GB+ RAM | `llama3.2:8b` | 더 좋은 품질 |
| GPU | 모든 모델 | 훨씬 빠름 |

## 커스텀 프로바이더

비공개 또는 커스텀 모델을 위해 자체 프로바이더를 구현합니다:

```python
from agentchord.llm.base import BaseLLMProvider
from agentchord.core.types import LLMResponse, Message, StreamChunk, Usage
from typing import Any, AsyncIterator


class MyCustomProvider(BaseLLMProvider):
    def __init__(self, model: str, api_key: str):
        self._model = model
        self._api_key = api_key

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return "mycustom"

    async def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        """커스텀 API 호출."""
        # 구현
        return LLMResponse(
            content="응답 내용",
            model=self._model,
            usage=Usage(prompt_tokens=10, completion_tokens=5),
            finish_reason="stop"
        )

    async def stream(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """API에서 스트리밍 응답."""
        yield StreamChunk(
            content="First ",
            delta="First "
        )
        yield StreamChunk(
            content="First chunk",
            delta="chunk",
            finish_reason="stop",
            usage=Usage(prompt_tokens=10, completion_tokens=5)
        )

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return 0.01

    @property
    def cost_per_1k_output_tokens(self) -> float:
        return 0.02
```

### 커스텀 프로바이더 등록

```python
from agentchord.llm.registry import get_registry
from agentchord import Agent

# 팩토리 함수 생성
def create_custom(model: str, **kwargs) -> MyCustomProvider:
    return MyCustomProvider(model=model, **kwargs)

# 등록
registry = get_registry()
registry.register("mycustom", create_custom, ["custom-"])

# Agent에서 사용
agent = Agent(
    name="assistant",
    role="도우미",
    model="custom-mymodel",
    api_key="..."
)
```

## 비용 정보

주요 모델별 비용:

| 프로바이더 | 모델 | 입력/1k | 출력/1k |
|-----------|------|---------|---------|
| OpenAI | gpt-4o | $0.005 | $0.015 |
| OpenAI | gpt-4o-mini | $0.00015 | $0.0006 |
| Anthropic | claude-3-5-sonnet | $0.003 | $0.015 |
| Anthropic | claude-3-5-haiku | $0.00080 | $0.004 |
| Gemini | gemini-2.0-flash | $0.0001 | $0.0004 |
| Ollama | 모든 모델 | $0.00 | $0.00 |

비용은 각 실행의 `result.cost`로 확인합니다:

```python
result = agent.run_sync("안녕")
print(f"입력 토큰: {result.usage.prompt_tokens}")
print(f"출력 토큰: {result.usage.completion_tokens}")
print(f"총 토큰: {result.usage.total_tokens}")
print(f"예상 비용: ${result.cost:.4f}")
```

## 에러 처리

```python
from agentchord.errors.exceptions import ModelNotFoundError, APIError

try:
    result = agent.run_sync("안녕")
except ModelNotFoundError:
    print("알 수 없는 모델 이름")
except APIError as e:
    print(f"API 에러: {e}")
```

## 베스트 프랙티스

### 1. 요구사항에 맞게 선택

```python
# 최고 품질
agent = Agent(model="gpt-4o")

# 속도와 비용 균형
agent = Agent(model="gpt-4o-mini")

# 복잡한 추론
agent = Agent(model="claude-3-5-sonnet")

# 프라이버시 중요
agent = Agent(model="ollama/llama3.2")
```

### 2. 환경 변수 사용

```python
import os

# .env 파일에 정의
os.environ["OPENAI_API_KEY"] = "sk-..."
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."
os.environ["GOOGLE_API_KEY"] = "AIza..."

# 프로바이더가 환경에서 자동 감지
agent = Agent(name="ai", role="도우미", model="gpt-4o")
```

### 3. 비용 모니터링

```python
total_cost = 0.0

for query in queries:
    result = agent.run_sync(query)
    total_cost += result.cost
    print(f"쿼리 비용: ${result.cost:.4f}, 합계: ${total_cost:.4f}")
```

### 4. A/B 테스트 쉽게 전환

```python
import os

provider = os.environ.get("LLM_PROVIDER", "openai")
model = "gpt-4o" if provider == "openai" else "claude-3-5-sonnet"

agent = Agent(
    name="assistant",
    role="도우미",
    model=model
)
```

## 완전한 예제

```python
from agentchord import Agent
import os

async def main():
    # 프로바이더 설정
    os.environ["OPENAI_API_KEY"] = "sk-..."
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."

    # 다른 프로바이더로 에이전트 생성
    openai_agent = Agent(
        name="openai_bot",
        role="OpenAI 어시스턴트",
        model="gpt-4o"
    )

    anthropic_agent = Agent(
        name="anthropic_bot",
        role="Anthropic 어시스턴트",
        model="claude-3-5-sonnet-20241022"
    )

    local_agent = Agent(
        name="local_bot",
        role="로컬 어시스턴트",
        model="ollama/llama3.2"
    )

    # 응답 비교
    prompt = "양자 얽힘을 간단히 설명해줘"

    result1 = openai_agent.run_sync(prompt)
    print(f"OpenAI (${result1.cost:.4f}): {result1.output[:100]}...")

    result2 = anthropic_agent.run_sync(prompt)
    print(f"Anthropic (${result2.cost:.4f}): {result2.output[:100]}...")

    result3 = local_agent.run_sync(prompt)
    print(f"Local (무료): {result3.output[:100]}...")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## 참고

- [도구 가이드](tools.md) - 모든 프로바이더에서 도구 사용
- [메모리 가이드](memory.md) - 프로바이더 전반에서 컨텍스트 유지
- [복원력 가이드](resilience.md) - 프로바이더 장애 처리
- [Agent API](../api/core.md) - Agent API 상세 정보
