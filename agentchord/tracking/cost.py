"""Cost tracking implementation."""

from __future__ import annotations

import threading
from typing import Callable

from agentchord.tracking.models import CostEntry, CostSummary, TokenUsage
from agentchord.tracking.pricing import calculate_cost
from agentchord.errors.exceptions import CostLimitExceededError


class CostTracker:
    """Thread-safe cost tracker for LLM API usage.

    Tracks token usage and costs across all LLM calls,
    with optional budget limits and callbacks.

    Example:
        >>> tracker = CostTracker(budget_limit=10.0)
        >>> tracker.track(CostEntry(
        ...     model="gpt-4o-mini",
        ...     usage=TokenUsage(prompt_tokens=100, completion_tokens=50),
        ...     cost_usd=0.001,
        ... ))
        >>> print(tracker.get_summary().total_cost_usd)
        0.001
    """

    def __init__(
        self,
        budget_limit: float | None = None,
        on_budget_warning: Callable[[CostSummary, float], None] | None = None,
        warning_threshold: float = 0.8,
        on_budget_exceeded: Callable[[CostSummary], None] | None = None,
        raise_on_exceed: bool = False,
    ) -> None:
        """Initialize cost tracker.

        Args:
            budget_limit: Maximum budget in USD (None = unlimited).
            on_budget_warning: Callback when usage reaches warning_threshold of budget.
            warning_threshold: Fraction of budget to trigger warning (0-1).
            on_budget_exceeded: Callback when budget is exceeded.
            raise_on_exceed: Whether to raise exception when budget exceeded.
        """
        self._budget_limit = budget_limit
        self._on_budget_warning = on_budget_warning
        self._warning_threshold = warning_threshold
        self._on_budget_exceeded = on_budget_exceeded
        self._raise_on_exceed = raise_on_exceed

        self._entries: list[CostEntry] = []
        self._lock = threading.Lock()
        self._warning_triggered = False

    @property
    def budget_limit(self) -> float | None:
        """Budget limit in USD."""
        return self._budget_limit

    @property
    def is_over_budget(self) -> bool:
        """Check if budget is exceeded."""
        if self._budget_limit is None:
            return False
        return self.total_cost >= self._budget_limit

    @property
    def total_cost(self) -> float:
        """Total cost in USD."""
        with self._lock:
            return sum(e.cost_usd for e in self._entries)

    @property
    def remaining_budget(self) -> float | None:
        """Remaining budget in USD (None if unlimited)."""
        if self._budget_limit is None:
            return None
        return max(0, self._budget_limit - self.total_cost)

    def track(self, entry: CostEntry) -> None:
        """Track a cost entry.

        Args:
            entry: The cost entry to track.

        Raises:
            CostLimitExceededError: If budget exceeded and raise_on_exceed=True.
        """
        with self._lock:
            self._entries.append(entry)

        self._check_budget()

    def track_usage(
        self,
        model: str,
        usage: TokenUsage,
        agent_name: str | None = None,
        **metadata: any,
    ) -> CostEntry:
        """Convenience method to track usage with auto-calculated cost.

        Args:
            model: Model name.
            usage: Token usage.
            agent_name: Optional agent name.
            **metadata: Additional metadata.

        Returns:
            The created CostEntry.
        """
        cost = calculate_cost(model, usage)
        entry = CostEntry(
            model=model,
            usage=usage,
            cost_usd=cost,
            agent_name=agent_name,
            metadata=metadata,
        )
        self.track(entry)
        return entry

    def get_summary(self) -> CostSummary:
        """Get aggregated cost summary."""
        with self._lock:
            return CostSummary.from_entries(list(self._entries))

    def get_entries(self) -> list[CostEntry]:
        """Get all tracked entries."""
        with self._lock:
            return list(self._entries)

    def get_by_model(self, model: str) -> CostSummary:
        """Get summary for a specific model."""
        with self._lock:
            entries = [e for e in self._entries if e.model == model]
            return CostSummary.from_entries(entries)

    def get_by_agent(self, agent_name: str) -> CostSummary:
        """Get summary for a specific agent."""
        with self._lock:
            entries = [e for e in self._entries if e.agent_name == agent_name]
            return CostSummary.from_entries(entries)

    def reset(self) -> CostSummary:
        """Reset tracker and return final summary.

        Returns:
            Summary of costs before reset.
        """
        with self._lock:
            summary = CostSummary.from_entries(list(self._entries))
            self._entries.clear()
            self._warning_triggered = False
            return summary

    def _check_budget(self) -> None:
        """Check budget limits and trigger callbacks."""
        if self._budget_limit is None:
            return

        total = self.total_cost

        # Check warning threshold
        if (
            not self._warning_triggered
            and self._on_budget_warning
            and total >= self._budget_limit * self._warning_threshold
        ):
            self._warning_triggered = True
            self._on_budget_warning(self.get_summary(), self._warning_threshold)

        # Check budget exceeded
        if total >= self._budget_limit:
            if self._on_budget_exceeded:
                self._on_budget_exceeded(self.get_summary())

            if self._raise_on_exceed:
                raise CostLimitExceededError(
                    current_cost=total,
                    limit=self._budget_limit,
                )
