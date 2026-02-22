"""Tracking data models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, computed_field


class TokenUsage(BaseModel):
    """Token usage for a single LLM call."""

    prompt_tokens: int = 0
    completion_tokens: int = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.prompt_tokens + self.completion_tokens

    def __add__(self, other: TokenUsage) -> TokenUsage:
        """Add two usage records."""
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
        )


class CostEntry(BaseModel):
    """Single cost tracking entry."""

    timestamp: datetime = Field(default_factory=datetime.now)
    model: str
    usage: TokenUsage
    cost_usd: float
    agent_name: str | None = None
    request_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CostSummary(BaseModel):
    """Aggregated cost summary."""

    total_cost_usd: float = 0.0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    request_count: int = 0
    by_model: dict[str, float] = Field(default_factory=dict)
    by_agent: dict[str, float] = Field(default_factory=dict)

    @classmethod
    def from_entries(cls, entries: list[CostEntry]) -> CostSummary:
        """Create summary from list of entries."""
        if not entries:
            return cls()

        total_cost = 0.0
        total_prompt = 0
        total_completion = 0
        by_model: dict[str, float] = {}
        by_agent: dict[str, float] = {}

        for entry in entries:
            total_cost += entry.cost_usd
            total_prompt += entry.usage.prompt_tokens
            total_completion += entry.usage.completion_tokens

            # Aggregate by model
            by_model[entry.model] = by_model.get(entry.model, 0.0) + entry.cost_usd

            # Aggregate by agent
            if entry.agent_name:
                by_agent[entry.agent_name] = (
                    by_agent.get(entry.agent_name, 0.0) + entry.cost_usd
                )

        return cls(
            total_cost_usd=total_cost,
            total_tokens=total_prompt + total_completion,
            prompt_tokens=total_prompt,
            completion_tokens=total_completion,
            request_count=len(entries),
            by_model=by_model,
            by_agent=by_agent,
        )
