#!/usr/bin/env python3
"""AgentChord Debate Strategy Example.

Shows agents debating a topic and reaching consensus.

실행:
    python examples/16_debate_strategy.py
"""
import asyncio

from agentchord import Agent, AgentTeam


async def main():
    optimist = Agent(
        name="optimist",
        role="Sees opportunities and positive aspects of technology",
        model="gpt-4o-mini",
    )
    skeptic = Agent(
        name="skeptic",
        role="Questions assumptions and identifies risks",
        model="gpt-4o-mini",
    )

    team = AgentTeam(
        name="debate-team",
        members=[optimist, skeptic],
        strategy="debate",
        max_rounds=2,
    )

    print("=== Multi-Agent Debate Strategy ===\n")

    async with team:
        result = await team.run(
            "Should AI agents be given autonomous decision-making authority?"
        )

    print(f"Synthesized Output:\n{result.output}\n")
    print(f"Debate Rounds: {result.rounds}")
    print(f"Total Cost: ${result.total_cost:.4f}")
    print(f"\nDebate Contributions:")
    for name, output in result.agent_outputs.items():
        print(f"\n  [{name}]:")
        print(f"  {output.output[:200]}...")


if __name__ == "__main__":
    asyncio.run(main())
