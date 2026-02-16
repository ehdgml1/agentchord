"""Unit tests for Tracking module."""

from __future__ import annotations

import pytest

from agentweave.tracking.models import TokenUsage, CostEntry, CostSummary
from agentweave.tracking.pricing import (
    MODEL_PRICING,
    calculate_cost,
    get_model_pricing,
    DEFAULT_PRICING,
)
from agentweave.tracking.cost import CostTracker
from agentweave.tracking.callbacks import (
    CallbackEvent,
    CallbackContext,
    CallbackManager,
)
from agentweave.errors.exceptions import CostLimitExceededError


class TestTokenUsage:
    """Tests for TokenUsage."""

    def test_total_tokens(self) -> None:
        """Should calculate total correctly."""
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50)

        assert usage.total_tokens == 150

    def test_addition(self) -> None:
        """Should add two usage records."""
        a = TokenUsage(prompt_tokens=100, completion_tokens=50)
        b = TokenUsage(prompt_tokens=200, completion_tokens=100)

        result = a + b

        assert result.prompt_tokens == 300
        assert result.completion_tokens == 150


class TestCostEntry:
    """Tests for CostEntry."""

    def test_entry_creation(self) -> None:
        """Should create entry with defaults."""
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50)
        entry = CostEntry(
            model="gpt-4o-mini",
            usage=usage,
            cost_usd=0.001,
        )

        assert entry.model == "gpt-4o-mini"
        assert entry.cost_usd == 0.001
        assert entry.timestamp is not None


class TestCostSummary:
    """Tests for CostSummary."""

    def test_from_entries_empty(self) -> None:
        """Should handle empty list."""
        summary = CostSummary.from_entries([])

        assert summary.total_cost_usd == 0.0
        assert summary.request_count == 0

    def test_from_entries_aggregation(self) -> None:
        """Should aggregate entries correctly."""
        entries = [
            CostEntry(
                model="gpt-4o-mini",
                usage=TokenUsage(prompt_tokens=100, completion_tokens=50),
                cost_usd=0.01,
                agent_name="agent1",
            ),
            CostEntry(
                model="gpt-4o",
                usage=TokenUsage(prompt_tokens=200, completion_tokens=100),
                cost_usd=0.05,
                agent_name="agent1",
            ),
            CostEntry(
                model="gpt-4o-mini",
                usage=TokenUsage(prompt_tokens=50, completion_tokens=25),
                cost_usd=0.005,
                agent_name="agent2",
            ),
        ]

        summary = CostSummary.from_entries(entries)

        assert summary.total_cost_usd == pytest.approx(0.065)
        assert summary.request_count == 3
        assert summary.prompt_tokens == 350
        assert summary.completion_tokens == 175
        assert summary.by_model["gpt-4o-mini"] == pytest.approx(0.015)
        assert summary.by_agent["agent1"] == pytest.approx(0.06)


class TestPricing:
    """Tests for pricing utilities."""

    def test_known_model_pricing(self) -> None:
        """Should return correct pricing for known models."""
        pricing = get_model_pricing("gpt-4o-mini")

        assert pricing == (0.15, 0.60)

    def test_unknown_model_default(self) -> None:
        """Should return default for unknown models."""
        pricing = get_model_pricing("unknown-model-xyz")

        assert pricing == DEFAULT_PRICING

    def test_calculate_cost(self) -> None:
        """Should calculate cost correctly."""
        usage = TokenUsage(prompt_tokens=1_000_000, completion_tokens=1_000_000)

        cost = calculate_cost("gpt-4o-mini", usage)

        # 0.15 + 0.60 = 0.75 per 1M total
        assert cost == pytest.approx(0.75)


class TestCostTracker:
    """Tests for CostTracker."""

    def test_track_and_summary(self) -> None:
        """Should track entries and provide summary."""
        tracker = CostTracker()

        tracker.track(CostEntry(
            model="gpt-4o-mini",
            usage=TokenUsage(prompt_tokens=100, completion_tokens=50),
            cost_usd=0.01,
        ))

        summary = tracker.get_summary()

        assert summary.total_cost_usd == 0.01
        assert summary.request_count == 1

    def test_track_usage_convenience(self) -> None:
        """Should auto-calculate cost."""
        tracker = CostTracker()

        entry = tracker.track_usage(
            model="gpt-4o-mini",
            usage=TokenUsage(prompt_tokens=1000, completion_tokens=500),
            agent_name="test",
        )

        assert entry.cost_usd > 0
        assert entry.agent_name == "test"

    def test_budget_limit_exceeded(self) -> None:
        """Should raise when budget exceeded."""
        tracker = CostTracker(budget_limit=0.01, raise_on_exceed=True)

        with pytest.raises(CostLimitExceededError):
            tracker.track(CostEntry(
                model="gpt-4o",
                usage=TokenUsage(prompt_tokens=1000, completion_tokens=500),
                cost_usd=0.02,  # Over budget
            ))

    def test_budget_warning_callback(self) -> None:
        """Should call warning callback."""
        warnings: list[float] = []

        def on_warning(summary: CostSummary, threshold: float) -> None:
            warnings.append(threshold)

        tracker = CostTracker(
            budget_limit=0.10,
            on_budget_warning=on_warning,
            warning_threshold=0.5,
        )

        tracker.track(CostEntry(
            model="gpt-4o",
            usage=TokenUsage(prompt_tokens=1000, completion_tokens=500),
            cost_usd=0.06,  # 60% of budget
        ))

        assert len(warnings) == 1
        assert warnings[0] == 0.5

    def test_reset(self) -> None:
        """Should reset tracker."""
        tracker = CostTracker()
        tracker.track(CostEntry(
            model="gpt-4o-mini",
            usage=TokenUsage(prompt_tokens=100, completion_tokens=50),
            cost_usd=0.01,
        ))

        summary = tracker.reset()

        assert summary.total_cost_usd == 0.01
        assert tracker.total_cost == 0.0


class TestCallbackManager:
    """Tests for CallbackManager."""

    @pytest.mark.asyncio
    async def test_register_and_emit(self) -> None:
        """Should call registered callback."""
        manager = CallbackManager()
        events: list[CallbackEvent] = []

        def on_start(ctx: CallbackContext) -> None:
            events.append(ctx.event)

        manager.register(CallbackEvent.AGENT_START, on_start)
        await manager.emit(CallbackEvent.AGENT_START)

        assert events == [CallbackEvent.AGENT_START]

    @pytest.mark.asyncio
    async def test_global_callback(self) -> None:
        """Should call global callback for all events."""
        manager = CallbackManager()
        events: list[CallbackEvent] = []

        def on_any(ctx: CallbackContext) -> None:
            events.append(ctx.event)

        manager.register_global(on_any)
        await manager.emit(CallbackEvent.AGENT_START)
        await manager.emit(CallbackEvent.AGENT_END)

        assert events == [CallbackEvent.AGENT_START, CallbackEvent.AGENT_END]

    @pytest.mark.asyncio
    async def test_async_callback(self) -> None:
        """Should support async callbacks."""
        manager = CallbackManager()
        results: list[str] = []

        async def async_callback(ctx: CallbackContext) -> None:
            results.append(ctx.data.get("value", ""))

        manager.register(CallbackEvent.LLM_END, async_callback)
        await manager.emit(CallbackEvent.LLM_END, value="test")

        assert results == ["test"]

    def test_unregister(self) -> None:
        """Should unregister callback."""
        manager = CallbackManager()

        def callback(ctx: CallbackContext) -> None:
            pass

        manager.register(CallbackEvent.AGENT_START, callback)
        removed = manager.unregister(CallbackEvent.AGENT_START, callback)

        assert removed is True
