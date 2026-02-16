"""MCP API endpoints.

Phase 0 MVP:
- List connected MCP servers
- Connect/disconnect servers
- List tools from server
- Health check
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from ..auth import get_current_user
from ..auth.jwt import User
from ..core.rbac import require_permission
from ..core.mcp_manager import (
    MCPServerConfig,
    MCPManagerError,
    MCPCommandNotAllowedError,
    MCPServerNotConnectedError,
)
from ..dtos.mcp import (
    MCPServerCreate,
    MCPServerResponse,
    MCPToolResponse,
    MCPHealthResponse,
)

router = APIRouter(prefix="/api/mcp/servers", tags=["mcp"])


@router.get("", response_model=list[MCPServerResponse])
@require_permission("workflow:read")
async def list_servers(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
):
    """List connected MCP servers.

    Args:
        request: FastAPI request object.
        user: Current authenticated user.

    Returns:
        List of connected MCP servers.
    """
    mcp_manager = request.app.state.mcp_manager
    configs = mcp_manager.list_servers()

    results = []
    for config in configs:
        status_info = mcp_manager.get_server_status(config.id)
        tools = mcp_manager.list_tools(config.id)

        status = "connected" if status_info["connected"] else "disconnected"
        if status_info["circuit_state"] == "open":
            status = "error"

        results.append(
            MCPServerResponse(
                id=config.id,
                name=config.name,
                command=config.command,
                args=config.args,
                description=config.description,
                status=status,
                tool_count=status_info["tool_count"],
                last_connected_at=None,
                tools=[
                    MCPToolResponse(
                        name=t.name,
                        description=t.description,
                        input_schema=t.input_schema,
                        server_id=t.server_id,
                    )
                    for t in tools
                ],
            )
        )
    return results


@router.post("", response_model=MCPServerResponse, status_code=201)
@require_permission("workflow:write")
async def connect_server(
    request: Request,
    server: MCPServerCreate,
    user: Annotated[User, Depends(get_current_user)],
):
    """Connect to MCP server.

    Args:
        request: FastAPI request object.
        server: Server connection configuration.
        user: Current authenticated user.

    Returns:
        Connected server details.

    Raises:
        400: Invalid server configuration or connection failed.
    """
    mcp_manager = request.app.state.mcp_manager

    # Create config with unique ID
    config = MCPServerConfig(
        id=str(uuid.uuid4()),
        name=server.name,
        command=server.command,
        args=server.args,
        env=server.env or None,
        description=server.description,
    )

    try:
        await mcp_manager.connect(config)
    except MCPCommandNotAllowedError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "COMMAND_NOT_ALLOWED",
                    "message": str(e),
                }
            },
        )
    except MCPManagerError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "CONNECTION_FAILED",
                    "message": str(e),
                }
            },
        )

    # Get actual status after connection
    status_info = mcp_manager.get_server_status(config.id)
    tools = mcp_manager.list_tools(config.id)

    now = datetime.now(UTC).replace(tzinfo=None).isoformat()

    return MCPServerResponse(
        id=config.id,
        name=config.name,
        command=config.command,
        args=config.args,
        description=server.description,
        status="connected",
        tool_count=status_info["tool_count"],
        last_connected_at=now,
        tools=[
            MCPToolResponse(
                name=t.name,
                description=t.description,
                input_schema=t.input_schema,
                server_id=t.server_id,
            )
            for t in tools
        ],
    )


@router.delete("/{server_id}", status_code=204)
@require_permission("workflow:write")
async def disconnect_server(
    request: Request,
    server_id: str,
    user: Annotated[User, Depends(get_current_user)],
):
    """Disconnect MCP server.

    Args:
        request: FastAPI request object.
        server_id: Server ID to disconnect.
        user: Current authenticated user.

    Raises:
        404: Server not found.
    """
    mcp_manager = request.app.state.mcp_manager

    if server_id not in mcp_manager._configs:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "SERVER_NOT_FOUND",
                    "message": f"MCP server '{server_id}' not found",
                }
            },
        )

    await mcp_manager.disconnect(server_id)


@router.get("/{server_id}/tools", response_model=list[MCPToolResponse])
@require_permission("workflow:read")
async def list_server_tools(
    request: Request,
    server_id: str,
    user: Annotated[User, Depends(get_current_user)],
):
    """List tools available on MCP server.

    Args:
        request: FastAPI request object.
        server_id: Server ID.
        user: Current authenticated user.

    Returns:
        List of available tools.

    Raises:
        404: Server not found.
    """
    mcp_manager = request.app.state.mcp_manager

    if server_id not in mcp_manager._configs:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "SERVER_NOT_FOUND",
                    "message": f"MCP server '{server_id}' not found",
                }
            },
        )

    tools = mcp_manager.list_tools(server_id)

    return [
        MCPToolResponse(
            name=tool.name,
            description=tool.description,
            input_schema=tool.input_schema,
            server_id=tool.server_id,
        )
        for tool in tools
    ]


@router.get("/{server_id}/health", response_model=MCPHealthResponse)
@require_permission("workflow:read")
async def check_server_health(
    request: Request,
    server_id: str,
    user: Annotated[User, Depends(get_current_user)],
):
    """Check MCP server health.

    Args:
        request: FastAPI request object.
        server_id: Server ID.
        user: Current authenticated user.

    Returns:
        Server health status.

    Raises:
        404: Server not found.
    """
    mcp_manager = request.app.state.mcp_manager

    if server_id not in mcp_manager._configs:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "SERVER_NOT_FOUND",
                    "message": f"MCP server '{server_id}' not found",
                }
            },
        )

    start_time = time.time()
    is_healthy = await mcp_manager.health_check(server_id)
    latency_ms = int((time.time() - start_time) * 1000)

    server_status = mcp_manager.get_server_status(server_id)

    if is_healthy:
        status = "healthy"
        message = f"Server is healthy (circuit: {server_status['circuit_state']})"
    else:
        status = "unhealthy"
        message = f"Server health check failed (circuit: {server_status['circuit_state']})"

    return MCPHealthResponse(
        server_id=server_id,
        status=status,
        message=message,
        latency_ms=latency_ms,
    )
