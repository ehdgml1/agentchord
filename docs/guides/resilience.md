# 복원력 가이드

AgentChord는 프로덕션에서 장애를 우아하게 처리하는 복원력 기능을 제공합니다. 재시도 정책, 서킷 브레이커, 타임아웃 관리를 포함합니다.

## 빠른 시작

합리적인 기본값으로 복원력을 활성화합니다:

```python
from agentchord import Agent
from agentchord.resilience import create_default_resilience

# 기본값이 적용된 복원력 설정 생성
resilience = create_default_resilience()

agent = Agent(
    name="robust_assistant",
    role="안정적인 도우미",
    model="gpt-4o-mini",
    resilience=resilience
)

# 일시적 장애 시 자동으로 재시도
result = agent.run_sync("안녕")
print(result.output)
```

## 실행 순서

AgentChord는 다음 순서로 복원력을 적용합니다 (외부에서 내부 순):

1. **Timeout** - 전체 작업의 최대 시간
2. **Circuit Breaker** - 연쇄 장애 방지
3. **Retry** - 자동 재시도와 백오프
4. **Function** - 실제 API 호출

```
사용자 → [Timeout → Circuit Breaker → Retry] → LLM API
```

## RetryPolicy

일시적 장애 시 설정 가능한 백오프로 자동 재시도합니다.

### 기본 재시도

```python
from agentchord.resilience import RetryPolicy, RetryStrategy

# 단순 고정 재시도: 3번 시도, 1초 지연
policy = RetryPolicy(
    max_retries=3,
    strategy=RetryStrategy.FIXED,
    base_delay=1.0
)

# 재시도와 함께 실행
result = await policy.execute(some_async_func, arg1, arg2)
```

### 재시도 전략

#### FIXED (고정) 지연

재시도 간격이 동일합니다:

```python
policy = RetryPolicy(
    max_retries=3,
    strategy=RetryStrategy.FIXED,
    base_delay=2.0  # 재시도 간 2초
)
# 시도: 0s → 2s → 4s (2초 고정 지연)
```

#### EXPONENTIAL (지수) 백오프

API 장애에 권장되는 지수적으로 증가하는 지연:

```python
policy = RetryPolicy(
    max_retries=4,
    strategy=RetryStrategy.EXPONENTIAL,
    base_delay=1.0,
    max_delay=60.0
)
# 1번째 시도: 즉시
# 2번째 시도: 1초 지연 (1 * 2^0)
# 3번째 시도: 2초 지연 (1 * 2^1)
# 4번째 시도: 4초 지연 (1 * 2^2)
# 5번째 시도: 8초 지연 (1 * 2^3)
```

#### LINEAR (선형) 백오프

선형적으로 증가하는 지연:

```python
policy = RetryPolicy(
    max_retries=3,
    strategy=RetryStrategy.LINEAR,
    base_delay=1.0
)
# 1번째 시도: 즉시
# 2번째 시도: 1초 지연 (1 * 1)
# 3번째 시도: 2초 지연 (1 * 2)
# 4번째 시도: 3초 지연 (1 * 3)
```

### Jitter (지터)

천둥떼 현상(Thundering Herd)을 방지하기 위해 무작위성을 추가합니다:

```python
policy = RetryPolicy(
    max_retries=3,
    strategy=RetryStrategy.EXPONENTIAL,
    base_delay=1.0,
    jitter=True,       # 무작위 지터 추가
    jitter_factor=0.1  # 지연의 +/- 10%
)
# 지터 적용 시 지연이 약간 변동: 0.9s-1.1s, 1.8s-2.2s 등
```

### 재시도 가능한 에러

특정 예외만 재시도합니다:

```python
from agentchord.errors.exceptions import RateLimitError, TimeoutError

policy = RetryPolicy(
    max_retries=3,
    retryable_errors=(
        RateLimitError,
        TimeoutError,
        ConnectionError,
    )
)

# RateLimitError에는 재시도함
# ValueError 등 다른 예외는 재시도하지 않음
```

기본 재시도 가능 에러:
- `RateLimitError`
- `TimeoutError`
- `APIError`
- `ConnectionError`
- `asyncio.TimeoutError`

### 에이전트에서 사용

```python
from agentchord import Agent
from agentchord.resilience import RetryPolicy, RetryStrategy, ResilienceConfig

policy = RetryPolicy(
    max_retries=3,
    strategy=RetryStrategy.EXPONENTIAL,
    base_delay=1.0,
    max_delay=30.0,
    jitter=True
)

agent = Agent(
    name="resilient",
    role="안정적인 어시스턴트",
    model="gpt-4o-mini",
    resilience=ResilienceConfig(
        retry_enabled=True,
        retry_policy=policy
    )
)

# 일시적 장애 시 자동으로 재시도
result = agent.run_sync("안녕")
```

## CircuitBreaker

서비스 중단 시 연쇄 장애를 방지합니다.

### 동작 방식

서킷 브레이커는 세 가지 상태를 가집니다:

```
CLOSED (정상) → OPEN (차단) → HALF_OPEN (테스트) → CLOSED
       ↓                ↓                ↓
    정상 동작      너무 많은 실패    회복 가능?
```

### 기본 서킷 브레이커

```python
from agentchord.resilience import CircuitBreaker

breaker = CircuitBreaker(
    failure_threshold=5,   # 5번 실패 후 OPEN
    success_threshold=2,   # 2번 성공 후 CLOSED
    timeout=60.0           # 60초 후 재시도
)

# 호출 시도 - 너무 많이 실패하면 서킷 OPEN
try:
    result = await breaker.execute(llm_api_call)
except CircuitBreakerOpenError:
    # 서비스 중단, 폴백 사용
    result = "서비스가 일시적으로 사용할 수 없습니다"
```

### 상태 전환

```python
breaker = CircuitBreaker(
    failure_threshold=3,   # 3번 실패 후 OPEN
    success_threshold=2,   # 2번 성공 후 CLOSED
    timeout=30.0           # 30초 후 회복 확인
)

# CLOSED 상태: 정상 동작
await breaker.execute(api_call)  # 정상 작동

# 3번 실패 후 → OPEN 상태
await breaker.execute(api_call)  # CircuitBreakerOpenError로 즉시 실패

# 30초 대기 → HALF_OPEN 상태
# 재시도 - 2번 성공 시 → CLOSED (정상 복귀)
# 1번 실패 시 → 다시 OPEN
```

### 속성

```python
print(breaker.state)          # "CLOSED", "OPEN", "HALF_OPEN"
print(breaker.failure_count)  # 리셋 이후 실패 횟수
print(breaker.success_count)  # HALF_OPEN에서 성공 횟수
```

### 에이전트에서 사용

```python
from agentchord import Agent
from agentchord.resilience import ResilienceConfig, CircuitBreaker

breaker = CircuitBreaker(
    failure_threshold=5,
    success_threshold=3,
    timeout=60.0
)

agent = Agent(
    name="circuit_breaker_agent",
    role="어시스턴트",
    model="gpt-4o-mini",
    resilience=ResilienceConfig(
        circuit_breaker_enabled=True,
        circuit_breaker=breaker
    )
)
```

## TimeoutManager

요청이 무한히 대기하는 것을 방지합니다.

### 기본 타임아웃

```python
from agentchord.resilience import TimeoutManager

manager = TimeoutManager(default_timeout=30.0)  # 30초

result = await manager.execute(llm_api_call)
```

### 모델별 타임아웃

다른 모델에 다른 타임아웃을 설정합니다:

```python
manager = TimeoutManager(
    default_timeout=60.0,
    per_model_timeouts={
        "gpt-4o": 120.0,           # GPT-4O는 2분
        "gpt-4o-mini": 30.0,       # GPT-4O mini는 30초
        "ollama/llama3.2": 300.0,  # 로컬 모델은 5분
    }
)

# 모델 기반으로 타임아웃 자동 선택
result = await manager.execute(llm_api_call, model="gpt-4o")
```

### 에이전트에서 사용

```python
from agentchord import Agent
from agentchord.resilience import ResilienceConfig, TimeoutManager

timeout_manager = TimeoutManager(
    default_timeout=60.0,
    per_model_timeouts={
        "gpt-4o": 120.0,
        "gpt-4o-mini": 30.0,
    }
)

agent = Agent(
    name="fast_agent",
    role="빠른 응답자",
    model="gpt-4o-mini",
    resilience=ResilienceConfig(
        timeout_enabled=True,
        timeout_manager=timeout_manager
    )
)
```

## ResilienceConfig

모든 복원력 기능을 하나의 설정으로 결합합니다.

### 세 가지 레이어 모두 사용

```python
from agentchord.resilience import (
    ResilienceConfig,
    RetryPolicy,
    RetryStrategy,
    CircuitBreaker,
    TimeoutManager
)

config = ResilienceConfig(
    # 재시도 설정
    retry_enabled=True,
    retry_policy=RetryPolicy(
        max_retries=3,
        strategy=RetryStrategy.EXPONENTIAL,
        base_delay=1.0,
        max_delay=30.0
    ),

    # 서킷 브레이커 설정
    circuit_breaker_enabled=True,
    circuit_breaker=CircuitBreaker(
        failure_threshold=5,
        success_threshold=2,
        timeout=60.0
    ),

    # 타임아웃 설정
    timeout_enabled=True,
    timeout_manager=TimeoutManager(
        default_timeout=60.0,
        per_model_timeouts={
            "gpt-4o": 120.0,
            "gpt-4o-mini": 30.0,
        }
    )
)

agent = Agent(
    name="super_resilient",
    role="매우 안정적인 어시스턴트",
    model="gpt-4o-mini",
    resilience=config
)
```

### 함수 직접 실행

```python
# 방법 1: 에이전트 사용 (자동)
result = agent.run_sync("안녕")

# 방법 2: 설정 직접 사용
result = await config.execute(llm_api_call, model="gpt-4o")
```

### 함수 래핑

```python
# 함수를 복원력으로 래핑
wrapped_func = config.wrap(my_async_function, model="gpt-4o")

# 래핑된 함수 사용
result = await wrapped_func(arg1, arg2)
```

### 기본 설정

합리적인 기본값으로 미리 구성됩니다:

```python
from agentchord.resilience import create_default_resilience

config = create_default_resilience()
# 제공하는 내용:
# - 3번 재시도, 지수 백오프
# - 60초 타임아웃
# - 서킷 브레이커 없음 (기본 비활성화)

agent = Agent(
    name="assistant",
    role="도우미",
    model="gpt-4o-mini",
    resilience=config
)
```

## 에러 처리

에러 종류에 따라 다르게 처리됩니다:

```python
from agentchord.errors.exceptions import (
    RateLimitError,      # 재시도됨
    TimeoutError,        # 재시도됨
    APIError,            # 재시도됨
    AuthenticationError, # 재시도 안 됨
    ModelNotFoundError   # 재시도 안 됨
)

# 이것은 재시도됨:
try:
    await agent.run_sync("안녕")
except RateLimitError:
    pass  # 자동으로 재시도됨

# 이것은 재시도 안 됨 (즉시 실패):
try:
    await agent.run_sync("안녕")
except AuthenticationError:
    pass  # 재시도 없이 즉시 실패
```

## 모니터링 및 디버깅

### 재시도 동작 확인

```python
policy = RetryPolicy(max_retries=3)

print(f"최대 재시도: {policy.max_retries}")
print(f"전략: {policy.strategy}")
print(f"기본 지연: {policy.base_delay}s")

# 지연 계산 확인
for attempt in range(3):
    delay = policy.get_delay(attempt)
    print(f"시도 {attempt}: {delay:.1f}s 지연")
```

### 서킷 브레이커 상태 확인

```python
breaker = CircuitBreaker(failure_threshold=3)

# 상태 모니터링
print(f"상태: {breaker.state}")
print(f"실패 횟수: {breaker.failure_count}")
print(f"성공 횟수: {breaker.success_count}")

if breaker.state == "OPEN":
    print("서킷이 열려 있음 - 호출이 차단됨")
```

### 로깅

AgentChord가 복원력 이벤트를 로그에 기록합니다:

```python
import logging

# 재시도/서킷 브레이커 이벤트 확인을 위해 로깅 활성화
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("agentchord.resilience")

# 재시도 시도, 서킷 브레이커 상태 변경 등이 보임
result = agent.run_sync("안녕")
```

## 베스트 프랙티스

### 1. 대부분의 경우 기본 설정 사용

```python
from agentchord.resilience import create_default_resilience

# 좋음: 합리적인 기본값
config = create_default_resilience()
agent = Agent(..., resilience=config)

# 피해야 할 과도한 설정
config = ResilienceConfig(
    retry_enabled=True,
    retry_policy=RetryPolicy(max_retries=10, strategy=RetryStrategy.FIXED),
    circuit_breaker_enabled=True,
    circuit_breaker=CircuitBreaker(failure_threshold=1),
    timeout_enabled=True,
    timeout_manager=TimeoutManager(default_timeout=5)
)
```

### 2. 모델 속도에 맞는 타임아웃

```python
manager = TimeoutManager(
    default_timeout=60.0,
    per_model_timeouts={
        "gpt-4o": 120.0,           # 느린 모델
        "gpt-4o-mini": 30.0,       # 빠른 모델
        "ollama/llama3.2": 300.0,  # 로컬, 느릴 수 있음
    }
)
```

### 3. API에는 지수 백오프 사용

```python
# 좋음: API 속도 제한에 지수 백오프
policy = RetryPolicy(
    max_retries=4,
    strategy=RetryStrategy.EXPONENTIAL,
    base_delay=1.0
)

# 나쁨: 고정 또는 선형은 속도 제한 시 API를 계속 두드림
policy = RetryPolicy(
    max_retries=4,
    strategy=RetryStrategy.FIXED,
    base_delay=1.0
)
```

### 4. 외부 서비스에는 서킷 브레이커 사용

```python
# 좋음: 서킷 브레이커로 연쇄 장애 방지
config = ResilienceConfig(
    circuit_breaker_enabled=True,
    circuit_breaker=CircuitBreaker(
        failure_threshold=5,
        timeout=60.0
    )
)
```

### 5. 디버깅을 위한 로깅

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

agent = Agent(..., resilience=create_default_resilience())

try:
    result = agent.run_sync("안녕")
except Exception as e:
    # 로그에 재시도 시도, 타임아웃 등이 기록됨
    logging.error(f"최종 실패: {e}")
```

## 완전한 예제

```python
from agentchord import Agent
from agentchord.resilience import (
    ResilienceConfig,
    RetryPolicy,
    RetryStrategy,
    CircuitBreaker,
    TimeoutManager,
)
import asyncio

async def main():
    # 복원력 설정
    config = ResilienceConfig(
        # 일시적 에러 재시도
        retry_enabled=True,
        retry_policy=RetryPolicy(
            max_retries=3,
            strategy=RetryStrategy.EXPONENTIAL,
            base_delay=1.0,
            max_delay=30.0,
            jitter=True
        ),

        # 연쇄 장애 방지
        circuit_breaker_enabled=True,
        circuit_breaker=CircuitBreaker(
            failure_threshold=5,
            success_threshold=2,
            timeout=60.0
        ),

        # 대기 중인 요청 방지
        timeout_enabled=True,
        timeout_manager=TimeoutManager(
            default_timeout=60.0,
            per_model_timeouts={
                "gpt-4o": 120.0,
                "gpt-4o-mini": 30.0,
            }
        )
    )

    # 복원력 에이전트 생성
    agent = Agent(
        name="resilient_assistant",
        role="안정적인 도우미",
        model="gpt-4o-mini",
        resilience=config
    )

    # 이 호출은 장애 시 재시도하고, 30초 후 타임아웃하며,
    # 연쇄 장애 방지를 위한 서킷 브레이커 사용
    try:
        result = agent.run_sync("복원력을 2문장으로 설명해줘")
        print(f"성공: {result.output}")
    except Exception as e:
        print(f"재시도 후 최종 실패: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 참고

- [프로바이더 가이드](providers.md) - 다양한 프로바이더와 함께 복원력 사용
- [도구 가이드](tools.md) - 도구 호출에 복원력 적용
- [Agent API](../api/core.md) - Agent API 상세 정보
