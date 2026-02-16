"""Debate strategy - agents discuss and reach consensus."""
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


class DebateStrategy(BaseStrategy):
    """Agents debate a topic, each responding to previous arguments.

    After all rounds, a designated synthesizer (or the first agent)
    creates the final consolidated output.
    """

    async def execute(
        self,
        task: str,
        agents: dict[str, Any],
        **kwargs: Any,
    ) -> TeamResult:
        from agentweave.orchestration.message_bus import MessageBus

        message_bus: MessageBus | None = kwargs.get("message_bus")
        max_rounds: int = kwargs.get("max_rounds", 3)
        synthesizer_name: str | None = kwargs.get("synthesizer")

        start_time = time.time()
        agent_outputs: dict[str, AgentOutput] = {}
        total_cost = 0.0
        total_tokens = 0
        debate_history: list[str] = []
        agent_list = list(agents.items())

        for round_num in range(max_rounds):
            for name, agent in agent_list:
                # Build debate context
                if debate_history:
                    context = (
                        f"Task: {task}\n\n"
                        f"Previous arguments:\n"
                        + "\n---\n".join(
                            debate_history[-len(agent_list) * 2:]
                        )
                        + f"\n\nRound {round_num + 1}: Please provide your "
                        f"perspective, building on or challenging the "
                        f"previous arguments."
                    )
                else:
                    context = (
                        f"Task: {task}\n\n"
                        f"Round 1: Please provide your initial perspective "
                        f"on this topic."
                    )

                result = await agent.run(context)
                entry = (
                    f"[{name}] (Round {round_num + 1}): {result.output}"
                )
                debate_history.append(entry)

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
                        message_type=MessageType.RESPONSE,
                        content=result.output,
                        metadata={"round": round_num + 1},
                    ))

        # Synthesize final output
        synth_name = synthesizer_name or agent_list[0][0]
        synth_agent = agents.get(synth_name, agent_list[0][1])

        synthesis_prompt = (
            f"Task: {task}\n\n"
            f"The following debate has concluded:\n"
            + "\n---\n".join(debate_history)
            + "\n\nPlease synthesize the key points into a final, "
            "comprehensive response."
        )

        synth_result = await synth_agent.run(synthesis_prompt)
        tokens = synth_result.usage.total_tokens if synth_result.usage else 0
        agent_outputs[f"{synth_name}_synthesis"] = AgentOutput(
            agent_name=synth_name,
            role=TeamRole.COORDINATOR,
            output=synth_result.output,
            tokens=tokens,
            cost=synth_result.cost,
            duration_ms=synth_result.duration_ms,
        )
        total_cost += synth_result.cost
        total_tokens += tokens

        messages = message_bus.get_history() if message_bus else []
        return TeamResult(
            output=synth_result.output,
            agent_outputs=agent_outputs,
            messages=messages,
            total_cost=total_cost,
            total_tokens=total_tokens,
            rounds=max_rounds,
            duration_ms=int((time.time() - start_time) * 1000),
            strategy=kwargs.get("strategy_name", "debate"),
        )
