"""Unit tests for orchestration types."""

from __future__ import annotations

from datetime import datetime

import pytest

from agentweave.orchestration.types import (
    AgentMessage,
    AgentOutput,
    MessageType,
    OrchestrationStrategy,
    TeamEvent,
    TeamMember,
    TeamResult,
    TeamRole,
)


class TestMessageType:
    """Tests for MessageType enum."""

    def test_message_type_values(self) -> None:
        """MessageType should have all expected values."""
        assert MessageType.TASK == "task"
        assert MessageType.RESULT == "result"
        assert MessageType.QUERY == "query"
        assert MessageType.RESPONSE == "response"
        assert MessageType.BROADCAST == "broadcast"
        assert MessageType.SYSTEM == "system"

    def test_message_type_count(self) -> None:
        """MessageType should have exactly 6 values."""
        assert len(MessageType) == 6


class TestTeamRole:
    """Tests for TeamRole enum."""

    def test_team_role_values(self) -> None:
        """TeamRole should have all expected values."""
        assert TeamRole.COORDINATOR == "coordinator"
        assert TeamRole.WORKER == "worker"
        assert TeamRole.REVIEWER == "reviewer"
        assert TeamRole.SPECIALIST == "specialist"

    def test_team_role_count(self) -> None:
        """TeamRole should have exactly 4 values."""
        assert len(TeamRole) == 4


class TestOrchestrationStrategy:
    """Tests for OrchestrationStrategy enum."""

    def test_orchestration_strategy_values(self) -> None:
        """OrchestrationStrategy should have all expected values."""
        assert OrchestrationStrategy.COORDINATOR == "coordinator"
        assert OrchestrationStrategy.ROUND_ROBIN == "round_robin"
        assert OrchestrationStrategy.DEBATE == "debate"
        assert OrchestrationStrategy.MAP_REDUCE == "map_reduce"
        assert OrchestrationStrategy.SEQUENTIAL == "sequential"

    def test_orchestration_strategy_count(self) -> None:
        """OrchestrationStrategy should have exactly 5 values."""
        assert len(OrchestrationStrategy) == 5


class TestAgentMessage:
    """Tests for AgentMessage."""

    def test_message_creation_minimal(self) -> None:
        """Message should be created with minimal required fields."""
        msg = AgentMessage(
            sender="agent-1",
            message_type=MessageType.TASK,
            content="Process this data",
        )

        assert msg.sender == "agent-1"
        assert msg.recipient is None
        assert msg.message_type == MessageType.TASK
        assert msg.content == "Process this data"
        assert msg.id  # Auto-generated UUID
        assert msg.timestamp  # Auto-generated timestamp
        assert msg.metadata == {}
        assert msg.parent_id is None

    def test_message_creation_full(self) -> None:
        """Message should accept all fields."""
        msg = AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            message_type=MessageType.RESULT,
            content="Task completed",
            metadata={"duration": 1.5, "tokens": 100},
            parent_id="msg-123",
        )

        assert msg.sender == "agent-1"
        assert msg.recipient == "agent-2"
        assert msg.message_type == MessageType.RESULT
        assert msg.content == "Task completed"
        assert msg.metadata["duration"] == 1.5
        assert msg.parent_id == "msg-123"

    def test_message_auto_id_unique(self) -> None:
        """Auto-generated message IDs should be unique."""
        msg1 = AgentMessage(sender="a", message_type=MessageType.TASK, content="1")
        msg2 = AgentMessage(sender="a", message_type=MessageType.TASK, content="2")

        assert msg1.id != msg2.id

    def test_message_auto_timestamp(self) -> None:
        """Auto-generated timestamp should be present."""
        msg = AgentMessage(sender="agent", message_type=MessageType.TASK, content="test")

        assert isinstance(msg.timestamp, datetime)

    def test_message_serialization(self) -> None:
        """Message should serialize to dict."""
        msg = AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            message_type=MessageType.QUERY,
            content="What is the status?",
        )

        data = msg.model_dump()

        assert data["sender"] == "agent-1"
        assert data["recipient"] == "agent-2"
        assert data["message_type"] == "query"
        assert data["content"] == "What is the status?"
        assert "id" in data
        assert "timestamp" in data

    def test_message_deserialization(self) -> None:
        """Message should deserialize from dict."""
        data = {
            "id": "msg-123",
            "sender": "agent-1",
            "recipient": "agent-2",
            "message_type": "task",
            "content": "Process",
            "metadata": {"key": "value"},
            "parent_id": None,
            "timestamp": "2024-01-01T00:00:00Z",
        }

        msg = AgentMessage.model_validate(data)

        assert msg.id == "msg-123"
        assert msg.sender == "agent-1"
        assert msg.message_type == MessageType.TASK
        assert msg.metadata["key"] == "value"

    def test_message_round_trip(self) -> None:
        """Message should survive serialization round-trip."""
        original = AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            message_type=MessageType.BROADCAST,
            content="Update all agents",
            metadata={"priority": "high"},
        )

        data = original.model_dump()
        restored = AgentMessage.model_validate(data)

        assert restored.sender == original.sender
        assert restored.recipient == original.recipient
        assert restored.message_type == original.message_type
        assert restored.content == original.content
        assert restored.metadata == original.metadata


class TestTeamMember:
    """Tests for TeamMember."""

    def test_member_creation_minimal(self) -> None:
        """TeamMember should be created with just a name."""
        member = TeamMember(name="worker-1")

        assert member.name == "worker-1"
        assert member.role == TeamRole.WORKER  # Default
        assert member.capabilities == []
        assert member.agent_config == {}

    def test_member_creation_full(self) -> None:
        """TeamMember should accept all fields."""
        member = TeamMember(
            name="research-agent",
            role=TeamRole.SPECIALIST,
            capabilities=["web_search", "summarization", "translation"],
            agent_config={"model": "gpt-4o", "temperature": 0.7},
        )

        assert member.name == "research-agent"
        assert member.role == TeamRole.SPECIALIST
        assert len(member.capabilities) == 3
        assert "web_search" in member.capabilities
        assert member.agent_config["model"] == "gpt-4o"

    def test_member_serialization(self) -> None:
        """TeamMember should serialize to dict."""
        member = TeamMember(
            name="coordinator",
            role=TeamRole.COORDINATOR,
            capabilities=["planning", "delegation"],
        )

        data = member.model_dump()

        assert data["name"] == "coordinator"
        assert data["role"] == "coordinator"
        assert data["capabilities"] == ["planning", "delegation"]

    def test_member_deserialization(self) -> None:
        """TeamMember should deserialize from dict."""
        data = {
            "name": "reviewer",
            "role": "reviewer",
            "capabilities": ["code_review"],
            "agent_config": {"strict": True},
        }

        member = TeamMember.model_validate(data)

        assert member.name == "reviewer"
        assert member.role == TeamRole.REVIEWER
        assert member.capabilities == ["code_review"]
        assert member.agent_config["strict"] is True


class TestTeamEvent:
    """Tests for TeamEvent."""

    def test_event_creation_minimal(self) -> None:
        """TeamEvent should be created with just a type."""
        event = TeamEvent(type="agent_start")

        assert event.type == "agent_start"
        assert event.sender is None
        assert event.recipient is None
        assert event.content == ""
        assert event.round == 0
        assert event.timestamp  # Auto-generated
        assert event.metadata == {}

    def test_event_creation_full(self) -> None:
        """TeamEvent should accept all fields."""
        event = TeamEvent(
            type="task_completed",
            sender="worker-1",
            recipient="coordinator",
            content="Task finished successfully",
            round=2,
            metadata={"duration_ms": 1500, "tokens": 200},
        )

        assert event.type == "task_completed"
        assert event.sender == "worker-1"
        assert event.recipient == "coordinator"
        assert event.content == "Task finished successfully"
        assert event.round == 2
        assert event.metadata["duration_ms"] == 1500

    def test_event_auto_timestamp(self) -> None:
        """TeamEvent should auto-generate timestamp."""
        event = TeamEvent(type="test")

        assert isinstance(event.timestamp, datetime)

    def test_event_serialization(self) -> None:
        """TeamEvent should serialize to dict."""
        event = TeamEvent(
            type="message_sent",
            sender="a",
            recipient="b",
            round=1,
        )

        data = event.model_dump()

        assert data["type"] == "message_sent"
        assert data["sender"] == "a"
        assert data["round"] == 1


class TestAgentOutput:
    """Tests for AgentOutput."""

    def test_output_creation_minimal(self) -> None:
        """AgentOutput should be created with required fields."""
        output = AgentOutput(
            agent_name="worker-1",
            role=TeamRole.WORKER,
            output="Task completed successfully",
        )

        assert output.agent_name == "worker-1"
        assert output.role == TeamRole.WORKER
        assert output.output == "Task completed successfully"
        assert output.tokens == 0  # Default
        assert output.cost == 0.0  # Default
        assert output.duration_ms == 0  # Default

    def test_output_creation_full(self) -> None:
        """AgentOutput should accept all fields."""
        output = AgentOutput(
            agent_name="research-agent",
            role=TeamRole.SPECIALIST,
            output="Research findings: ...",
            tokens=1500,
            cost=0.03,
            duration_ms=2500,
        )

        assert output.agent_name == "research-agent"
        assert output.role == TeamRole.SPECIALIST
        assert output.tokens == 1500
        assert output.cost == 0.03
        assert output.duration_ms == 2500

    def test_output_serialization(self) -> None:
        """AgentOutput should serialize to dict."""
        output = AgentOutput(
            agent_name="worker",
            role=TeamRole.WORKER,
            output="done",
            tokens=100,
        )

        data = output.model_dump()

        assert data["agent_name"] == "worker"
        assert data["role"] == "worker"
        assert data["tokens"] == 100

    def test_output_deserialization(self) -> None:
        """AgentOutput should deserialize from dict."""
        data = {
            "agent_name": "specialist",
            "role": "specialist",
            "output": "analysis complete",
            "tokens": 500,
            "cost": 0.01,
            "duration_ms": 1000,
        }

        output = AgentOutput.model_validate(data)

        assert output.agent_name == "specialist"
        assert output.role == TeamRole.SPECIALIST
        assert output.tokens == 500


class TestTeamResult:
    """Tests for TeamResult."""

    def test_result_creation_minimal(self) -> None:
        """TeamResult should be created with just output."""
        result = TeamResult(output="Final team result")

        assert result.output == "Final team result"
        assert result.agent_outputs == {}
        assert result.messages == []
        assert result.total_cost == 0.0
        assert result.total_tokens == 0
        assert result.rounds == 0
        assert result.duration_ms == 0
        assert result.strategy == ""
        assert result.team_name == ""

    def test_result_creation_full(self) -> None:
        """TeamResult should accept all fields."""
        output1 = AgentOutput(
            agent_name="worker-1",
            role=TeamRole.WORKER,
            output="Part 1",
            tokens=100,
            cost=0.002,
        )
        output2 = AgentOutput(
            agent_name="worker-2",
            role=TeamRole.WORKER,
            output="Part 2",
            tokens=150,
            cost=0.003,
        )

        msg = AgentMessage(
            sender="coordinator",
            recipient="worker-1",
            message_type=MessageType.TASK,
            content="Start work",
        )

        result = TeamResult(
            output="Combined result from all workers",
            agent_outputs={"worker-1": output1, "worker-2": output2},
            messages=[msg],
            total_cost=0.15,
            total_tokens=5000,
            rounds=3,
            duration_ms=5500,
            strategy="coordinator",
            team_name="research-team",
        )

        assert result.output == "Combined result from all workers"
        assert len(result.agent_outputs) == 2
        assert "worker-1" in result.agent_outputs
        assert len(result.messages) == 1
        assert result.total_cost == 0.15
        assert result.total_tokens == 5000
        assert result.rounds == 3
        assert result.strategy == "coordinator"
        assert result.team_name == "research-team"

    def test_result_with_empty_collections(self) -> None:
        """TeamResult should handle empty collections."""
        result = TeamResult(
            output="test",
            agent_outputs={},
            messages=[],
        )

        assert result.agent_outputs == {}
        assert result.messages == []

    def test_result_serialization(self) -> None:
        """TeamResult should serialize to dict."""
        result = TeamResult(
            output="final",
            total_cost=0.1,
            total_tokens=1000,
            strategy="sequential",
        )

        data = result.model_dump()

        assert data["output"] == "final"
        assert data["total_cost"] == 0.1
        assert data["strategy"] == "sequential"

    def test_result_deserialization(self) -> None:
        """TeamResult should deserialize from dict."""
        data = {
            "output": "result",
            "agent_outputs": {},
            "messages": [],
            "total_cost": 0.05,
            "total_tokens": 500,
            "rounds": 2,
            "duration_ms": 3000,
            "strategy": "debate",
            "team_name": "team-alpha",
        }

        result = TeamResult.model_validate(data)

        assert result.output == "result"
        assert result.strategy == "debate"
        assert result.team_name == "team-alpha"

    def test_result_round_trip(self) -> None:
        """TeamResult should survive serialization round-trip."""
        output = AgentOutput(
            agent_name="agent",
            role=TeamRole.WORKER,
            output="done",
        )

        msg = AgentMessage(
            sender="a",
            message_type=MessageType.TASK,
            content="go",
        )

        original = TeamResult(
            output="final",
            agent_outputs={"agent": output},
            messages=[msg],
            total_cost=0.02,
            total_tokens=200,
            rounds=1,
            strategy="round_robin",
        )

        data = original.model_dump()
        restored = TeamResult.model_validate(data)

        assert restored.output == original.output
        assert restored.total_cost == original.total_cost
        assert restored.strategy == original.strategy
        assert len(restored.agent_outputs) == 1
        assert len(restored.messages) == 1
