#!/usr/bin/env python3
"""Cost Tracking Example.

이 예제는 AgentWeave의 비용 추적 시스템 사용법을 보여줍니다.

실행:
    python examples/08_cost_tracking.py
"""

import asyncio

from agentweave.tracking import (
    TokenUsage,
    CostEntry,
    CostSummary,
    CostTracker,
    calculate_cost,
    CallbackEvent,
    CallbackContext,
    CallbackManager,
)


def demo_cost_calculation() -> None:
    """비용 계산 데모."""
    print("=" * 60)
    print("1. Cost Calculation Demo")
    print("=" * 60)

    # 토큰 사용량 생성
    usage = TokenUsage(
        prompt_tokens=1000,
        completion_tokens=500,
    )

    print(f"\n토큰 사용량:")
    print(f"  - 입력: {usage.prompt_tokens:,}")
    print(f"  - 출력: {usage.completion_tokens:,}")
    print(f"  - 총합: {usage.total_tokens:,}")

    # 모델별 비용 계산
    models = ["gpt-4o-mini", "gpt-4o", "claude-3-5-sonnet", "claude-3-opus"]

    print("\n[모델별 예상 비용]")
    for model in models:
        cost = calculate_cost(model, usage)
        print(f"  {model}: ${cost:.4f}")


def demo_cost_tracker() -> None:
    """CostTracker 데모."""
    print("\n" + "=" * 60)
    print("2. Cost Tracker Demo")
    print("=" * 60)

    # 예산 경고 콜백
    def on_warning(summary: CostSummary, threshold: float) -> None:
        print(f"\n⚠️  예산 경고! {threshold*100:.0f}% 도달")
        print(f"    현재 사용: ${summary.total_cost_usd:.4f}")

    # 트래커 생성 (예산 $0.10, 80%에서 경고)
    tracker = CostTracker(
        budget_limit=0.10,
        on_budget_warning=on_warning,
        warning_threshold=0.8,
    )

    print(f"\n예산 한도: ${tracker.budget_limit:.2f}")

    # API 호출 시뮬레이션
    calls = [
        ("gpt-4o-mini", TokenUsage(prompt_tokens=500, completion_tokens=200), "agent1"),
        ("gpt-4o-mini", TokenUsage(prompt_tokens=800, completion_tokens=300), "agent1"),
        ("gpt-4o", TokenUsage(prompt_tokens=200, completion_tokens=100), "agent2"),
        ("claude-3-haiku", TokenUsage(prompt_tokens=1000, completion_tokens=500), "agent2"),
    ]

    print("\n[API 호출 추적]")
    for model, usage, agent in calls:
        entry = tracker.track_usage(model=model, usage=usage, agent_name=agent)
        print(f"  {agent} → {model}: ${entry.cost_usd:.4f}")

    # 요약 출력
    summary = tracker.get_summary()

    print(f"\n[비용 요약]")
    print(f"  총 비용: ${summary.total_cost_usd:.4f}")
    print(f"  총 토큰: {summary.total_tokens:,}")
    print(f"  API 호출: {summary.request_count}회")
    print(f"  남은 예산: ${tracker.remaining_budget:.4f}")

    print(f"\n[모델별 비용]")
    for model, cost in summary.by_model.items():
        print(f"  {model}: ${cost:.4f}")

    print(f"\n[Agent별 비용]")
    for agent, cost in summary.by_agent.items():
        print(f"  {agent}: ${cost:.4f}")


async def demo_callbacks() -> None:
    """CallbackManager 데모."""
    print("\n" + "=" * 60)
    print("3. Callback System Demo")
    print("=" * 60)

    manager = CallbackManager()

    # 동기 콜백
    def on_agent_start(ctx: CallbackContext) -> None:
        print(f"  🚀 Agent 시작: {ctx.agent_name}")

    def on_agent_end(ctx: CallbackContext) -> None:
        output = ctx.data.get("output", "")[:50]
        print(f"  ✅ Agent 완료: {ctx.agent_name} → {output}...")

    # 비동기 콜백
    async def on_llm_call(ctx: CallbackContext) -> None:
        model = ctx.data.get("model", "unknown")
        print(f"  🤖 LLM 호출: {model}")

    # 글로벌 콜백 (모든 이벤트)
    def log_all(ctx: CallbackContext) -> None:
        print(f"  [LOG] {ctx.event.value} at {ctx.timestamp.strftime('%H:%M:%S')}")

    # 콜백 등록
    manager.register(CallbackEvent.AGENT_START, on_agent_start)
    manager.register(CallbackEvent.AGENT_END, on_agent_end)
    manager.register(CallbackEvent.LLM_START, on_llm_call)
    manager.register_global(log_all)

    print("\n[이벤트 시뮬레이션]")

    # 이벤트 발생 시뮬레이션
    await manager.emit(
        CallbackEvent.AGENT_START,
        agent_name="researcher",
    )

    await manager.emit(
        CallbackEvent.LLM_START,
        agent_name="researcher",
        model="gpt-4o-mini",
    )

    await manager.emit(
        CallbackEvent.LLM_END,
        agent_name="researcher",
        model="gpt-4o-mini",
        tokens=150,
    )

    await manager.emit(
        CallbackEvent.AGENT_END,
        agent_name="researcher",
        output="연구 결과: AI 기술은 빠르게 발전하고 있습니다.",
    )


async def main() -> None:
    """메인 함수."""
    print("\n" + "=" * 60)
    print("AgentWeave Cost Tracking Examples")
    print("=" * 60)

    demo_cost_calculation()
    demo_cost_tracker()
    await demo_callbacks()

    print("\n" + "=" * 60)
    print("Cost Tracking Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
