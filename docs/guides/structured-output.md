# 구조화된 출력

Pydantic 스키마를 사용해 LLM에서 타입 안전한 JSON 응답을 얻습니다.

## 개요

구조화된 출력을 사용하면 Pydantic 모델로 LLM에게 원하는 정확한 형식을 정의할 수 있습니다. 자유 형식 텍스트를 파싱하는 대신 스키마에 맞는 검증된 JSON을 얻습니다.

**장점:**

- **타입 안전성**: Pydantic 검증으로 데이터 무결성 보장
- **자동 완성**: IDE가 스키마의 필드를 제안
- **네이티브 지원**: 가능한 경우 OpenAI의 엄격한 JSON 스키마 모드 사용
- **범용 폴백**: 시스템 프롬프트 주입으로 모든 프로바이더에서 작동
- **안전한 파싱**: 잘못된 응답에서 크래시 방지

## 빠른 시작

```python
from pydantic import BaseModel, Field
from agentchord import Agent
from agentchord.core.structured import OutputSchema

# 출력 스키마 정의
class SentimentAnalysis(BaseModel):
    sentiment: str = Field(..., description="positive, negative, or neutral")
    confidence: float = Field(..., ge=0.0, le=1.0)
    summary: str

# 에이전트 생성
agent = Agent(
    name="analyzer",
    role="감성 분석기",
    model="gpt-4o-mini",
)

# 스키마 사용
schema = OutputSchema(SentimentAnalysis)
result = await agent.run(
    "분석: 이 제품이 정말 좋아요!",
    output_schema=schema,
)

# 검증된 데이터 접근
if result.parsed_output:
    print(result.parsed_output["sentiment"])   # "positive"
    print(result.parsed_output["confidence"])  # 0.95
```

## 스키마 생성

### 기본 스키마

```python
from pydantic import BaseModel

class Person(BaseModel):
    name: str
    age: int
    email: str | None = None

schema = OutputSchema(Person)
```

### 필드 검증 포함

```python
from pydantic import BaseModel, Field

class ProductReview(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="별점 1-5")
    title: str = Field(..., min_length=5, max_length=100)
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)

schema = OutputSchema(ProductReview, description="제품 리뷰 형식")
```

### 중첩 구조

```python
class Address(BaseModel):
    street: str
    city: str
    country: str

class Company(BaseModel):
    name: str
    employees: int
    headquarters: Address
    branches: list[Address] = []

schema = OutputSchema(Company)
```

### Literal 타입 사용

```python
from typing import Literal

class TaskAssignment(BaseModel):
    task: str
    priority: Literal["low", "medium", "high"]
    status: Literal["pending", "in_progress", "done"]
    assignee: str

schema = OutputSchema(TaskAssignment)
```

## 에이전트에서 사용

### 기본 사용법

```python
result = await agent.run(
    "이 텍스트에서 연락처 정보 추출해줘...",
    output_schema=schema,
)

# 파싱 성공 여부 확인
if result.parsed_output:
    # 타입이 있는 데이터 사용
    contact = result.parsed_output
else:
    # 파싱 실패 처리
    print("파싱 실패:", result.output)
```

### OpenAI 프로바이더 (네이티브 지원)

OpenAI 모델의 경우 `OutputSchema`가 자동으로 OpenAI의 엄격한 JSON 스키마 모드를 사용합니다:

```python
agent = Agent(
    name="extractor",
    role="데이터 추출기",
    model="gpt-4o-mini",  # OpenAI 모델
)

schema = OutputSchema(ContactInfo)
result = await agent.run(input_text, output_schema=schema)
# OpenAI의 response_format 파라미터로 엄격한 검증 사용
```

### 다른 프로바이더 (시스템 프롬프트)

Anthropic, Ollama 등 OpenAI가 아닌 프로바이더는 스키마가 시스템 프롬프트에 주입됩니다:

```python
agent = Agent(
    name="extractor",
    role="데이터 추출기",
    model="claude-3-5-sonnet-20241022",  # Anthropic 모델
)

schema = OutputSchema(ContactInfo)
result = await agent.run(input_text, output_schema=schema)
# 스키마 지시사항이 시스템 프롬프트에 추가됨
```

## 검증

### 안전한 검증

예외 없이 검증하려면 `validate_safe()`를 사용합니다:

```python
schema = OutputSchema(Person)

# 잘못된 데이터 시 None 반환 (예외 발생 안 함)
person = schema.validate_safe('{"name": "Alice"}')  # age 누락
if person is None:
    print("검증 실패")
```

### 엄격한 검증

예외가 필요하면 `validate()`를 사용합니다:

```python
try:
    person = schema.validate('{"name": "Bob", "age": "invalid"}')
except ValidationError as e:
    print(f"검증 에러: {e}")
```

### LLM 응답 자동 처리

`OutputSchema`는 일반적인 LLM 응답 형식을 자동으로 처리합니다:

```python
# 마크다운 래퍼 처리
response = '''```json
{"name": "Alice", "age": 30}
```'''
person = schema.validate(response)  # 성공적으로 파싱

# 주변 텍스트 처리
response = '다음은 데이터입니다: {"name": "Bob", "age": 25} 요청하신 대로입니다.'
person = schema.validate(response)  # JSON 추출 성공

# 일반 JSON 처리
response = '{"name": "Charlie", "age": 35}'
person = schema.validate(response)  # 정상 작동
```

## 완전한 예제

```python
from typing import Literal
from pydantic import BaseModel, Field
from agentchord import Agent
from agentchord.core.structured import OutputSchema

# 스키마 정의
class Ingredient(BaseModel):
    name: str
    quantity: str
    unit: str

class Recipe(BaseModel):
    title: str = Field(..., description="레시피 이름")
    cuisine: str
    difficulty: Literal["easy", "medium", "hard"]
    prep_time_minutes: int = Field(..., gt=0)
    ingredients: list[Ingredient]
    steps: list[str] = Field(..., min_length=1)
    servings: int = Field(..., gt=0)

# 에이전트 생성
agent = Agent(
    name="chef",
    role="레시피 창작자",
    model="gpt-4o-mini",
)

# 구조화된 출력 사용
schema = OutputSchema(Recipe, description="레시피 형식")
result = await agent.run(
    "4인분 간단한 파스타 레시피 만들어줘",
    output_schema=schema,
)

# 검증된 데이터 활용
if result.parsed_output:
    recipe = result.parsed_output
    print(f"레시피: {recipe['title']}")
    print(f"난이도: {recipe['difficulty']}")
    print(f"재료 수: {len(recipe['ingredients'])}")
    print(f"단계 수: {len(recipe['steps'])}")

    for ingredient in recipe["ingredients"]:
        print(f"- {ingredient['quantity']} {ingredient['unit']} {ingredient['name']}")
else:
    print("레시피 파싱 실패")
    print("원본 출력:", result.output)
```

## 결과 메타데이터

구조화된 출력 결과에는 추가 메타데이터가 포함됩니다:

```python
result = await agent.run(input_text, output_schema=schema)

# 원본 LLM 응답
print(result.output)  # 원본 JSON 문자열

# 파싱 및 검증된 출력
print(result.parsed_output)  # dict 또는 None

# 어떤 스키마가 사용됐는지 확인
print(result.metadata["output_schema"])  # "Recipe"

# 다른 메타데이터 보존됨
print(result.metadata["agent_name"])
print(result.metadata["model"])
print(result.metadata["provider"])
```

## 에러 처리 패턴

### 점진적 저하

```python
result = await agent.run(input_text, output_schema=schema)

if result.parsed_output:
    # 구조화된 데이터 사용
    process_validated_data(result.parsed_output)
else:
    # 텍스트 처리로 폴백
    process_text_output(result.output)
```

### 실패 시 재시도

```python
max_attempts = 3
for attempt in range(max_attempts):
    result = await agent.run(input_text, output_schema=schema)
    if result.parsed_output:
        break
    if attempt < max_attempts - 1:
        print(f"시도 {attempt + 1} 실패, 재시도 중...")
```

### 부분 검증

```python
# 선택적 검증을 위한 Pydantic partial 모델 사용
from pydantic import BaseModel

class PartialPerson(BaseModel):
    name: str | None = None
    age: int | None = None

schema = OutputSchema(PartialPerson)
result = await agent.run(input_text, output_schema=schema)
# 필드가 누락되어도 성공
```

## 베스트 프랙티스

### 1. 명확한 필드 설명 작성

LLM이 올바른 값을 생성할 수 있도록 설명을 추가합니다:

```python
class Task(BaseModel):
    title: str = Field(..., description="간단한 작업 설명")
    priority: int = Field(..., ge=1, le=5, description="우선순위 레벨 1-5")
```

### 2. Literal 타입으로 열거형 값 제한

```python
status: Literal["pending", "active", "done"]
```

### 3. Pydantic 검증자 사용

```python
from pydantic import field_validator

class Product(BaseModel):
    price: float

    @field_validator('price')
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('가격은 양수여야 합니다')
        return v
```

### 4. 항상 `parsed_output` 확인 후 사용

```python
if result.parsed_output:
    # 안전하게 사용 가능
    data = result.parsed_output
```

### 5. 스키마를 단순하게 유지

복잡한 중첩 구조는 LLM을 혼란스럽게 할 수 있습니다:
- 가능하면 평면적인 구조 선호
- 중첩 깊이 2-3 수준으로 제한
- 명확하고 단순한 필드 이름 사용

### 6. 프로바이더별 동작 테스트

```python
# OpenAI로 테스트
agent_openai = Agent(model="gpt-4o-mini", ...)

# Anthropic으로 테스트
agent_anthropic = Agent(model="claude-3-5-sonnet-20241022", ...)
```

## 고급 사용법

### 커스텀 검증

```python
from pydantic import BaseModel, field_validator

class Email(BaseModel):
    address: str

    @field_validator('address')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('유효하지 않은 이메일')
        return v.lower()

schema = OutputSchema(Email)
```

### 스키마 상속

```python
class BaseMetadata(BaseModel):
    created_at: str
    version: int

class Article(BaseMetadata):
    title: str
    content: str
    tags: list[str]

schema = OutputSchema(Article)
```

### 동적 스키마 생성

```python
def create_schema(fields: list[str]) -> OutputSchema:
    # Pydantic 모델을 동적으로 생성
    model = type('DynamicModel', (BaseModel,), {
        field: (str, ...) for field in fields
    })
    return OutputSchema(model)

schema = create_schema(["name", "email", "phone"])
```

## API 참고

### OutputSchema

```python
class OutputSchema(Generic[T]):
    def __init__(self, model: type[BaseModel], description: str | None = None)

    @property
    def model_class(self) -> type[T]

    @property
    def json_schema(self) -> dict[str, Any]

    @property
    def description(self) -> str

    def to_openai_response_format(self) -> dict[str, Any]

    def to_system_prompt_instruction(self) -> str

    def validate(self, data: str | dict) -> T

    def validate_safe(self, data: str | dict) -> T | None
```

### Agent.run()에서 output_schema 사용

```python
async def run(
    self,
    input: str,
    *,
    max_tool_rounds: int = 10,
    output_schema: OutputSchema | None = None,
    **kwargs: Any
) -> AgentResult
```

### parsed_output이 있는 AgentResult

```python
class AgentResult(BaseModel):
    output: str                          # 원본 LLM 응답
    parsed_output: dict[str, Any] | None # 검증된 출력
    messages: list[Message]
    usage: Usage
    cost: float
    duration_ms: int
    metadata: dict[str, Any]             # "output_schema" 키 포함
```

## 참고

- [핵심 개념](core-concepts.md) - 에이전트와 결과 이해
- [프로바이더](providers.md) - LLM 프로바이더 설정
- [도구](tools.md) - 구조화된 출력과 도구 결합
- [예제](../examples.md) - 더 많은 사용 예제
