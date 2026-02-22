"""MCP Client implementation.

This module provides a client for connecting to MCP servers
and invoking their tools.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, AsyncIterator

from agentchord.protocols.mcp.types import MCPServerConfig, MCPTool, MCPToolResult

if TYPE_CHECKING:
    pass


@dataclass
class MCPConnection:
    """Represents a connection to an MCP server."""

    server_id: str
    config: MCPServerConfig
    tools: list[MCPTool] = field(default_factory=list)
    _session: Any = None
    _read_stream: Any = None
    _write_stream: Any = None


class MCPClient:
    """Client for connecting to and interacting with MCP servers.

    MCPClient manages connections to multiple MCP servers and provides
    a unified interface to discover and call their tools.

    Example:
        >>> async with MCPClient() as mcp:
        ...     await mcp.connect("npx", ["-y", "@anthropic/mcp-server-github"])
        ...     tools = await mcp.list_tools()
        ...     result = await mcp.call_tool("create_issue", {"title": "Bug"})

    Note:
        Requires the `mcp` package: pip install agentchord[mcp]
    """

    def __init__(self) -> None:
        """Initialize MCP client."""
        self._connections: dict[str, MCPConnection] = {}
        self._tool_registry: dict[str, str] = {}  # tool_name -> server_id
        self._started = False
        self._mcp_available = self._check_mcp_available()

    def _check_mcp_available(self) -> bool:
        """Check if MCP package is installed."""
        try:
            import mcp  # noqa: F401
            return True
        except ImportError:
            return False

    def _require_mcp(self) -> None:
        """Raise error if MCP is not available."""
        if not self._mcp_available:
            raise ImportError(
                "MCP package not installed. "
                "Install with: pip install agentchord[mcp]"
            )

    async def __aenter__(self) -> MCPClient:
        """Enter async context."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context and cleanup connections."""
        await self.disconnect_all()

    async def connect(
        self,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        server_id: str | None = None,
    ) -> list[MCPTool]:
        """Connect to an MCP server.

        Args:
            command: Command to execute (e.g., 'npx', 'uvx').
            args: Command arguments (e.g., ['-y', '@anthropic/mcp-server-github']).
            env: Environment variables for the server process.
            server_id: Optional identifier for this server.

        Returns:
            List of tools provided by the server.

        Raises:
            ImportError: If MCP package is not installed.
            ConnectionError: If connection fails.

        Example:
            >>> tools = await mcp.connect(
            ...     "npx", ["-y", "@anthropic/mcp-server-filesystem"],
            ...     env={"ALLOWED_DIRECTORIES": "/tmp"}
            ... )
        """
        self._require_mcp()

        config = MCPServerConfig(
            command=command,
            args=args or [],
            env=env or {},
            server_id=server_id,
        )

        actual_server_id = config.get_server_id()

        if actual_server_id in self._connections:
            return self._connections[actual_server_id].tools

        connection = await self._create_connection(config, actual_server_id)
        self._connections[actual_server_id] = connection

        # Register tools in global registry
        for tool in connection.tools:
            self._tool_registry[tool.name] = actual_server_id

        return connection.tools

    async def _create_connection(
        self,
        config: MCPServerConfig,
        server_id: str,
    ) -> MCPConnection:
        """Create a new MCP connection."""
        from mcp import types
        from mcp.client.session import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client

        server_params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env or None,
        )

        connection = MCPConnection(server_id=server_id, config=config)

        # Create the connection (simplified - in production would need proper lifecycle)
        read_stream, write_stream = await stdio_client(server_params).__aenter__()
        connection._read_stream = read_stream
        connection._write_stream = write_stream

        session = ClientSession(read_stream, write_stream)
        await session.__aenter__()
        await session.initialize()
        connection._session = session

        # Fetch available tools
        tools_response = await session.list_tools()
        connection.tools = [
            MCPTool(
                name=t.name,
                description=t.description or "",
                input_schema=t.inputSchema if hasattr(t, "inputSchema") else {},
                server_id=server_id,
            )
            for t in tools_response.tools
        ]

        return connection

    async def disconnect(self, server_id: str) -> None:
        """Disconnect from a specific MCP server.

        Args:
            server_id: ID of the server to disconnect.
        """
        if server_id not in self._connections:
            return

        connection = self._connections[server_id]

        # Remove tools from registry
        for tool in connection.tools:
            if tool.name in self._tool_registry:
                del self._tool_registry[tool.name]

        # Close session
        if connection._session:
            await connection._session.__aexit__(None, None, None)

        del self._connections[server_id]

    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers."""
        server_ids = list(self._connections.keys())
        for server_id in server_ids:
            await self.disconnect(server_id)

    async def list_tools(self, server_id: str | None = None) -> list[MCPTool]:
        """List available tools.

        Args:
            server_id: If provided, only list tools from this server.

        Returns:
            List of available MCPTool objects.
        """
        if server_id:
            connection = self._connections.get(server_id)
            return connection.tools if connection else []

        all_tools = []
        for connection in self._connections.values():
            all_tools.extend(connection.tools)
        return all_tools

    def get_tool(self, name: str) -> MCPTool | None:
        """Get a tool by name.

        Args:
            name: Tool name.

        Returns:
            MCPTool if found, None otherwise.
        """
        server_id = self._tool_registry.get(name)
        if not server_id:
            return None

        connection = self._connections.get(server_id)
        if not connection:
            return None

        for tool in connection.tools:
            if tool.name == name:
                return tool
        return None

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> MCPToolResult:
        """Call an MCP tool by name.

        Args:
            name: Name of the tool to call.
            arguments: Arguments to pass to the tool.

        Returns:
            MCPToolResult containing the tool's output.

        Raises:
            ValueError: If tool is not found.
            RuntimeError: If tool call fails.

        Example:
            >>> result = await mcp.call_tool(
            ...     "read_file",
            ...     {"path": "/tmp/example.txt"}
            ... )
            >>> print(result.content)
        """
        self._require_mcp()

        from mcp import types

        server_id = self._tool_registry.get(name)
        if not server_id:
            available = list(self._tool_registry.keys())
            raise ValueError(
                f"Tool '{name}' not found. Available tools: {available}"
            )

        connection = self._connections.get(server_id)
        if not connection or not connection._session:
            raise RuntimeError(f"No active connection for server '{server_id}'")

        result = await connection._session.call_tool(name, arguments or {})

        # Extract content
        content_parts = []
        for content_block in result.content:
            if isinstance(content_block, types.TextContent):
                content_parts.append(content_block.text)
            elif hasattr(content_block, "text"):
                content_parts.append(str(content_block.text))

        return MCPToolResult(
            content="\n".join(content_parts),
            is_error=result.isError if hasattr(result, "isError") else False,
            raw_content=list(result.content),
        )

    @property
    def connected_servers(self) -> list[str]:
        """Get list of connected server IDs."""
        return list(self._connections.keys())

    @property
    def available_tools(self) -> list[str]:
        """Get list of available tool names."""
        return list(self._tool_registry.keys())

    def __repr__(self) -> str:
        servers = len(self._connections)
        tools = len(self._tool_registry)
        return f"MCPClient(servers={servers}, tools={tools})"
