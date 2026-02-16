"""Core type definitions for AgentWeave.

This module defines the fundamental data structures used throughout the framework.
All types use Pydantic for validation and serialization.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Role of a message in a conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolCall(BaseModel):
    """A tool call made by the assistant."""

    id: str = Field(..., description="Unique identifier for this tool call")
    name: str = Field(..., description="Name of the tool to call")
    arguments: dict[str, Any] = Field(
        default_factory=dict, description="Arguments passed to the tool"
    )


class Message(BaseModel):
    """A single message in a conversation."""

    role: MessageRole = Field(..., description="Role of the message sender")
    content: str = Field(..., description="Content of the message")
    name: str | None = Field(None, description="Optional name for the sender")
    tool_calls: list[ToolCall] | None = Field(
        None, description="Tool calls made by the assistant"
    )
    tool_call_id: str | None = Field(
        None, description="ID of the tool call this message responds to"
    )

    @classmethod
    def system(cls, content: str) -> Message:
        """Create a system message."""
        return cls(role=MessageRole.SYSTEM, content=content)

    @classmethod
    def user(cls, content: str) -> Message:
        """Create a user message."""
        return cls(role=MessageRole.USER, content=content)

    @classmethod
    def assistant(cls, content: str) -> Message:
        """Create an assistant message."""
        return cls(role=MessageRole.ASSISTANT, content=content)


class Usage(BaseModel):
    """Token usage statistics."""

    prompt_tokens: int = Field(..., ge=0, description="Number of prompt tokens used")
    completion_tokens: int = Field(
        ..., ge=0, description="Number of completion tokens used"
    )

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.prompt_tokens + self.completion_tokens


class LLMResponse(BaseModel):
    """Response from an LLM provider."""

    content: str = Field(..., description="Generated content")
    model: str = Field(..., description="Model used for generation")
    usage: Usage = Field(..., description="Token usage statistics")
    finish_reason: str = Field(..., description="Reason for completion")
    tool_calls: list[ToolCall] | None = Field(
        None, description="Tool calls requested by the model"
    )
    raw_response: dict[str, Any] | None = Field(
        None, description="Raw response from the provider"
    )


class AgentResult(BaseModel):
    """Result of an agent execution."""

    output: str = Field(..., description="Final output from the agent")
    parsed_output: dict[str, Any] | None = Field(
        None, description="Parsed structured output if output_schema was used"
    )
    messages: list[Message] = Field(
        default_factory=list, description="Full conversation history"
    )
    usage: Usage = Field(..., description="Token usage statistics")
    cost: float = Field(..., ge=0, description="Estimated cost in USD")
    duration_ms: int = Field(..., ge=0, description="Execution duration in milliseconds")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class StreamChunk(BaseModel):
    """A chunk of streamed LLM response."""

    content: str = Field(..., description="Accumulated content so far")
    delta: str = Field(..., description="New content in this chunk")
    finish_reason: str | None = Field(
        None, description="Reason for completion (last chunk only)"
    )
    usage: Usage | None = Field(None, description="Token usage (last chunk only)")
