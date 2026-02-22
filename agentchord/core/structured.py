"""Structured output support for AgentChord.

Enables agents to return validated JSON output conforming to a Pydantic schema.
"""
from __future__ import annotations

import json
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class OutputSchema(Generic[T]):
    """Wraps a Pydantic model to generate JSON schema for LLM structured output.

    Example:
        >>> from pydantic import BaseModel
        >>> class Person(BaseModel):
        ...     name: str
        ...     age: int
        >>> schema = OutputSchema(Person)
        >>> schema.json_schema  # Returns JSON schema dict
        >>> schema.to_openai_response_format()  # Returns OpenAI response_format param
    """

    def __init__(self, model: type[T], description: str | None = None) -> None:
        self._model = model
        self._description = description or model.__doc__ or model.__name__

    @property
    def model_class(self) -> type[T]:
        """The Pydantic model class."""
        return self._model

    @property
    def json_schema(self) -> dict[str, Any]:
        """Generate JSON schema from the Pydantic model."""
        return self._model.model_json_schema()

    @property
    def description(self) -> str:
        """Description for the schema."""
        return self._description

    def to_openai_response_format(self) -> dict[str, Any]:
        """Generate OpenAI response_format parameter.

        Returns:
            Dict for OpenAI's response_format parameter with json_schema type.
        """
        schema = self.json_schema
        return {
            "type": "json_schema",
            "json_schema": {
                "name": self._model.__name__,
                "description": self._description,
                "schema": schema,
                "strict": True,
            },
        }

    def to_system_prompt_instruction(self) -> str:
        """Generate system prompt instruction for providers without native JSON mode.

        Returns:
            String instruction to append to system prompt.
        """
        schema_str = json.dumps(self.json_schema, indent=2)
        return (
            f"\n\nYou MUST respond with valid JSON that conforms to this schema:\n"
            f"```json\n{schema_str}\n```\n"
            f"Do not include any text outside the JSON object. "
            f"Respond ONLY with the JSON."
        )

    def validate(self, data: str | dict[str, Any]) -> T:
        """Parse and validate data against the schema.

        Args:
            data: JSON string or dict to validate.

        Returns:
            Validated Pydantic model instance.

        Raises:
            ValidationError: If data doesn't match schema.
            json.JSONDecodeError: If string is not valid JSON.
        """
        if isinstance(data, str):
            # Try to extract JSON from content that might have surrounding text
            data = self._extract_json(data)
            parsed = json.loads(data)
        else:
            parsed = data
        return self._model.model_validate(parsed)

    def validate_safe(self, data: str | dict[str, Any]) -> T | None:
        """Parse and validate without raising exceptions.

        Returns:
            Validated model instance or None if validation fails.
        """
        try:
            return self.validate(data)
        except (json.JSONDecodeError, ValidationError, ValueError):
            return None

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract JSON from text that might contain markdown code blocks or extra text."""
        text = text.strip()
        # Remove markdown code block wrappers
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        # If starts with { or [, assume it's JSON
        if text.startswith(("{", "[")):
            return text

        # Try to find JSON object in the text by attempting json.loads from each {
        start = 0
        while True:
            idx = text.find("{", start)
            if idx == -1:
                break
            try:
                # Try parsing from this position
                candidate = text[idx:]
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError as e:
                # If we got past the first char, try trimming from the end
                if e.pos and e.pos > 1:
                    # Find the last } and try that substring
                    last_brace = candidate.rfind("}")
                    if last_brace > 0:
                        trimmed = candidate[: last_brace + 1]
                        try:
                            json.loads(trimmed)
                            return trimmed
                        except json.JSONDecodeError:
                            pass
                start = idx + 1

        return text  # Return as-is, let json.loads handle the error
