"""WebSocket endpoint for debug mode streaming.

Phase 2 Task:
- WebSocket handler for debug execution
- Connection management
- Event streaming
- Inactivity timeout (10 minutes)
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import jwt as pyjwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.auth.jwt import JWT_SECRET, JWT_ALGORITHM
from app.core.debug_executor import DebugExecutor, DebugSession, DebugEvent
from app.dtos.debug import DebugStartRequest, DebugCommand


router = APIRouter(tags=["debug"])


class DebugConnectionManager:
    """Manages active debug WebSocket connections.

    Ensures only one debug session per workflow and handles cleanup.
    """

    def __init__(self):
        """Initialize connection manager."""
        self.active_sessions: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        """Connect and register a new debug session.

        Args:
            session_id: Unique session identifier.
            websocket: WebSocket connection.
        """
        await websocket.accept()
        self.active_sessions[session_id] = websocket

    def disconnect(self, session_id: str):
        """Disconnect and unregister debug session.

        Args:
            session_id: Session identifier to disconnect.
        """
        self.active_sessions.pop(session_id, None)

    async def send_event(self, session_id: str, event: dict[str, Any]):
        """Send event to specific debug session.

        Args:
            session_id: Session identifier.
            event: Event data to send.
        """
        if ws := self.active_sessions.get(session_id):
            try:
                await ws.send_json(event)
            except Exception:
                # Connection might be closed
                self.disconnect(session_id)


# Global connection manager instance
manager = DebugConnectionManager()


def _verify_token(token: str | None) -> dict | None:
    """Verify JWT token without closing websocket.

    Args:
        token: JWT token string.

    Returns:
        Decoded token payload or None if verification fails.
    """
    if not token:
        return None

    try:
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception:
        return None


@router.websocket("/ws/debug/{workflow_id}")
async def debug_workflow(
    websocket: WebSocket,
    workflow_id: str,
    token: str | None = None,
):
    """WebSocket endpoint for debug mode execution.

    Protocol:
        Client sends:
            - {"action": "auth", "token": "..."} (FIRST MESSAGE for authentication)
            - {"action": "start", "input": "...", "breakpoints": ["node1", "node2"]}
            - {"action": "continue"}
            - {"action": "step"}
            - {"action": "stop"}

        Server sends (DebugEvent):
            - {"type": "node_start", "node_id": "...", "data": {...}}
            - {"type": "breakpoint", "node_id": "...", "data": {...}}
            - {"type": "node_complete", "node_id": "...", "data": {...}}
            - {"type": "complete", "data": {...}}
            - {"type": "error", "data": {"message": "..."}}
            - {"type": "timeout"}

    Args:
        websocket: WebSocket connection.
        workflow_id: Workflow to debug.
        token: JWT authentication token (deprecated query parameter, use first-message auth).
    """
    # Accept connection first (auth happens via first message)
    await websocket.accept()

    # Wait for authentication message (10 second timeout)
    user_payload: dict | None = None
    try:
        first_message = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        data = json.loads(first_message)

        if data.get("action") == "auth":
            # First-message authentication (preferred)
            auth_token = data.get("token")
            user_payload = _verify_token(auth_token)
        else:
            # Fallback to query parameter for backward compatibility
            user_payload = _verify_token(token)

            # If no query param either, this is an error
            if user_payload is None:
                await websocket.close(code=4001, reason="First message must be authentication")
                return

            # Re-process the first message as a command (since it wasn't auth)
            # Store it to process after session setup
            first_command = data
    except asyncio.TimeoutError:
        await websocket.close(code=4001, reason="Authentication timeout")
        return
    except json.JSONDecodeError:
        await websocket.close(code=4001, reason="Invalid JSON in authentication message")
        return

    if user_payload is None:
        await websocket.close(code=4001, reason="Invalid authentication token")
        return

    session_id = f"debug-{workflow_id}"
    # Don't call manager.connect() here - we already accepted the websocket
    manager.active_sessions[session_id] = websocket

    # Create debug session
    session = DebugSession()
    debug_task: asyncio.Task | None = None

    # Check if we have a buffered command from backward-compat fallback
    buffered_command = locals().get('first_command')

    try:
        # Wait for start command
        while True:
            # Process buffered command first (if using query param auth)
            if buffered_command is not None:
                data = buffered_command
                buffered_command = None  # Clear buffer
            else:
                try:
                    # Receive message with 10-minute inactivity timeout
                    message = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=600.0  # 10 minutes
                    )
                except asyncio.TimeoutError:
                    # Send timeout event
                    await websocket.send_json({
                        "type": "timeout",
                        "data": {"message": "Session timed out after 10 minutes of inactivity"}
                    })
                    break

                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": "Invalid JSON"}
                    })
                    continue

            action = data.get("action")

            # Skip "auth" action if received again (already authenticated)
            if action == "auth":
                continue

            if action == "start":
                # Parse start request
                try:
                    start_req = DebugStartRequest(**data)
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": f"Invalid start request: {str(e)}"}
                    })
                    continue

                # Set breakpoints
                session._breakpoints = set(start_req.breakpoints)

                # Start debug execution in background
                debug_task = asyncio.create_task(
                    _run_debug_workflow(
                        websocket,
                        session,
                        workflow_id,
                        start_req.input,
                        user_payload,
                    )
                )

            elif action == "continue":
                # Resume execution from breakpoint
                session.continue_()

            elif action == "step":
                # Step to next node
                session.step()

            elif action == "stop":
                # Stop debug execution
                session.stop()
                if debug_task and not debug_task.done():
                    debug_task.cancel()
                break

            else:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": f"Unknown action: {action}"}
                })

            # Check if debug task completed
            if debug_task and debug_task.done():
                break

    except WebSocketDisconnect:
        # Client disconnected
        pass
    except Exception as e:
        # Unexpected error
        try:
            await websocket.send_json({
                "type": "error",
                "data": {"message": f"Server error: {str(e)}"}
            })
        except Exception:
            pass
    finally:
        # Cleanup
        session.stop()
        if debug_task and not debug_task.done():
            debug_task.cancel()
            try:
                await debug_task
            except asyncio.CancelledError:
                pass
        manager.disconnect(session_id)


async def _run_debug_workflow(
    websocket: WebSocket,
    session: DebugSession,
    workflow_id: str,
    workflow_input: str,
    user_payload: dict,
):
    """Run debug workflow and stream events.

    Args:
        websocket: WebSocket for sending events.
        session: Debug session.
        workflow_id: Workflow ID.
        workflow_input: Workflow input string.
        user_payload: Authenticated user's JWT payload.
    """
    try:
        import json as json_mod

        from sqlalchemy import select

        from app.db.database import AsyncSessionLocal
        from app.models.workflow import Workflow

        # Load workflow from database
        async with AsyncSessionLocal() as db_session:
            result = await db_session.execute(
                select(Workflow).where(Workflow.id == workflow_id)
            )
            workflow = result.scalar_one_or_none()

        if not workflow:
            await websocket.send_json({
                "type": "error",
                "data": {"message": f"Workflow {workflow_id} not found"},
            })
            return

        # Verify ownership (IDOR protection)
        user_id = user_payload.get("sub")
        user_role = user_payload.get("role")

        # Check ownership: allow if admin, or if owner_id is None (legacy), or if user owns it
        if workflow.owner_id is not None and user_role != "admin" and workflow.owner_id != user_id:
            await websocket.close(code=4003, reason="Not authorized to debug this workflow")
            return

        workflow_data = {
            "id": workflow.id,
            "name": workflow.name,
            "nodes": (
                json_mod.loads(workflow.nodes)
                if isinstance(workflow.nodes, str)
                else workflow.nodes
            ),
            "edges": (
                json_mod.loads(workflow.edges)
                if isinstance(workflow.edges, str)
                else workflow.edges
            ),
        }

        # Create debug executor
        executor = DebugExecutor(workflow_data, session)

        # Stream debug events
        async for event in executor.run_debug():
            # Convert event to dict for JSON serialization
            event_dict = {
                "type": event.type.value,
                "node_id": event.node_id,
                "data": event.data,
                "timestamp": event.timestamp,
            }
            await websocket.send_json(event_dict)

    except asyncio.CancelledError:
        # Task was cancelled
        pass
    except Exception as e:
        # Send error event
        try:
            await websocket.send_json({
                "type": "error",
                "data": {"message": str(e)}
            })
        except Exception:
            pass
