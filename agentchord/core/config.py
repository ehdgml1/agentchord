"""Configuration classes for AgentChord.

This module provides configuration dataclasses for agents and workflows.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AgentConfig(BaseModel):
    """Configuration for an Agent.

    Example:
        >>> config = AgentConfig(
        ...     model="gpt-4o-mini",
        ...     temperature=0.7,
        ...     max_tokens=4096,
        ... )
    """

    model: str = Field(
        default="gpt-4o-mini",
        description="LLM model to use (e.g., 'gpt-4o', 'claude-3-5-sonnet')",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0 = deterministic, 2.0 = very random)",
    )
    max_tokens: int = Field(
        default=4096,
        gt=0,
        description="Maximum number of tokens to generate",
    )
    timeout: float = Field(
        default=60.0,
        gt=0,
        description="Timeout in seconds for LLM requests",
    )
    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter",
    )
    stop: list[str] | None = Field(
        default=None,
        description="Stop sequences for generation",
    )


class CostConfig(BaseModel):
    """Configuration for cost tracking.

    Example:
        >>> config = CostConfig(
        ...     budget_limit=5.0,
        ...     alert_threshold=0.8,
        ... )
    """

    budget_limit: float | None = Field(
        default=None,
        gt=0,
        description="Maximum budget in USD. None means unlimited.",
    )
    alert_threshold: float = Field(
        default=0.8,
        gt=0,
        le=1.0,
        description="Percentage of budget at which to trigger alerts (0.0-1.0)",
    )
    track_per_agent: bool = Field(
        default=True,
        description="Whether to track costs per agent",
    )


class RetryConfig(BaseModel):
    """Configuration for retry behavior.

    Example:
        >>> config = RetryConfig(
        ...     max_retries=3,
        ...     backoff_multiplier=2.0,
        ... )
    """

    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum number of retry attempts",
    )
    initial_delay: float = Field(
        default=1.0,
        gt=0,
        description="Initial delay between retries in seconds",
    )
    backoff_multiplier: float = Field(
        default=2.0,
        ge=1.0,
        description="Multiplier for exponential backoff",
    )
    max_delay: float = Field(
        default=60.0,
        gt=0,
        description="Maximum delay between retries in seconds",
    )
    retryable_exceptions: tuple[type[Exception], ...] = Field(
        default=(),
        description="Exception types that should trigger retry",
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)
