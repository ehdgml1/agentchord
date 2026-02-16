#!/usr/bin/env python3
"""AgentWeave Multi-Agent Team Example.

Shows how to create a team of agents that collaborate using
the coordinator strategy (delegation via tools).

실행 전 준비:
    export OPENAI_API_KEY="sk-your-api-key"

실행:
    python examples/15_multi_agent_team.py
"""
import asyncio

from agentweave import Agent, AgentTeam


async def main():
    # Define team members
    researcher = Agent(
        name="researcher",
        role="Research expert who finds and analyzes information",
        model="gpt-4o-mini",
    )
    writer = Agent(
        name="writer",
        role="Content writer who creates clear, engaging text",
        model="gpt-4o-mini",
    )
    reviewer = Agent(
        name="reviewer",
        role="Quality reviewer who checks accuracy and clarity",
        model="gpt-4o-mini",
    )

    # Create a team with coordinator strategy
    team = AgentTeam(
        name="content-team",
        members=[researcher, writer, reviewer],
        strategy="coordinator",
        max_rounds=5,
    )

    print("=== Multi-Agent Team: Coordinator Strategy ===\n")

    async with team:
        result = await team.run(
            "Write a short summary about the benefits of multi-agent AI systems"
        )

    print(f"Output:\n{result.output}\n")
    print(f"Strategy: {result.strategy}")
    print(f"Rounds: {result.rounds}")
    print(f"Total Cost: ${result.total_cost:.4f}")
    print(f"Total Tokens: {result.total_tokens:,}")
    print(f"Duration: {result.duration_ms}ms")
    print(f"\nAgent Outputs:")
    for name, output in result.agent_outputs.items():
        role_value = output.role.value if hasattr(output.role, "value") else str(output.role)
        print(f"  [{name}] ({role_value}): {output.output[:100]}...")
    print(f"\nMessages exchanged: {len(result.messages)}")


if __name__ == "__main__":
    asyncio.run(main())
