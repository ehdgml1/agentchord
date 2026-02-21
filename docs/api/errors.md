# 에러 API 레퍼런스

AgentChord의 모든 예외 타입에 대한 완전한 API 레퍼런스입니다.

모든 예외는 `AgentChordError`를 상속하며, `retryable` 플래그로 재시도 가능 여부를 나타냅니다.

---

## 예외 계층 구조

```
AgentChordError
├── ConfigurationError
│   ├── MissingAPIKeyError
│   └── InvalidConfigError
├── LLMError
│   ├── RateLimitError
│   ├── AuthenticationError
│   ├── APIError
│   ├── TimeoutError
│   └── ModelNotFoundError
├── AgentError
│   ├── AgentExecutionError
│   └── AgentTimeoutError
├── CostLimitExceededError
└── WorkflowError
    ├── InvalidFlowError
    ├── AgentNotFoundInFlowError
    ├── WorkflowExecutionError
    └── EmptyWorkflowError
```

---

## AgentChordError

모든 AgentChord 예외의 기본 클래스입니다. `retryable` 플래그를 포함합니다.

```python
from agentchord.errors import AgentChordError

try:
    result = await agent.run("...")
except AgentChordError as e:
    print(f"에러: {e}")
    if e.retryable:
        print("재시도 가능한 에러입니다.")
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `message` | `str` | 필수 | 에러 메시지 |
| `retryable` | `bool` | `False` | 재시도 가능 여부 |

**속성:**

| 속성 | 타입 | 설명 |
|------|------|------|
| `retryable` | `bool` | 해당 에러가 재시도 가능한지 여부 |

---

## 설정 에러

### ConfigurationError

설정 관련 에러의 기본 클래스입니다. `retryable=False`로 고정됩니다.

```python
from agentchord.errors import ConfigurationError
```

**생성자 파라미터:**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `message` | `str` | 에러 메시지 |

---

### MissingAPIKeyError

API 키가 설정되지 않았을 때 발생합니다.

```python
from agentchord.errors import MissingAPIKeyError

try:
    provider = OpenAIProvider(model="gpt-4o-mini")
except MissingAPIKeyError as e:
    print(f"프로바이더: {e.provider}")
    # "OPENAI_API_KEY 환경 변수를 설정하세요."
```

**생성자 파라미터:**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `provider` | `str` | 프로바이더 이름 (예: `"openai"`) |

**속성:**

| 속성 | 타입 | 설명 |
|------|------|------|
| `provider` | `str` | 프로바이더 이름 |

> 에러 메시지 형식: `"API key for '{provider}' is not configured. Set the {PROVIDER}_API_KEY environment variable."`

---

### InvalidConfigError

설정 값이 유효하지 않을 때 발생합니다.

```python
from agentchord.errors import InvalidConfigError
```

**생성자 파라미터:**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `field` | `str` | 잘못된 설정 필드 이름 |
| `value` | `object` | 잘못된 값 |
| `reason` | `str` | 유효하지 않은 이유 |

**속성:**

| 속성 | 타입 | 설명 |
|------|------|------|
| `field` | `str` | 잘못된 필드 이름 |
| `value` | `object` | 잘못된 값 |

---

## LLM 에러

### LLMError

LLM 관련 에러의 기본 클래스입니다. 프로바이더와 모델 정보를 포함합니다.

```python
from agentchord.errors import LLMError

try:
    response = await provider.complete(messages)
except LLMError as e:
    print(f"프로바이더: {e.provider}, 모델: {e.model}")
    print(f"재시도 가능: {e.retryable}")
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `message` | `str` | 필수 | 에러 메시지 |
| `provider` | `str` | 필수 | LLM 프로바이더 이름 |
| `model` | `str \| None` | `None` | 모델 식별자 |
| `retryable` | `bool` | `False` | 재시도 가능 여부 |

**속성:**

| 속성 | 타입 | 설명 |
|------|------|------|
| `provider` | `str` | LLM 프로바이더 이름 |
| `model` | `str \| None` | 모델 식별자 |

---

### RateLimitError

API 속도 제한 초과 시 발생합니다. `retryable=True`로 고정됩니다.

```python
from agentchord.errors import RateLimitError

try:
    response = await provider.complete(messages)
except RateLimitError as e:
    if e.retry_after:
        print(f"{e.retry_after}초 후 재시도")
    else:
        print("잠시 후 재시도 필요")
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `message` | `str` | 필수 | 에러 메시지 |
| `provider` | `str` | 필수 | LLM 프로바이더 이름 |
| `model` | `str \| None` | `None` | 모델 식별자 |
| `retry_after` | `float \| None` | `None` | 권장 대기 시간 (초) |

**속성:**

| 속성 | 타입 | 설명 |
|------|------|------|
| `retry_after` | `float \| None` | API가 제공하는 재시도 대기 시간 (초) |

---

### AuthenticationError

인증 실패 시 발생합니다. `retryable=False`로 고정됩니다 (자격증명 수정 필요).

```python
from agentchord.errors import AuthenticationError
```

**생성자 파라미터:**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `message` | `str` | 에러 메시지 |
| `provider` | `str` | LLM 프로바이더 이름 |

---

### APIError

일반적인 API 에러입니다. `retryable=True`로 고정됩니다.

```python
from agentchord.errors import APIError

try:
    response = await provider.complete(messages)
except APIError as e:
    print(f"HTTP 상태 코드: {e.status_code}")
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `message` | `str` | 필수 | 에러 메시지 |
| `provider` | `str` | 필수 | LLM 프로바이더 이름 |
| `model` | `str \| None` | `None` | 모델 식별자 |
| `status_code` | `int \| None` | `None` | HTTP 상태 코드 |

**속성:**

| 속성 | 타입 | 설명 |
|------|------|------|
| `status_code` | `int \| None` | HTTP 응답 상태 코드 |

---

### TimeoutError

요청 타임아웃 시 발생합니다. `retryable=True`로 고정됩니다.

```python
from agentchord.errors import TimeoutError

try:
    response = await provider.complete(messages)
except TimeoutError as e:
    print(f"타임아웃: {e.timeout_seconds}초")
```

**생성자 파라미터:**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `message` | `str` | 에러 메시지 |
| `provider` | `str` | LLM 프로바이더 이름 |
| `model` | `str \| None` | 모델 식별자 |
| `timeout_seconds` | `float` | 타임아웃 시간 (초) |

**속성:**

| 속성 | 타입 | 설명 |
|------|------|------|
| `timeout_seconds` | `float` | 타임아웃 시간 (초) |

---

### ModelNotFoundError

지원하지 않는 모델을 사용하려 할 때 발생합니다. `retryable=False`로 고정됩니다.

```python
from agentchord.errors import ModelNotFoundError

try:
    provider = registry.create_provider("unknown-model-v99")
except ModelNotFoundError as e:
    print(f"모델 '{e.model}'은 지원하지 않습니다.")
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `model` | `str` | 필수 | 찾을 수 없는 모델 이름 |
| `provider` | `str \| None` | `None` | 프로바이더 이름 |

> 에러 메시지 형식: `"Model '{model}' not found or not supported by provider '{provider}'."`

---

## 에이전트 에러

### AgentError

에이전트 관련 에러의 기본 클래스입니다.

```python
from agentchord.errors import AgentError
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `message` | `str` | 필수 | 에러 메시지 |
| `agent_name` | `str` | 필수 | 에이전트 이름 |
| `retryable` | `bool` | `False` | 재시도 가능 여부 |

**속성:**

| 속성 | 타입 | 설명 |
|------|------|------|
| `agent_name` | `str` | 에러가 발생한 에이전트 이름 |

---

### AgentExecutionError

에이전트 실행 중 에러가 발생했을 때 사용합니다. `retryable=True`로 고정됩니다.

```python
from agentchord.errors import AgentExecutionError

try:
    result = await agent.run("...")
except AgentExecutionError as e:
    print(f"에이전트 '{e.agent_name}' 실행 실패")
```

**생성자 파라미터:**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `message` | `str` | 에러 메시지 |
| `agent_name` | `str` | 에이전트 이름 |

---

### AgentTimeoutError

에이전트 실행이 타임아웃될 때 발생합니다. `retryable=True`로 고정됩니다.

```python
from agentchord.errors import AgentTimeoutError

try:
    result = await agent.run("...")
except AgentTimeoutError as e:
    print(f"에이전트 '{e.agent_name}'가 {e.timeout_seconds}초 후 타임아웃")
```

**생성자 파라미터:**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `agent_name` | `str` | 타임아웃된 에이전트 이름 |
| `timeout_seconds` | `float` | 타임아웃 시간 (초) |

**속성:**

| 속성 | 타입 | 설명 |
|------|------|------|
| `timeout_seconds` | `float` | 타임아웃 시간 (초) |

> 에러 메시지 형식: `"Agent '{agent_name}' timed out after {timeout_seconds}s."`

---

## 비용 에러

### CostLimitExceededError

비용 한도를 초과했을 때 발생합니다. `retryable=False`로 고정됩니다.

```python
from agentchord.errors import CostLimitExceededError
from agentchord.tracking import CostTracker

tracker = CostTracker(budget_limit=1.0, raise_on_exceed=True)

try:
    result = await agent.run("...", callbacks=tracker.callbacks)
except CostLimitExceededError as e:
    print(f"현재 비용: ${e.current_cost:.4f}")
    print(f"한도: ${e.limit:.4f}")
    if e.agent_name:
        print(f"에이전트: {e.agent_name}")
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `current_cost` | `float` | 필수 | 현재 누적 비용 (USD) |
| `limit` | `float` | 필수 | 비용 한도 (USD) |
| `agent_name` | `str \| None` | `None` | 한도를 초과한 에이전트 이름 |

**속성:**

| 속성 | 타입 | 설명 |
|------|------|------|
| `current_cost` | `float` | 현재 누적 비용 (USD) |
| `limit` | `float` | 설정된 비용 한도 (USD) |
| `agent_name` | `str \| None` | 에이전트 이름 |

> 에러 메시지 형식: `"Cost limit exceeded: ${current_cost:.4f} >= ${limit:.4f}"`

---

## 워크플로우 에러

### WorkflowError

워크플로우 관련 에러의 기본 클래스입니다.

```python
from agentchord.errors import WorkflowError
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `message` | `str` | 필수 | 에러 메시지 |
| `retryable` | `bool` | `False` | 재시도 가능 여부 |

---

### InvalidFlowError

Flow DSL 문법이 잘못되었을 때 발생합니다. `retryable=False`로 고정됩니다.

```python
from agentchord.errors import InvalidFlowError

try:
    workflow = Workflow(agents=[a, b], flow="A -> -> B")
except InvalidFlowError as e:
    print(f"잘못된 플로우: {e.flow}")
    print(f"이유: {e.reason}")
```

**생성자 파라미터:**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `flow` | `str` | 잘못된 플로우 문자열 |
| `reason` | `str` | 파싱 에러 이유 |

**속성:**

| 속성 | 타입 | 설명 |
|------|------|------|
| `flow` | `str` | 잘못된 플로우 문자열 |
| `reason` | `str` | 에러 이유 |

> 에러 메시지 형식: `"Invalid flow '{flow}': {reason}"`

---

### AgentNotFoundInFlowError

플로우에서 존재하지 않는 에이전트를 참조할 때 발생합니다. `retryable=False`로 고정됩니다.

```python
from agentchord.errors import AgentNotFoundInFlowError

try:
    workflow = Workflow(agents=[a], flow="A -> NonExistent")
    await workflow.run("...")
except AgentNotFoundInFlowError as e:
    print(f"찾을 수 없는 에이전트: {e.agent_name}")
    print(f"사용 가능한 에이전트: {e.available}")
```

**생성자 파라미터:**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `agent_name` | `str` | 찾을 수 없는 에이전트 이름 |
| `available` | `list[str]` | 워크플로우에 등록된 에이전트 이름 목록 |

**속성:**

| 속성 | 타입 | 설명 |
|------|------|------|
| `agent_name` | `str` | 찾을 수 없는 에이전트 이름 |
| `available` | `list[str]` | 사용 가능한 에이전트 이름 목록 |

---

### WorkflowExecutionError

워크플로우 실행 중 에러가 발생했을 때 사용합니다. `retryable=True`로 고정됩니다.

```python
from agentchord.errors import WorkflowExecutionError

try:
    result = await workflow.run("...")
except WorkflowExecutionError as e:
    if e.failed_agent:
        print(f"실패한 에이전트: {e.failed_agent}")
    if e.step_index is not None:
        print(f"실패한 스텝 인덱스: {e.step_index}")
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `message` | `str` | 필수 | 에러 메시지 |
| `failed_agent` | `str \| None` | `None` | 실패한 에이전트 이름 |
| `step_index` | `int \| None` | `None` | 실패한 스텝의 인덱스 |

**속성:**

| 속성 | 타입 | 설명 |
|------|------|------|
| `failed_agent` | `str \| None` | 실패한 에이전트 이름 |
| `step_index` | `int \| None` | 실패한 스텝 인덱스 |

---

### EmptyWorkflowError

에이전트 없이 워크플로우를 실행하려 할 때 발생합니다. `retryable=False`로 고정됩니다.

```python
from agentchord.errors import EmptyWorkflowError

try:
    workflow = Workflow()  # 에이전트 없음
    await workflow.run("...")
except EmptyWorkflowError:
    print("에이전트를 추가한 후 실행하세요.")
```

**생성자 파라미터:**

없음 (고정 메시지: `"Workflow has no agents. Add agents before running."`)

---

## 에러 처리 패턴

### retryable 플래그 활용

```python
import asyncio
from agentchord.errors import AgentChordError

async def run_with_retry(agent, prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await agent.run(prompt)
        except AgentChordError as e:
            if not e.retryable or attempt == max_retries - 1:
                raise
            wait = 2 ** attempt  # 지수 백오프
            print(f"재시도 {attempt + 1}/{max_retries} - {wait}초 대기")
            await asyncio.sleep(wait)
```

### 에러 타입별 분기 처리

```python
from agentchord.errors import (
    RateLimitError,
    AuthenticationError,
    TimeoutError,
    CostLimitExceededError,
    AgentChordError,
)

try:
    result = await agent.run("...")
except RateLimitError as e:
    # 속도 제한 - 대기 후 재시도
    wait = e.retry_after or 60.0
    await asyncio.sleep(wait)
except AuthenticationError as e:
    # 인증 실패 - 즉시 중단
    raise SystemExit(f"API 키를 확인하세요: {e.provider}")
except TimeoutError as e:
    # 타임아웃 - 더 짧은 요청으로 재시도
    print(f"{e.timeout_seconds}초 타임아웃 발생")
except CostLimitExceededError as e:
    # 비용 한도 초과 - 중단
    print(f"비용 한도 ${e.limit:.2f} 초과 (현재: ${e.current_cost:.4f})")
except AgentChordError as e:
    # 기타 에러
    print(f"에러: {e}")
```

### ResilienceConfig와 함께 사용

```python
from agentchord import Agent
from agentchord.resilience import ResilienceConfig, RetryPolicy

# 재시도 가능한 에러를 자동으로 처리
config = ResilienceConfig(
    retry=RetryPolicy(
        max_retries=3,
        retryable_errors=[RateLimitError, TimeoutError, APIError],
    )
)

agent = Agent(
    name="resilient-agent",
    role="안정적인 에이전트",
    resilience=config,
)
```
