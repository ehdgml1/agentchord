"""Coordinator strategy - delegates tasks to worker agents via tool calling."""
from __future__ import annotations

import time
from typing import Any

from agentchord.orchestration.strategies.base import BaseStrategy, StrategyContext
from agentchord.orchestration.tools import create_context_tools, create_delegation_tools
from agentchord.orchestration.types import (
    AgentOutput,
    TeamResult,
    TeamRole,
)


class CoordinatorStrategy(BaseStrategy):
    """Orchestration via a coordinator agent that delegates using tools.

    The coordinator receives delegation tools dynamically - one per team member.
    The LLM naturally decides when and to whom to delegate tasks.
    Worker agent results flow back through the tool calling loop.
    """

    async def execute(
        self,
        task: str,
        agents: dict[str, Any],
        ctx: StrategyContext,
    ) -> TeamResult:
        from agentchord.core.agent import Agent

        coordinator_agent: Agent | None = ctx.coordinator
        members = ctx.members
        message_bus = ctx.message_bus
        shared_context = ctx.shared_context
        max_rounds = ctx.max_rounds if ctx.max_rounds is not None else 10
        callbacks = ctx.callbacks

        start_time = time.time()
        agent_outputs: dict[str, AgentOutput] = {}
        total_cost = 0.0
        total_tokens = 0

        # Find coordinator or use first agent
        if coordinator_agent is None:
            coordinator_name = next(iter(agents))
            coordinator_agent = agents[coordinator_name]

        # Worker agents (all except coordinator)
        worker_agents = {
            name: agent for name, agent in agents.items()
            if agent is not coordinator_agent
        }

        if not worker_agents:
            # Only one agent, run directly
            result = await coordinator_agent.run(task)
            return TeamResult(
                output=result.output,
                agent_outputs={
                    coordinator_agent.name: AgentOutput(
                        agent_name=coordinator_agent.name,
                        role=TeamRole.COORDINATOR,
                        output=result.output,
                        tokens=result.usage.total_tokens if result.usage else 0,
                        cost=result.cost,
                        duration_ms=result.duration_ms,
                    )
                },
                total_cost=result.cost,
                total_tokens=result.usage.total_tokens if result.usage else 0,
                rounds=1,
                duration_ms=int((time.time() - start_time) * 1000),
                strategy=ctx.strategy_name or "coordinator",
            )

        # Build on_result callback to record AgentOutput
        async def _on_delegation_result(
            agent_name: str, role_str: str, worker_result: Any,
        ) -> None:
            """Record worker output when delegation completes."""
            # Resolve role enum from member info
            member_info = next(
                (m for m in members if m.name == agent_name), None
            )
            role_enum = member_info.role if member_info else TeamRole.WORKER
            agent_outputs[agent_name] = AgentOutput(
                agent_name=agent_name,
                role=role_enum,
                output=worker_result.output,
                tokens=(
                    worker_result.usage.total_tokens
                    if worker_result.usage else 0
                ),
                cost=worker_result.cost,
                duration_ms=worker_result.duration_ms,
            )

            if shared_context is not None:
                await shared_context.set(
                    f"{agent_name}_result", worker_result.output, agent=agent_name
                )

        # Create delegation tools via shared factory (M13: dedup)
        tool_members = [
            (
                name,
                worker,
                next((m for m in members if m.name == name), None),
            )
            for name, worker in worker_agents.items()
        ]
        delegation_tools = create_delegation_tools(
            members=tool_members,
            message_bus=message_bus,
            sender_name=coordinator_agent.name,
            on_result=_on_delegation_result,
        )

        # Create context tools if shared context is available
        context_tools = (
            create_context_tools(
                shared_context=shared_context,
                agent_name=coordinator_agent.name,
            )
            if shared_context is not None
            else []
        )
        all_tools = delegation_tools + context_tools

        # Build coordinator system prompt
        member_descriptions = []
        for name, agent in worker_agents.items():
            member_info = next(
                (m for m in members if m.name == name), None
            )
            caps = (
                f" (capabilities: {', '.join(member_info.capabilities)})"
                if member_info and member_info.capabilities
                else ""
            )
            member_descriptions.append(
                f"- {name}: {agent.role or 'worker'}{caps}"
            )

        coordinator_system = (
            "You are a team coordinator managing the following agents:\n"
            + "\n".join(member_descriptions)
            + "\n\n"
            "Your job is to:\n"
            "1. Analyze the given task\n"
            "2. Delegate subtasks to appropriate team members "
            "using the delegation tools\n"
            "3. Synthesize their results into a final comprehensive response\n\n"
            "Use the delegate_to_* tools to assign work. "
            "You can delegate to multiple agents."
        )

        # Use Agent's public context managers for tool injection and prompt extension
        async with coordinator_agent.temporary_tools(all_tools):
            async with coordinator_agent.with_extended_prompt(coordinator_system):
                # Run coordinator - pass max_rounds as max_tool_rounds
                coord_result = await coordinator_agent.run(
                    task, max_tool_rounds=max_rounds,
                )

                # Record coordinator output
                agent_outputs[coordinator_agent.name] = AgentOutput(
                    agent_name=coordinator_agent.name,
                    role=TeamRole.COORDINATOR,
                    output=coord_result.output,
                    tokens=(
                        coord_result.usage.total_tokens
                        if coord_result.usage else 0
                    ),
                    cost=coord_result.cost,
                    duration_ms=coord_result.duration_ms,
                )

                # Aggregate costs
                total_cost = sum(ao.cost for ao in agent_outputs.values())
                total_tokens = sum(ao.tokens for ao in agent_outputs.values())
                messages = message_bus.get_history() if message_bus else []

                return TeamResult(
                    output=coord_result.output,
                    agent_outputs=agent_outputs,
                    messages=messages,
                    total_cost=total_cost,
                    total_tokens=total_tokens,
                    rounds=len(agent_outputs),
                    duration_ms=int((time.time() - start_time) * 1000),
                    strategy=ctx.strategy_name or "coordinator",
                )
