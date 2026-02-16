# Structured Output

Get validated, type-safe JSON responses from LLMs using Pydantic schemas.

## Overview

Structured output allows you to define the exact format you want from an LLM using Pydantic models. Instead of parsing free-form text, you get validated JSON that matches your schema.

**Benefits:**

- **Type Safety**: Pydantic validation ensures data integrity
- **Auto-completion**: IDEs suggest fields from your schema
- **Native Support**: Uses OpenAI's strict JSON schema mode when available
- **Graceful Fallback**: Works with all providers via system prompt injection
- **Error Handling**: Safe parsing prevents crashes on malformed responses

## Quick Start

```python
from pydantic import BaseModel, Field
from agentweave import Agent
from agentweave.core.structured import OutputSchema

# Define your output schema
class SentimentAnalysis(BaseModel):
    sentiment: str = Field(..., description="positive, negative, or neutral")
    confidence: float = Field(..., ge=0.0, le=1.0)
    summary: str

# Create agent
agent = Agent(
    name="analyzer",
    role="Sentiment analyzer",
    model="gpt-4o-mini",
)

# Use the schema
schema = OutputSchema(SentimentAnalysis)
result = await agent.run(
    "Analyze: I love this product!",
    output_schema=schema,
)

# Access validated data
if result.parsed_output:
    print(result.parsed_output["sentiment"])  # "positive"
    print(result.parsed_output["confidence"])  # 0.95
```

## Creating Schemas

### Basic Schema

```python
from pydantic import BaseModel

class Person(BaseModel):
    name: str
    age: int
    email: str | None = None

schema = OutputSchema(Person)
```

### With Field Validation

```python
from pydantic import BaseModel, Field

class ProductReview(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Star rating 1-5")
    title: str = Field(..., min_length=5, max_length=100)
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)

schema = OutputSchema(ProductReview, description="Product review format")
```

### Nested Structures

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

### Using Literal Types

```python
from typing import Literal

class TaskAssignment(BaseModel):
    task: str
    priority: Literal["low", "medium", "high"]
    status: Literal["pending", "in_progress", "done"]
    assignee: str

schema = OutputSchema(TaskAssignment)
```

## Using with Agents

### Basic Usage

```python
result = await agent.run(
    "Extract contact info from this text...",
    output_schema=schema,
)

# Check if parsing succeeded
if result.parsed_output:
    # Use the typed data
    contact = result.parsed_output
else:
    # Handle parsing failure
    print("Failed to parse:", result.output)
```

### OpenAI Provider (Native Support)

For OpenAI models, `OutputSchema` automatically uses OpenAI's strict JSON schema mode:

```python
agent = Agent(
    name="extractor",
    role="Data extractor",
    model="gpt-4o-mini",  # OpenAI model
)

schema = OutputSchema(ContactInfo)
result = await agent.run(input_text, output_schema=schema)
# Uses OpenAI's response_format parameter with strict validation
```

### Other Providers (System Prompt)

For non-OpenAI providers (Anthropic, Ollama, etc.), the schema is injected into the system prompt:

```python
agent = Agent(
    name="extractor",
    role="Data extractor",
    model="claude-3-5-sonnet-20241022",  # Anthropic model
)

schema = OutputSchema(ContactInfo)
result = await agent.run(input_text, output_schema=schema)
# Schema instructions added to system prompt
```

## Validation

### Safe Validation

Use `validate_safe()` to avoid exceptions:

```python
schema = OutputSchema(Person)

# Returns None instead of raising on invalid data
person = schema.validate_safe('{"name": "Alice"}')  # Missing age
if person is None:
    print("Validation failed")
```

### Strict Validation

Use `validate()` for exceptions:

```python
try:
    person = schema.validate('{"name": "Bob", "age": "invalid"}')
except ValidationError as e:
    print(f"Validation error: {e}")
```

### Handling LLM Responses

`OutputSchema` handles common LLM response formats automatically:

```python
# Works with markdown wrappers
response = '''```json
{"name": "Alice", "age": 30}
```'''
person = schema.validate(response)  # ✓ Parses successfully

# Works with surrounding text
response = 'Here is the data: {"name": "Bob", "age": 25} as requested.'
person = schema.validate(response)  # ✓ Extracts JSON

# Works with plain JSON
response = '{"name": "Charlie", "age": 35}'
person = schema.validate(response)  # ✓ Works
```

## Complete Example

```python
from typing import Literal
from pydantic import BaseModel, Field
from agentweave import Agent
from agentweave.core.structured import OutputSchema

# Define schemas
class Ingredient(BaseModel):
    name: str
    quantity: str
    unit: str

class Recipe(BaseModel):
    title: str = Field(..., description="Recipe name")
    cuisine: str
    difficulty: Literal["easy", "medium", "hard"]
    prep_time_minutes: int = Field(..., gt=0)
    ingredients: list[Ingredient]
    steps: list[str] = Field(..., min_length=1)
    servings: int = Field(..., gt=0)

# Create agent
agent = Agent(
    name="chef",
    role="Recipe creator",
    model="gpt-4o-mini",
)

# Use structured output
schema = OutputSchema(Recipe, description="Recipe format")
result = await agent.run(
    "Create a simple pasta recipe for 4 people",
    output_schema=schema,
)

# Work with validated data
if result.parsed_output:
    recipe = result.parsed_output
    print(f"Recipe: {recipe['title']}")
    print(f"Difficulty: {recipe['difficulty']}")
    print(f"Ingredients: {len(recipe['ingredients'])}")
    print(f"Steps: {len(recipe['steps'])}")

    # Type-safe access
    for ingredient in recipe["ingredients"]:
        print(f"- {ingredient['quantity']} {ingredient['unit']} {ingredient['name']}")
else:
    print("Failed to parse recipe")
    print("Raw output:", result.output)
```

## Result Metadata

Structured output results include additional metadata:

```python
result = await agent.run(input_text, output_schema=schema)

# Raw LLM response
print(result.output)  # Original JSON string

# Parsed and validated output
print(result.parsed_output)  # Dict or None

# Check which schema was used
print(result.metadata["output_schema"])  # "Recipe"

# Other metadata is preserved
print(result.metadata["agent_name"])
print(result.metadata["model"])
print(result.metadata["provider"])
```

## Error Handling Patterns

### Graceful Degradation

```python
result = await agent.run(input_text, output_schema=schema)

if result.parsed_output:
    # Use structured data
    process_validated_data(result.parsed_output)
else:
    # Fallback to text processing
    process_text_output(result.output)
```

### Retry on Failure

```python
max_attempts = 3
for attempt in range(max_attempts):
    result = await agent.run(input_text, output_schema=schema)
    if result.parsed_output:
        break
    if attempt < max_attempts - 1:
        print(f"Attempt {attempt + 1} failed, retrying...")
```

### Partial Validation

```python
# Use Pydantic's partial models for optional validation
from pydantic import BaseModel

class PartialPerson(BaseModel):
    name: str | None = None
    age: int | None = None

schema = OutputSchema(PartialPerson)
result = await agent.run(input_text, output_schema=schema)
# Will succeed even with missing fields
```

## Best Practices

1. **Clear Descriptions**: Add field descriptions to guide the LLM
   ```python
   class Task(BaseModel):
       title: str = Field(..., description="Brief task description")
       priority: int = Field(..., ge=1, le=5, description="Priority level 1-5")
   ```

2. **Use Literal Types**: For enumerated values, use `Literal`
   ```python
   status: Literal["pending", "active", "done"]
   ```

3. **Validate Constraints**: Use Pydantic's validators
   ```python
   from pydantic import field_validator

   class Product(BaseModel):
       price: float

       @field_validator('price')
       def price_must_be_positive(cls, v):
           if v <= 0:
               raise ValueError('price must be positive')
           return v
   ```

4. **Handle None Gracefully**: Always check `parsed_output` before use
   ```python
   if result.parsed_output:
       # Safe to use
       data = result.parsed_output
   ```

5. **Keep Schemas Simple**: Complex nested structures can confuse LLMs
   - Prefer flat structures when possible
   - Limit nesting depth to 2-3 levels
   - Use clear, simple field names

6. **Test with Different Providers**: Behavior may vary across providers
   ```python
   # Test with OpenAI
   agent_openai = Agent(model="gpt-4o-mini", ...)

   # Test with Anthropic
   agent_anthropic = Agent(model="claude-3-5-sonnet-20241022", ...)
   ```

## Advanced Usage

### Custom Validation

```python
from pydantic import BaseModel, field_validator

class Email(BaseModel):
    address: str

    @field_validator('address')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('invalid email')
        return v.lower()

schema = OutputSchema(Email)
```

### Schema Composition

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

### Dynamic Schemas

```python
def create_schema(fields: list[str]) -> OutputSchema:
    # Dynamically create a Pydantic model
    model = type('DynamicModel', (BaseModel,), {
        field: (str, ...) for field in fields
    })
    return OutputSchema(model)

schema = create_schema(["name", "email", "phone"])
```

## API Reference

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

### Agent.run() with output_schema

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

### AgentResult with parsed_output

```python
class AgentResult(BaseModel):
    output: str  # Raw LLM response
    parsed_output: dict[str, Any] | None  # Validated output
    messages: list[Message]
    usage: Usage
    cost: float
    duration_ms: int
    metadata: dict[str, Any]  # Includes "output_schema" key
```

## See Also

- [Core Concepts](core-concepts.md) - Understanding agents and results
- [Providers](providers.md) - LLM provider configuration
- [Tools](tools.md) - Combining structured output with tools
- [Examples](../examples.md) - More usage examples
