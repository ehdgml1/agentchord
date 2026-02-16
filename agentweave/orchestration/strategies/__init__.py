"""Orchestration strategies for multi-agent coordination."""
from __future__ import annotations

from agentweave.orchestration.strategies.base import BaseStrategy
from agentweave.orchestration.strategies.coordinator import CoordinatorStrategy
from agentweave.orchestration.strategies.debate import DebateStrategy
from agentweave.orchestration.strategies.map_reduce import MapReduceStrategy
from agentweave.orchestration.strategies.round_robin import RoundRobinStrategy

__all__ = [
    "BaseStrategy",
    "CoordinatorStrategy",
    "DebateStrategy",
    "MapReduceStrategy",
    "RoundRobinStrategy",
]
