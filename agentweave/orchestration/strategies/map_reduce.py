"""Map-reduce strategy - parallel task splitting and result merging."""
from __future__ import annotations

import asyncio
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


class MapReduceStrategy(BaseStrategy):
    """Split task among agents, execute in parallel, merge results.

    All agents handle the task in parallel (map phase).
    The first agent then merges all results (reduce phase).
    """

    async def execute(
        self,
        task: str,
        agents: dict[str, Any],
        **kwargs: Any,
    ) -> TeamResult:
        from agentweave.orchestration.message_bus import MessageBus

        message_bus: MessageBus | None = kwargs.get("message_bus")

        start_time = time.time()
        agent_outputs: dict[str, AgentOutput] = {}
        total_cost = 0.0
        total_tokens = 0
        agent_list = list(agents.items())

        if len(agent_list) == 1:
            # Single agent, just run directly
            name, agent = agent_list[0]
            result = await agent.run(task)
            tokens = result.usage.total_tokens if result.usage else 0
            return TeamResult(
                output=result.output,
                agent_outputs={
                    name: AgentOutput(
                        agent_name=name,
                        role=TeamRole.WORKER,
                        output=result.output,
                        tokens=tokens,
                        cost=result.cost,
                        duration_ms=result.duration_ms,
                    )
                },
                total_cost=result.cost,
                total_tokens=tokens,
                rounds=1,
                duration_ms=int((time.time() - start_time) * 1000),
                strategy=kwargs.get("strategy_name", "map_reduce"),
            )

        # Map phase: all agents work on the task in parallel
        async def _run_agent(name: str, agent: Any) -> tuple[str, Any]:
            if message_bus:
                await message_bus.send(AgentMessage(
                    sender="system",
                    recipient=name,
                    message_type=MessageType.TASK,
                    content=task,
                ))
            result = await agent.run(task)
            if message_bus:
                await message_bus.send(AgentMessage(
                    sender=name,
                    recipient="system",
                    message_type=MessageType.RESULT,
                    content=result.output,
                ))
            return name, result

        results = await asyncio.gather(
            *[_run_agent(name, agent) for name, agent in agent_list],
            return_exceptions=True,
        )

        # Collect outputs - some may be exceptions
        partial_outputs: list[str] = []
        for i, result_or_exc in enumerate(results):
            name = agent_list[i][0]
            if isinstance(result_or_exc, Exception):
                agent_outputs[name] = AgentOutput(
                    agent_name=name,
                    role=TeamRole.WORKER,
                    output=f"Error: {result_or_exc}",
                    tokens=0,
                    cost=0.0,
                    duration_ms=0,
                )
                partial_outputs.append(f"[{name}]: Error - {type(result_or_exc).__name__}")
                continue
            name, result = result_or_exc
            tokens = result.usage.total_tokens if result.usage else 0
            agent_outputs[name] = AgentOutput(
                agent_name=name,
                role=TeamRole.WORKER,
                output=result.output,
                tokens=tokens,
                cost=result.cost,
                duration_ms=result.duration_ms,
            )
            total_cost += result.cost
            total_tokens += tokens
            partial_outputs.append(f"[{name}]: {result.output}")

        # Reduce phase: first agent merges results
        reducer_name, reducer_agent = agent_list[0]
        merge_prompt = (
            f"Original task: {task}\n\n"
            f"The following agents have provided their outputs:\n\n"
            + "\n---\n".join(partial_outputs)
            + "\n\nPlease synthesize all outputs into a single "
            "comprehensive response."
        )

        merge_result = await reducer_agent.run(merge_prompt)
        tokens = merge_result.usage.total_tokens if merge_result.usage else 0
        agent_outputs[f"{reducer_name}_reduce"] = AgentOutput(
            agent_name=reducer_name,
            role=TeamRole.COORDINATOR,
            output=merge_result.output,
            tokens=tokens,
            cost=merge_result.cost,
            duration_ms=merge_result.duration_ms,
        )
        total_cost += merge_result.cost
        total_tokens += tokens

        messages = message_bus.get_history() if message_bus else []
        return TeamResult(
            output=merge_result.output,
            agent_outputs=agent_outputs,
            messages=messages,
            total_cost=total_cost,
            total_tokens=total_tokens,
            rounds=2,  # Map + Reduce
            duration_ms=int((time.time() - start_time) * 1000),
            strategy=kwargs.get("strategy_name", "map_reduce"),
        )
