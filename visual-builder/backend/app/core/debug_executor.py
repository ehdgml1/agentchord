"""Debug mode workflow executor with step-through capability."""
import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator, Any
from datetime import UTC, datetime


class DebugEventType(Enum):
    """Debug event types."""

    BREAKPOINT = "breakpoint"
    NODE_START = "node_start"
    NODE_COMPLETE = "node_complete"
    COMPLETE = "complete"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class DebugEvent:
    """Debug execution event."""

    type: DebugEventType
    node_id: str | None = None
    data: dict | None = field(
        default_factory=dict
    )
    timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )


class DebugSession:
    """Manages debug session state."""

    INACTIVITY_TIMEOUT = 600

    def __init__(self):
        """Initialize debug session."""
        self._command_queue = asyncio.Queue()
        self._stopped = False
        self._last_activity = datetime.now(UTC)
        self._breakpoints: set[str] = set()

    async def wait_for_command(
        self,
        timeout: float | None = None,
    ) -> str:
        """Wait for debug command.

        Args:
            timeout: Wait timeout

        Returns:
            Command: continue, step, or stop

        Raises:
            asyncio.TimeoutError: Timeout
        """
        if timeout is None:
            timeout = self.INACTIVITY_TIMEOUT

        try:
            cmd = await asyncio.wait_for(
                self._command_queue.get(),
                timeout=timeout,
            )
            self._last_activity = datetime.now(UTC)
            return cmd
        except asyncio.TimeoutError:
            self._stopped = True
            raise

    def continue_(self):
        """Continue execution."""
        self._command_queue.put_nowait("continue")

    def step(self):
        """Step to next node."""
        self._command_queue.put_nowait("step")

    def stop(self):
        """Stop execution."""
        self._stopped = True
        self._command_queue.put_nowait("stop")

    @property
    def is_stopped(self) -> bool:
        """Check if stopped."""
        return self._stopped


class DebugExecutor:
    """Step-through workflow executor."""

    def __init__(
        self,
        workflow_data: dict[str, Any],
        session: DebugSession,
    ):
        """Initialize executor.

        Args:
            workflow_data: Workflow definition
            session: Debug session
        """
        self.workflow_data = workflow_data
        self.session = session
        self.current_node_idx = 0
        self._results: dict[str, Any] = {}

    async def run_debug(
        self,
    ) -> AsyncIterator[DebugEvent]:
        """Run workflow in debug mode.

        Yields:
            Debug events
        """
        nodes = self.workflow_data.get("nodes", [])

        try:
            for idx, node in enumerate(nodes):
                if self.session.is_stopped:
                    break

                self.current_node_idx = idx
                node_id = node.get("id", f"node_{idx}")

                # Check if this is a breakpoint
                is_breakpoint = node_id in self.session._breakpoints

                if is_breakpoint:
                    # Emit breakpoint event
                    yield DebugEvent(
                        type=DebugEventType.BREAKPOINT,
                        node_id=node_id,
                        data={
                            "node": node,
                            "index": idx,
                            "total": len(nodes),
                        },
                    )

                    # Wait for user command
                    try:
                        cmd = await self.session.wait_for_command()
                    except asyncio.TimeoutError:
                        yield DebugEvent(
                            type=DebugEventType.TIMEOUT,
                            node_id=node_id,
                            data={"message": "Inactivity timeout"},
                        )
                        break

                    if cmd == "stop" or self.session.is_stopped:
                        break

                # Emit node start event
                yield DebugEvent(
                    type=DebugEventType.NODE_START,
                    node_id=node_id,
                    data={"node": node},
                )

                # Execute node
                try:
                    result = await self._execute_node(node)
                except Exception as e:
                    yield DebugEvent(
                        type=DebugEventType.ERROR,
                        node_id=node_id,
                        data={
                            "error": str(e),
                            "type": type(e).__name__,
                        },
                    )
                    break

                # Emit node complete event
                yield DebugEvent(
                    type=DebugEventType.NODE_COMPLETE,
                    node_id=node_id,
                    data={
                        "result": result,
                        "node": node,
                    },
                )

            if not self.session.is_stopped:
                yield DebugEvent(
                    type=DebugEventType.COMPLETE,
                    data={
                        "results": self._results,
                        "nodes_executed": self.current_node_idx + 1,
                    },
                )

        except Exception as e:
            yield DebugEvent(
                type=DebugEventType.ERROR,
                node_id=nodes[self.current_node_idx].get("id") if self.current_node_idx < len(nodes) else None,
                data={
                    "error": str(e),
                    "type": type(e).__name__,
                },
            )

    async def _execute_node(
        self,
        node: dict[str, Any],
    ) -> Any:
        """Execute single node.

        Args:
            node: Node definition

        Returns:
            Node result
        """
        await asyncio.sleep(0.1)

        node_id = node.get("id")
        node_type = node.get("type", "unknown")

        result = {
            "node_id": node_id,
            "type": node_type,
            "status": "success",
            "output": f"Executed {node_type}",
        }

        self._results[node_id] = result
        return result
