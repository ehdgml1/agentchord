"""Unit tests for structured output support."""
from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import BaseModel, Field, ValidationError

from agentweave.core.structured import OutputSchema


class Person(BaseModel):
    """A simple person model."""

    name: str = Field(..., description="Person's full name")
    age: int = Field(..., ge=0, le=150, description="Person's age")
    email: str | None = Field(None, description="Email address")


class NestedData(BaseModel):
    """Model with nested structures."""

    title: str
    items: list[str]
    metadata: dict[str, Any]


class TestOutputSchema:
    """Test OutputSchema class."""

    def test_init_basic(self) -> None:
        """Test basic initialization."""
        schema = OutputSchema(Person)
        assert schema.model_class == Person
        assert schema.description == "A simple person model."

    def test_init_custom_description(self) -> None:
        """Test initialization with custom description."""
        schema = OutputSchema(Person, description="Custom description")
        assert schema.description == "Custom description"

    def test_json_schema_generation(self) -> None:
        """Test JSON schema generation."""
        schema = OutputSchema(Person)
        json_schema = schema.json_schema

        assert "properties" in json_schema
        assert "name" in json_schema["properties"]
        assert "age" in json_schema["properties"]
        assert json_schema["required"] == ["name", "age"]

    def test_to_openai_response_format(self) -> None:
        """Test OpenAI response_format generation."""
        schema = OutputSchema(Person, description="Person data")
        response_format = schema.to_openai_response_format()

        assert response_format["type"] == "json_schema"
        assert response_format["json_schema"]["name"] == "Person"
        assert response_format["json_schema"]["description"] == "Person data"
        assert response_format["json_schema"]["strict"] is True
        assert "schema" in response_format["json_schema"]

    def test_to_system_prompt_instruction(self) -> None:
        """Test system prompt instruction generation."""
        schema = OutputSchema(Person)
        instruction = schema.to_system_prompt_instruction()

        assert "You MUST respond with valid JSON" in instruction
        assert "schema" in instruction.lower()
        assert "Person" in instruction or "properties" in instruction
        assert "Respond ONLY with the JSON" in instruction

    def test_validate_dict(self) -> None:
        """Test validation with dict input."""
        schema = OutputSchema(Person)
        data = {"name": "Alice", "age": 30, "email": "alice@example.com"}

        result = schema.validate(data)
        assert isinstance(result, Person)
        assert result.name == "Alice"
        assert result.age == 30
        assert result.email == "alice@example.com"

    def test_validate_json_string(self) -> None:
        """Test validation with JSON string input."""
        schema = OutputSchema(Person)
        data = '{"name": "Bob", "age": 25}'

        result = schema.validate(data)
        assert isinstance(result, Person)
        assert result.name == "Bob"
        assert result.age == 25

    def test_validate_with_markdown_wrapper(self) -> None:
        """Test validation with markdown code block wrapper."""
        schema = OutputSchema(Person)
        data = '```json\n{"name": "Charlie", "age": 35}\n```'

        result = schema.validate(data)
        assert result.name == "Charlie"
        assert result.age == 35

    def test_validate_with_surrounding_text(self) -> None:
        """Test validation with surrounding text."""
        schema = OutputSchema(Person)
        data = 'Here is the data: {"name": "David", "age": 40} and that is it.'

        result = schema.validate(data)
        assert result.name == "David"
        assert result.age == 40

    def test_validate_safe_success(self) -> None:
        """Test validate_safe with valid data."""
        schema = OutputSchema(Person)
        data = {"name": "Eve", "age": 28}

        result = schema.validate_safe(data)
        assert result is not None
        assert result.name == "Eve"

    def test_validate_safe_failure(self) -> None:
        """Test validate_safe with invalid data."""
        schema = OutputSchema(Person)
        data = {"name": "Frank"}  # Missing required 'age'

        result = schema.validate_safe(data)
        assert result is None

    def test_validate_safe_malformed_json(self) -> None:
        """Test validate_safe with malformed JSON."""
        schema = OutputSchema(Person)
        data = '{"name": "Grace", "age": '  # Incomplete JSON

        result = schema.validate_safe(data)
        assert result is None

    def test_validate_fails_on_missing_required(self) -> None:
        """Test that validation fails on missing required fields."""
        schema = OutputSchema(Person)
        data = {"name": "Helen"}  # Missing 'age'

        with pytest.raises(ValidationError):
            schema.validate(data)

    def test_validate_fails_on_invalid_type(self) -> None:
        """Test that validation fails on invalid type."""
        schema = OutputSchema(Person)
        data = {"name": "Ian", "age": "thirty"}  # Age should be int

        with pytest.raises(ValidationError):
            schema.validate(data)

    def test_validate_nested_structure(self) -> None:
        """Test validation with nested structures."""
        schema = OutputSchema(NestedData)
        data = {
            "title": "Test",
            "items": ["a", "b", "c"],
            "metadata": {"key": "value", "count": 3},
        }

        result = schema.validate(data)
        assert result.title == "Test"
        assert result.items == ["a", "b", "c"]
        assert result.metadata["key"] == "value"

    def test_extract_json_plain(self) -> None:
        """Test _extract_json with plain JSON."""
        text = '{"name": "John", "age": 30}'
        result = OutputSchema._extract_json(text)
        assert result == text

    def test_extract_json_with_json_markdown(self) -> None:
        """Test _extract_json with ```json wrapper."""
        text = '```json\n{"name": "Jane", "age": 25}\n```'
        result = OutputSchema._extract_json(text)
        assert "```" not in result
        assert result.strip() == '{"name": "Jane", "age": 25}'

    def test_extract_json_with_generic_markdown(self) -> None:
        """Test _extract_json with ``` wrapper."""
        text = '```\n{"name": "Jim", "age": 35}\n```'
        result = OutputSchema._extract_json(text)
        assert "```" not in result
        assert result.strip() == '{"name": "Jim", "age": 35}'

    def test_extract_json_from_text(self) -> None:
        """Test _extract_json finding JSON in text."""
        text = 'The result is: {"name": "Jake", "age": 40} as shown above.'
        result = OutputSchema._extract_json(text)
        assert result == '{"name": "Jake", "age": 40}'

    def test_extract_json_nested_braces(self) -> None:
        """Test _extract_json with nested braces."""
        text = 'Extra text {"outer": {"inner": "value"}, "age": 30} more text'
        result = OutputSchema._extract_json(text)
        json_obj = json.loads(result)
        assert json_obj["outer"]["inner"] == "value"
        assert json_obj["age"] == 30

    def test_extract_json_no_json_found(self) -> None:
        """Test _extract_json when no JSON is found."""
        text = 'This is plain text with no JSON'
        result = OutputSchema._extract_json(text)
        assert result == text  # Returns as-is


class TestOutputSchemaIntegration:
    """Integration tests for OutputSchema with various scenarios."""

    def test_full_workflow_dict_to_model(self) -> None:
        """Test complete workflow from dict to validated model."""
        schema = OutputSchema(Person, description="Person information")

        # Simulate LLM response as dict
        llm_response = {"name": "Alice", "age": 30, "email": "alice@test.com"}

        # Validate
        person = schema.validate(llm_response)

        # Verify
        assert person.name == "Alice"
        assert person.age == 30
        assert person.email == "alice@test.com"

    def test_full_workflow_json_string_to_model(self) -> None:
        """Test complete workflow from JSON string to validated model."""
        schema = OutputSchema(Person)

        # Simulate LLM response as JSON string
        llm_response = '{"name": "Bob", "age": 25, "email": null}'

        # Validate
        person = schema.validate(llm_response)

        # Verify
        assert person.name == "Bob"
        assert person.age == 25
        assert person.email is None

    def test_full_workflow_with_markdown_llm_response(self) -> None:
        """Test with markdown-wrapped LLM response (common with some models)."""
        schema = OutputSchema(Person)

        # Simulate LLM response with markdown wrapper
        llm_response = '''```json
{
    "name": "Charlie",
    "age": 35,
    "email": "charlie@test.com"
}
```'''

        # Validate
        person = schema.validate(llm_response)

        # Verify
        assert person.name == "Charlie"
        assert person.age == 35

    def test_openai_format_structure(self) -> None:
        """Test that OpenAI format has correct structure."""
        schema = OutputSchema(Person, description="Test person")
        format_dict = schema.to_openai_response_format()

        # Verify structure matches OpenAI's expected format
        assert format_dict["type"] == "json_schema"
        assert "json_schema" in format_dict

        json_schema_obj = format_dict["json_schema"]
        assert json_schema_obj["name"] == "Person"
        assert json_schema_obj["strict"] is True
        assert "schema" in json_schema_obj
        assert isinstance(json_schema_obj["schema"], dict)

    def test_multiple_schemas(self) -> None:
        """Test using multiple different schemas."""
        person_schema = OutputSchema(Person)
        nested_schema = OutputSchema(NestedData)

        # Different schemas should have different properties
        person_json = person_schema.json_schema
        nested_json = nested_schema.json_schema

        assert "name" in person_json["properties"]
        assert "title" in nested_json["properties"]
        assert "items" in nested_json["properties"]

    def test_schema_reuse(self) -> None:
        """Test that a schema can be reused for multiple validations."""
        schema = OutputSchema(Person)

        data1 = {"name": "Person1", "age": 20}
        data2 = {"name": "Person2", "age": 30}
        data3 = '{"name": "Person3", "age": 40}'

        person1 = schema.validate(data1)
        person2 = schema.validate(data2)
        person3 = schema.validate(data3)

        assert person1.name == "Person1"
        assert person2.name == "Person2"
        assert person3.name == "Person3"
