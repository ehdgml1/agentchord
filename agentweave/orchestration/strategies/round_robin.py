"""Round-robin strategy - agents take turns refining output."""
from __future__ import annotations

import time
from typing import Any

from agentweave.orchestration.strategies.base import BaseStrategy
from agentweave.orchestration.types import (
    AgentMessage,
    AgentOutput,
    MessageType,
    TeamResult,
    TeamRole,
)


class RoundRobinStrategy(BaseStrategy):
    """Each agent takes a turn, building on the previous agent's output."""

    async def execute(
        self,
        task: str,
        agents: dict[str, Any],
        **kwargs: Any,
    ) -> TeamResult:
        from agentweave.orchestration.message_bus import MessageBus

        message_bus: MessageBus | None = kwargs.get("message_bus")
        max_rounds: int = kwargs.get("max_rounds", 1)

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

                if message_bus:
                    await message_bus.send(AgentMessage(
                        sender=name,
                        recipient="system",
                        message_type=MessageType.RESULT,
                        content=result.output,
                        metadata={"round": round_num + 1},
                    ))

        messages = message_bus.get_history() if message_bus else []
        return TeamResult(
            output=current_input,
            agent_outputs=agent_outputs,
            messages=messages,
            total_cost=total_cost,
            total_tokens=total_tokens,
            rounds=max_rounds,
            duration_ms=int((time.time() - start_time) * 1000),
            strategy=kwargs.get("strategy_name", "round_robin"),
        )
