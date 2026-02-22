"""Round-robin strategy - agents take turns refining output."""
from __future__ import annotations

import time
from typing import Any

from agentchord.orchestration.strategies.base import BaseStrategy, StrategyContext
from agentchord.orchestration.tools import create_consult_tools
from agentchord.orchestration.types import (
    AgentMessage,
    AgentOutput,
    MessageType,
    TeamResult,
    TeamRole,
)
from agentchord.tracking.callbacks import CallbackEvent


class RoundRobinStrategy(BaseStrategy):
    """Each agent takes a turn, building on the previous agent's output."""

    async def execute(
        self,
        task: str,
        agents: dict[str, Any],
        ctx: StrategyContext,
    ) -> TeamResult:
        message_bus = ctx.message_bus
        max_rounds = ctx.max_rounds if ctx.max_rounds is not None else 1

        start_time = time.time()
        agent_outputs: dict[str, AgentOutput] = {}
        total_cost = 0.0
        total_tokens = 0
        agent_list = list(agents.items())
        current_input = task

        for round_num in range(max_rounds):
            for name, agent in agent_list:
                if message_bus:
                    await message_bus.send(AgentMessage(
                        sender="system",
                        recipient=name,
                        message_type=MessageType.TASK,
                        content=current_input,
                        metadata={"round": round_num + 1},
                    ))

                if ctx.callbacks:
                    await ctx.callbacks.emit(
                        CallbackEvent.AGENT_DELEGATED,
                        agent_name=name,
                        round=round_num + 1,
                        strategy="round_robin",
                    )

                if ctx.enable_consult:
                    other_agents = [
                        (n, a, next((m for m in ctx.members if m.name == n), None))
                        for n, a in agent_list if n != name
                    ]
                    consult_tools = create_consult_tools(
                        peers=other_agents,
                        current_agent_name=name,
                        message_bus=message_bus,
                        max_depth=ctx.max_consult_depth,
                    )
                    async with agent.temporary_tools(consult_tools):
                        result = await agent.run(current_input)
                else:
                    result = await agent.run(current_input)
                current_input = result.output

                tokens = result.usage.total_tokens if result.usage else 0
                agent_outputs[f"{name}_r{round_num + 1}"] = AgentOutput(
                    agent_name=name,
                    role=TeamRole.WORKER,
                    output=result.output,
                    tokens=tokens,
                    cost=result.cost,
                    duration_ms=result.duration_ms,
                )
                total_cost += result.cost
                total_tokens += tokens

                if ctx.callbacks:
                    await ctx.callbacks.emit(
                        CallbackEvent.AGENT_COMPLETED,
                        agent_name=name,
                        round=round_num + 1,
                        tokens=tokens,
                        cost=result.cost,
                        strategy="round_robin",
                    )

                if ctx.shared_context is not None:
                    await ctx.shared_context.set(
                        f"{name}_r{round_num + 1}", result.output, agent=name
                    )

                if message_bus:
                    await message_bus.send(AgentMessage(
                        sender=name,
                        recipient="system",
                        message_type=MessageType.RESULT,
                        content=result.output,
                        metadata={"round": round_num + 1},
                    ))

        if ctx.shared_context is not None:
            await ctx.shared_context.set("final_output", current_input, agent="round_robin")

        messages = message_bus.get_history() if message_bus else []
        return TeamResult(
            output=current_input,
            agent_outputs=agent_outputs,
            messages=messages,
            total_cost=total_cost,
            total_tokens=total_tokens,
            rounds=max_rounds,
            duration_ms=int((time.time() - start_time) * 1000),
            strategy=ctx.strategy_name or "round_robin",
        )
