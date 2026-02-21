# 복원력 API 레퍼런스

장애 허용과 신뢰성을 위한 복원력 패턴에 대한 완전한 API 레퍼런스입니다.

---

## RetryStrategy

재시도 딜레이 계산 전략을 나타내는 열거형입니다.

```python
from agentchord.resilience.retry import RetryStrategy

RetryStrategy.FIXED        # 고정 딜레이
RetryStrategy.EXPONENTIAL  # 지수 백오프 (기본값)
RetryStrategy.LINEAR       # 선형 증가
```

**값:**

| 값 | 문자열 | 딜레이 계산 방식 |
|----|--------|----------------|
| `FIXED` | `"fixed"` | 매 재시도마다 `base_delay` 고정 |
| `EXPONENTIAL` | `"exponential"` | `base_delay * 2^attempt` |
| `LINEAR` | `"linear"` | `base_delay * (attempt + 1)` |

---

## RetryPolicy

재시도 정책을 구성하고 실행하는 클래스입니다. 고정, 지수, 선형 백오프 전략과 지터(jitter)를 지원합니다.

```python
from agentchord.resilience.retry import RetryPolicy, RetryStrategy

# 지수 백오프 (기본값)
policy = RetryPolicy(
    max_retries=3,
    strategy=RetryStrategy.EXPONENTIAL,
    base_delay=1.0,
    max_delay=60.0,
    jitter=True,
)

# 고정 딜레이
policy = RetryPolicy(max_retries=5, strategy=RetryStrategy.FIXED, base_delay=2.0)

# 특정 예외만 재시도
from agentchord.errors import RateLimitError
policy = RetryPolicy(
    max_retries=3,
    retryable_errors=(RateLimitError,),
)

# 함수 실행
result = await policy.execute(some_async_func, arg1, arg2, kwarg=value)
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `max_retries` | `int` | `3` | 최대 재시도 횟수 (0이면 재시도 없음) |
| `strategy` | `RetryStrategy` | `EXPONENTIAL` | 딜레이 계산 전략 |
| `base_delay` | `float` | `1.0` | 기본 딜레이 (초). 양수여야 함 |
| `max_delay` | `float` | `60.0` | 최대 딜레이 상한선 (초) |
| `jitter` | `bool` | `True` | 딜레이에 랜덤 지터 추가 여부 (thundering herd 방지) |
| `jitter_factor` | `float` | `0.1` | 지터 크기 (딜레이의 비율, 0.0~1.0) |
| `retryable_errors` | `tuple[type[Exception], ...] \| None` | `None` | 재시도할 예외 타입. None이면 기본값 사용 |

**기본 재시도 예외 (`DEFAULT_RETRYABLE`):**

- `RateLimitError`
- `TimeoutError`
- `APIError`
- `ConnectionError`
- `asyncio.TimeoutError`

**메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `execute` | `async execute(func: Callable, *args, **kwargs) -> T` | `T` | 재시도 로직을 적용하여 함수 실행 |
| `get_delay` | `get_delay(attempt: int) -> float` | `float` | 시도 번호에 따른 딜레이 계산 (초). 지터 포함 |
| `should_retry` | `should_retry(error: Exception, attempt: int) -> bool` | `bool` | 현재 에러와 시도 횟수로 재시도 여부 결정 |

**프로퍼티:**

| 프로퍼티 | 타입 | 설명 |
|----------|------|------|
| `max_retries` | `int` | 최대 재시도 횟수 |
| `strategy` | `RetryStrategy` | 재시도 전략 |

**딜레이 계산 예시 (base_delay=1.0, max_delay=60.0):**

| 전략 | 1차 재시도 | 2차 재시도 | 3차 재시도 |
|------|-----------|-----------|-----------|
| FIXED | 1.0s | 1.0s | 1.0s |
| EXPONENTIAL | 1.0s | 2.0s | 4.0s |
| LINEAR | 1.0s | 2.0s | 3.0s |

---

## CircuitState

서킷 브레이커의 현재 상태를 나타내는 열거형입니다.

```python
from agentchord.resilience.circuit_breaker import CircuitState

CircuitState.CLOSED    # 정상 동작 - 요청 허용
CircuitState.OPEN      # 장애 모드 - 요청 즉시 거부
CircuitState.HALF_OPEN # 복구 테스트 - 제한적 요청 허용
```

---

## CircuitBreaker

연쇄 장애를 방지하는 서킷 브레이커 패턴 구현입니다.

```python
from agentchord.resilience.circuit_breaker import CircuitBreaker, CircuitOpenError

breaker = CircuitBreaker(
    failure_threshold=5,   # 5번 실패하면 서킷 열기
    success_threshold=2,   # 2번 성공하면 서킷 닫기
    timeout=30.0,          # 30초 후 HALF_OPEN으로 전환
)

# 실행
try:
    result = await breaker.execute(some_api_call, arg1, arg2)
except CircuitOpenError as e:
    print(f"서킷 열림. {e.retry_after:.1f}초 후 재시도")
    result = fallback_value  # 폴백 처리

# 상태 확인
print(breaker.state)          # CircuitState.CLOSED
print(breaker.failure_count)  # 현재 실패 횟수
print(breaker.is_closed)      # True이면 요청 허용 상태

# 수동 재설정
breaker.reset()
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `failure_threshold` | `int` | `5` | 서킷을 열기 위한 연속 실패 횟수. 1 이상이어야 함 |
| `success_threshold` | `int` | `2` | HALF_OPEN에서 서킷을 닫기 위한 연속 성공 횟수. 1 이상이어야 함 |
| `timeout` | `float` | `30.0` | OPEN에서 HALF_OPEN으로 전환할 대기 시간 (초). 양수여야 함 |
| `excluded_exceptions` | `tuple[type[Exception], ...]` | `()` | 실패로 카운트하지 않을 예외 타입 목록 |

**메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `execute` | `async execute(func: Callable, *args, **kwargs) -> T` | `T` | 서킷 브레이커 보호 하에 함수 실행. 서킷이 열려있으면 `CircuitOpenError` |
| `record_success` | `record_success() -> None` | `None` | 성공 기록. HALF_OPEN 상태에서 임계값 도달 시 서킷 닫음 |
| `record_failure` | `record_failure(error: Exception) -> None` | `None` | 실패 기록. 임계값 도달 시 서킷 열음 |
| `reset` | `reset() -> None` | `None` | 서킷을 CLOSED 상태로 수동 초기화 |

**프로퍼티:**

| 프로퍼티 | 타입 | 설명 |
|----------|------|------|
| `state` | `CircuitState` | 현재 서킷 상태 |
| `failure_count` | `int` | 현재 실패 횟수 |
| `is_closed` | `bool` | CLOSED 또는 HALF_OPEN인 경우 True (요청 허용 상태) |

**상태 전환 다이어그램:**

```
CLOSED ---(실패 횟수 >= threshold)---> OPEN
OPEN   ---(timeout 경과)-----------> HALF_OPEN
HALF_OPEN ---(성공 횟수 >= threshold)--> CLOSED
HALF_OPEN ---(실패 발생)-------------> OPEN
```

---

## CircuitOpenError

서킷이 열려 있을 때 요청이 거부된 경우 발생하는 예외입니다.

```python
from agentchord.resilience.circuit_breaker import CircuitOpenError

try:
    result = await breaker.execute(api_call)
except CircuitOpenError as e:
    print(str(e))           # "Circuit breaker is open. Retry after 25.3s"
    print(e.retry_after)    # 재시도까지 남은 시간 (초)
```

**필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `retry_after` | `float \| None` | 재시도까지 남은 예상 시간 (초) |

---

## TimeoutManager

LLM 호출을 위한 계층적 타임아웃 관리 클래스입니다. 모델별 타임아웃 설정을 지원합니다.

```python
from agentchord.resilience.timeout import TimeoutManager

manager = TimeoutManager(
    default_timeout=60.0,
    per_model_timeouts={
        "gpt-4": 120.0,
        "claude-3-opus": 180.0,
    },
    use_builtin_defaults=True,
)

# 타임아웃 조회
timeout = manager.get_timeout("gpt-4o")         # 120.0 (gpt-4 prefix match)
timeout = manager.get_timeout("claude-3-opus")  # 180.0
timeout = manager.get_timeout("unknown-model")  # 60.0 (기본값)
timeout = manager.get_timeout()                  # 60.0 (모델 미지정)

# 타임아웃 설정
manager.set_timeout("my-model", 90.0)

# 타임아웃 적용하여 실행
result = await manager.execute(
    api_call,
    arg1, arg2,
    model="gpt-4",        # 해당 모델의 타임아웃 적용
    kwarg=value,
)
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `default_timeout` | `float` | `60.0` | 기본 타임아웃 (초). 양수여야 함 |
| `per_model_timeouts` | `dict[str, float] \| None` | `None` | 모델별 타임아웃 오버라이드 딕셔너리 |
| `use_builtin_defaults` | `bool` | `True` | 내장 모델 기본 타임아웃 사용 여부 |

**내장 모델 기본 타임아웃:**

| 모델 | 타임아웃 |
|------|---------|
| `gpt-4` | 120초 |
| `gpt-4-turbo` | 90초 |
| `claude-3-opus` | 180초 |
| `claude-3-opus-20240229` | 180초 |

**메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `get_timeout` | `get_timeout(model: str \| None = None) -> float` | `float` | 모델에 적용할 타임아웃 반환. 정확 일치 후 프리픽스 일치 시도 |
| `set_timeout` | `set_timeout(model: str, timeout: float) -> None` | `None` | 특정 모델의 타임아웃 설정 |
| `execute` | `async execute(func, *args, timeout: float \| None = None, model: str \| None = None, **kwargs) -> T` | `T` | 타임아웃을 적용하여 함수 실행. 타임아웃 시 `TimeoutError` |

**프로퍼티:**

| 프로퍼티 | 타입 | 설명 |
|----------|------|------|
| `default_timeout` | `float` | 기본 타임아웃 (초) |

---

## ResilienceConfig

재시도, 서킷 브레이커, 타임아웃을 하나로 통합하는 설정 클래스입니다.

```python
from agentchord.resilience.config import ResilienceConfig, create_default_resilience
from agentchord.resilience.retry import RetryPolicy, RetryStrategy
from agentchord.resilience.circuit_breaker import CircuitBreaker
from agentchord.resilience.timeout import TimeoutManager

# 완전한 복원력 설정
config = ResilienceConfig(
    retry_enabled=True,
    retry_policy=RetryPolicy(
        max_retries=3,
        strategy=RetryStrategy.EXPONENTIAL,
        base_delay=1.0,
    ),
    circuit_breaker_enabled=True,
    circuit_breaker=CircuitBreaker(failure_threshold=5, timeout=30),
    timeout_enabled=True,
    timeout_manager=TimeoutManager(default_timeout=60.0),
)

# 기본 설정 사용 (재시도 3회 + 60초 타임아웃)
config = create_default_resilience()

# 에이전트에 적용
from agentchord import Agent
agent = Agent(name="resilient", role="...", resilience=config)

# 직접 실행 (실행 순서: 타임아웃 > 서킷 브레이커 > 재시도 > 함수)
result = await config.execute(api_call, arg1, model="gpt-4")

# 함수 래핑
wrapped_fn = config.wrap(api_call, model="gpt-4")
result = await wrapped_fn(arg1, arg2)
```

**필드:**

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `retry_enabled` | `bool` | `True` | 재시도 활성화 여부 |
| `retry_policy` | `RetryPolicy \| None` | `None` | 재시도 정책. None이면 기본 `RetryPolicy()` 사용 |
| `circuit_breaker_enabled` | `bool` | `False` | 서킷 브레이커 활성화 여부 |
| `circuit_breaker` | `CircuitBreaker \| None` | `None` | 서킷 브레이커. None이면 기본 `CircuitBreaker()` 사용 |
| `timeout_enabled` | `bool` | `True` | 타임아웃 활성화 여부 |
| `timeout_manager` | `TimeoutManager \| None` | `None` | 타임아웃 매니저. None이면 기본 `TimeoutManager()` 사용 |

**메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `execute` | `async execute(func, *args, model: str \| None = None, **kwargs) -> T` | `T` | 모든 복원력 레이어를 적용하여 실행 |
| `wrap` | `wrap(func, model: str \| None = None) -> Callable` | `Callable` | 복원력 레이어가 적용된 래퍼 함수 반환 |
| `get_retry_policy` | `get_retry_policy() -> RetryPolicy \| None` | `RetryPolicy \| None` | 활성화된 재시도 정책 반환 |
| `get_circuit_breaker` | `get_circuit_breaker() -> CircuitBreaker \| None` | `CircuitBreaker \| None` | 활성화된 서킷 브레이커 반환 |
| `get_timeout_manager` | `get_timeout_manager() -> TimeoutManager \| None` | `TimeoutManager \| None` | 활성화된 타임아웃 매니저 반환 |

**실행 레이어 순서 (바깥에서 안으로):**

```
타임아웃 (outermost)
  └── 서킷 브레이커
        └── 재시도
              └── 실제 함수 호출
```

---

## create_default_resilience

기본 복원력 설정을 빠르게 생성하는 편의 함수입니다.

```python
from agentchord.resilience.config import create_default_resilience

config = create_default_resilience()
# 결과:
# ResilienceConfig(
#     retry_enabled=True,
#     retry_policy=RetryPolicy(max_retries=3),  # 지수 백오프
#     timeout_enabled=True,
#     timeout_manager=TimeoutManager(default_timeout=60.0),
#     circuit_breaker_enabled=False,  # 비활성화
# )
```

**반환값:** `ResilienceConfig` - 재시도 3회(지수 백오프) + 60초 타임아웃이 설정된 기본 복원력 설정
