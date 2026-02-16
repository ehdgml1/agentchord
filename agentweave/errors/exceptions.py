"""AgentWeave exception hierarchy.

All exceptions inherit from AgentWeaveError for easy catching.
Each exception includes a `retryable` flag to indicate if the operation can be retried.
"""

from __future__ import annotations


class AgentWeaveError(Exception):
    """Base exception for all AgentWeave errors."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


# Configuration Errors
class ConfigurationError(AgentWeaveError):
    """Configuration-related errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message, retryable=False)


class MissingAPIKeyError(ConfigurationError):
    """API key is missing or not configured."""

    def __init__(self, provider: str) -> None:
        super().__init__(
            f"API key for '{provider}' is not configured. "
            f"Set the {provider.upper()}_API_KEY environment variable."
        )
        self.provider = provider


class InvalidConfigError(ConfigurationError):
    """Invalid configuration value."""

    def __init__(self, field: str, value: object, reason: str) -> None:
        super().__init__(f"Invalid config for '{field}': {value}. {reason}")
        self.field = field
        self.value = value


# LLM Errors
class LLMError(AgentWeaveError):
    """Base class for LLM-related errors."""

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        model: str | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message, retryable=retryable)
        self.provider = provider
        self.model = model


class RateLimitError(LLMError):
    """Rate limit exceeded. Can be retried after backoff."""

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        model: str | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message, provider=provider, model=model, retryable=True)
        self.retry_after = retry_after


class AuthenticationError(LLMError):
    """Authentication failed. Cannot be retried without fixing credentials."""

    def __init__(self, message: str, *, provider: str) -> None:
        super().__init__(message, provider=provider, retryable=False)


class APIError(LLMError):
    """General API error. May be retried."""

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        model: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message, provider=provider, model=model, retryable=True)
        self.status_code = status_code


class TimeoutError(LLMError):
    """Request timed out. Can be retried."""

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        model: str | None = None,
        timeout_seconds: float,
    ) -> None:
        super().__init__(message, provider=provider, model=model, retryable=True)
        self.timeout_seconds = timeout_seconds


class ModelNotFoundError(LLMError):
    """Model not found or not supported."""

    def __init__(self, model: str, provider: str | None = None) -> None:
        provider_str = provider or "unknown"
        super().__init__(
            f"Model '{model}' not found or not supported by provider '{provider_str}'.",
            provider=provider_str,
            model=model,
            retryable=False,
        )


# Agent Errors
class AgentError(AgentWeaveError):
    """Base class for Agent-related errors."""

    def __init__(
        self,
        message: str,
        *,
        agent_name: str,
        retryable: bool = False,
    ) -> None:
        super().__init__(message, retryable=retryable)
        self.agent_name = agent_name


class AgentExecutionError(AgentError):
    """Error during agent execution."""

    def __init__(self, message: str, *, agent_name: str) -> None:
        super().__init__(message, agent_name=agent_name, retryable=True)


class AgentTimeoutError(AgentError):
    """Agent execution timed out."""

    def __init__(self, agent_name: str, timeout_seconds: float) -> None:
        super().__init__(
            f"Agent '{agent_name}' timed out after {timeout_seconds}s.",
            agent_name=agent_name,
            retryable=True,
        )
        self.timeout_seconds = timeout_seconds


# Cost Errors
class CostLimitExceededError(AgentWeaveError):
    """Cost limit exceeded."""

    def __init__(
        self,
        current_cost: float,
        limit: float,
        *,
        agent_name: str | None = None,
    ) -> None:
        super().__init__(
            f"Cost limit exceeded: ${current_cost:.4f} >= ${limit:.4f}",
            retryable=False,
        )
        self.current_cost = current_cost
        self.limit = limit
        self.agent_name = agent_name


# Workflow Errors
class WorkflowError(AgentWeaveError):
    """Base class for Workflow-related errors."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message, retryable=retryable)


class InvalidFlowError(WorkflowError):
    """Invalid flow DSL syntax."""

    def __init__(self, flow: str, reason: str) -> None:
        super().__init__(f"Invalid flow '{flow}': {reason}", retryable=False)
        self.flow = flow
        self.reason = reason


class AgentNotFoundInFlowError(WorkflowError):
    """Agent referenced in flow does not exist."""

    def __init__(self, agent_name: str, available: list[str]) -> None:
        super().__init__(
            f"Agent '{agent_name}' not found in workflow. "
            f"Available agents: {', '.join(available)}",
            retryable=False,
        )
        self.agent_name = agent_name
        self.available = available


class WorkflowExecutionError(WorkflowError):
    """Error during workflow execution."""

    def __init__(
        self,
        message: str,
        *,
        failed_agent: str | None = None,
        step_index: int | None = None,
    ) -> None:
        super().__init__(message, retryable=True)
        self.failed_agent = failed_agent
        self.step_index = step_index


class EmptyWorkflowError(WorkflowError):
    """Workflow has no agents or steps defined."""

    def __init__(self) -> None:
        super().__init__(
            "Workflow has no agents. Add agents before running.",
            retryable=False,
        )
