"""Debate strategy - agents discuss and reach consensus."""
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


class DebateStrategy(BaseStrategy):
    """Agents debate a topic, each responding to previous arguments.

    After all rounds, a designated synthesizer (or the first agent)
    creates the final consolidated output.
    """

    async def execute(
        self,
        task: str,
        agents: dict[str, Any],
        ctx: StrategyContext,
    ) -> TeamResult:
        message_bus = ctx.message_bus
        max_rounds = ctx.max_rounds if ctx.max_rounds is not None else 3
        synthesizer_name: str | None = None  # Not in ctx; set externally if needed

        start_time = time.time()
        agent_outputs: dict[str, AgentOutput] = {}
        total_cost = 0.0
        total_tokens = 0
        debate_history: list[str] = []
        agent_list = list(agents.items())

        previous_positions: dict[str, str] = {}
        converged = False
        actual_rounds = 0

        for round_num in range(max_rounds):
            actual_rounds = round_num + 1
            current_positions: dict[str, str] = {}

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

                if message_bus:
                    await message_bus.send(AgentMessage(
                        sender="system",
                        recipient=name,
                        message_type=MessageType.TASK,
                        content=context[:500],
                        metadata={"round": round_num + 1},
                    ))

                if ctx.callbacks:
                    await ctx.callbacks.emit(
                        CallbackEvent.AGENT_DELEGATED,
                        agent_name=name,
                        round=round_num + 1,
                        strategy="debate",
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
                        result = await agent.run(context)
                else:
                    result = await agent.run(context)
                current_positions[name] = result.output
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

                if ctx.callbacks:
                    await ctx.callbacks.emit(
                        CallbackEvent.AGENT_COMPLETED,
                        agent_name=name,
                        round=round_num + 1,
                        tokens=tokens,
                        cost=result.cost,
                        strategy="debate",
                    )

                if ctx.shared_context is not None:
                    await ctx.shared_context.set(
                        f"{name}_position_r{round_num + 1}", result.output, agent=name
                    )

                if message_bus:
                    await message_bus.send(AgentMessage(
                        sender=name,
                        message_type=MessageType.RESPONSE,
                        content=result.output,
                        metadata={"round": round_num + 1},
                    ))

            # Check convergence (only after first round)
            if round_num > 0 and previous_positions:
                positions_unchanged = all(
                    current_positions.get(n) == previous_positions.get(n)
                    for n in current_positions
                )
                if positions_unchanged:
                    converged = True
                    if ctx.callbacks:
                        await ctx.callbacks.emit(
                            CallbackEvent.CONVERGENCE_DETECTED,
                            round=actual_rounds,
                            strategy="debate",
                        )
                    if ctx.shared_context is not None:
                        await ctx.shared_context.set(
                            "convergence_round", actual_rounds, agent="debate"
                        )
                    break

            previous_positions = dict(current_positions)

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

        if message_bus:
            await message_bus.send(AgentMessage(
                sender="system",
                recipient=synth_name,
                message_type=MessageType.TASK,
                content="Synthesize debate results",
                metadata={"phase": "synthesis"},
            ))

        if ctx.callbacks:
            await ctx.callbacks.emit(
                CallbackEvent.SYNTHESIS_START,
                synthesizer=synth_name,
                debate_rounds=max_rounds,
                strategy="debate",
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

        if ctx.callbacks:
            await ctx.callbacks.emit(
                CallbackEvent.AGENT_COMPLETED,
                agent_name=synth_name,
                round=max_rounds + 1,
                tokens=tokens,
                cost=synth_result.cost,
                strategy="debate",
                phase="synthesis",
            )

        if message_bus:
            await message_bus.send(AgentMessage(
                sender=synth_name,
                recipient="system",
                message_type=MessageType.RESULT,
                content=synth_result.output,
                metadata={"phase": "synthesis"},
            ))

        if ctx.shared_context is not None:
            await ctx.shared_context.set("synthesis", synth_result.output, agent=synth_name)

        if ctx.shared_context is not None and converged:
            await ctx.shared_context.set("converged", True, agent="debate")

        messages = message_bus.get_history() if message_bus else []
        return TeamResult(
            output=synth_result.output,
            agent_outputs=agent_outputs,
            messages=messages,
            total_cost=total_cost,
            total_tokens=total_tokens,
            rounds=actual_rounds,
            duration_ms=int((time.time() - start_time) * 1000),
            strategy=ctx.strategy_name or "debate",
        )
