"""MCP Server connection and tool execution manager.

Phase -1 아키텍처 스파이크:
- 명령어 인젝션 방지 (허용목록)
- 경로 탐색 방지
- CircuitBreaker 통합
- 리소스 제한 준비
"""

from __future__ import annotations

import asyncio
import re
import shutil
from dataclasses import dataclass, field
from typing import Any

# AgentWeave resilience imports
import sys
from pathlib import Path
# Add agentweave package to path (parent of visual-builder)
_agentweave_root = str(Path(__file__).resolve().parent.parent.parent.parent.parent)
if _agentweave_root not in sys.path:
    sys.path.insert(0, _agentweave_root)
from agentweave.resilience.circuit_breaker import CircuitBreaker, CircuitOpenError


# 허용된 MCP 명령어 화이트리스트
ALLOWED_MCP_COMMANDS: dict[str, str | None] = {
    "npx": shutil.which("npx"),
    "node": shutil.which("node"),
    "python": shutil.which("python"),
    "python3": shutil.which("python3"),
    "uvx": shutil.which("uvx"),
}

# 차단된 인자 (코드 인젝션 방지)
BLOCKED_ARGS: set[str] = {
    "--eval", "-e",      # JavaScript/Python eval
    "--exec",            # 실행
    "-c",                # Python -c
    "--import",          # 동적 import
}

# 환경변수 이름 패턴
ENV_VAR_PATTERN = re.compile(r'^[A-Z_][A-Z0-9_]*$')


class MCPManagerError(Exception):
    """MCP Manager related errors."""
    pass


class MCPCommandNotAllowedError(MCPManagerError):
    """Command not in allowed list."""
    def __init__(self, command: str) -> None:
        super().__init__(
            f"Command '{command}' not allowed. "
            f"Allowed: {list(ALLOWED_MCP_COMMANDS.keys())}"
        )
        self.command = command


class MCPServerNotConnectedError(MCPManagerError):
    """MCP server not connected."""
    def __init__(self, server_id: str) -> None:
        super().__init__(f"MCP server '{server_id}' not connected")
        self.server_id = server_id


class MCPToolNotFoundError(MCPManagerError):
    """MCP tool not found."""
    def __init__(self, server_id: str, tool_name: str) -> None:
        super().__init__(f"Tool '{tool_name}' not found in server '{server_id}'")
        self.server_id = server_id
        self.tool_name = tool_name


@dataclass
class MCPServerConfig:
    """MCP 서버 설정 (보안 검증 포함).

    Attributes:
        id: Unique server identifier.
        name: Human-readable server name.
        command: Executable command (must be in ALLOWED_MCP_COMMANDS).
        args: Command arguments.
        env: Environment variables for the server process.
        description: Optional server description.
    """
    id: str
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] | None = None
    description: str = ""

    def __post_init__(self) -> None:
        """Validate configuration security."""
        self._validate_command()
        self._validate_args()
        self._validate_env()

    def _validate_command(self) -> None:
        """Validate command is in allowed list."""
        if self.command not in ALLOWED_MCP_COMMANDS:
            raise MCPCommandNotAllowedError(self.command)

        # 명령어가 시스템에 존재하는지 확인
        if ALLOWED_MCP_COMMANDS[self.command] is None:
            raise MCPManagerError(
                f"Command '{self.command}' not found in system PATH"
            )

    def _validate_args(self) -> None:
        """Validate arguments for security risks."""
        for arg in self.args:
            # 차단된 인자 체크
            if arg in BLOCKED_ARGS:
                raise MCPManagerError(
                    f"Argument '{arg}' is blocked for security reasons"
                )

            # 경로 탐색 방지
            if ".." in arg:
                raise MCPManagerError(
                    f"Path traversal detected in argument: {arg}"
                )

            # 절대 경로 방지 (특정 안전한 경로 제외)
            if arg.startswith("/") and not self._is_safe_path(arg):
                raise MCPManagerError(
                    f"Absolute path not allowed: {arg}"
                )

    def _validate_env(self) -> None:
        """Validate environment variable names."""
        if not self.env:
            return

        for key in self.env.keys():
            if not ENV_VAR_PATTERN.match(key):
                raise MCPManagerError(
                    f"Invalid environment variable name: {key}"
                )

    @staticmethod
    def _is_safe_path(path: str) -> bool:
        """Check if absolute path is in safe list."""
        safe_prefixes = [
            "/tmp/",
            "/var/tmp/",
        ]
        return any(path.startswith(prefix) for prefix in safe_prefixes)


@dataclass
class MCPTool:
    """MCP Tool information.

    Attributes:
        server_id: ID of the server providing this tool.
        name: Tool name.
        description: Tool description.
        input_schema: JSON schema for tool inputs.
    """
    server_id: str
    name: str
    description: str
    input_schema: dict[str, Any]


class MCPManager:
    """MCP 서버 연결 및 Tool 실행 관리.

    Features:
        - Command injection prevention
        - Circuit breaker per server
        - Timeout protection
        - Connection health tracking

    Example:
        >>> manager = MCPManager()
        >>> config = MCPServerConfig(
        ...     id="fetch",
        ...     name="Fetch",
        ...     command="npx",
        ...     args=["-y", "@anthropic/mcp-fetch"],
        ... )
        >>> await manager.connect(config)
        >>> result = await manager.execute_tool("fetch", "fetch", {"url": "..."})
    """

    # Circuit breaker settings
    CIRCUIT_FAILURE_THRESHOLD = 3
    CIRCUIT_TIMEOUT = 60.0

    # Execution timeout
    DEFAULT_TOOL_TIMEOUT = 30.0

    def __init__(self) -> None:
        """Initialize MCP manager."""
        self._sessions: dict[str, Any] = {}  # server_id -> ClientSession
        self._tools: dict[str, list[MCPTool]] = {}  # server_id -> tools
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._configs: dict[str, MCPServerConfig] = {}
        self._client_contexts: dict[str, Any] = {}  # server_id -> client context manager
        self._session_contexts: dict[str, Any] = {}  # server_id -> session context manager

    def _get_or_create_breaker(self, server_id: str) -> CircuitBreaker:
        """Get or create circuit breaker for server."""
        if server_id not in self._circuit_breakers:
            self._circuit_breakers[server_id] = CircuitBreaker(
                failure_threshold=self.CIRCUIT_FAILURE_THRESHOLD,
                timeout=self.CIRCUIT_TIMEOUT,
            )
        return self._circuit_breakers[server_id]

    async def connect(self, config: MCPServerConfig) -> None:
        """Connect to MCP server.

        Args:
            config: Server configuration (validated on creation).

        Raises:
            MCPManagerError: If connection fails.
        """
        # Import MCP client (lazy import to avoid dependency issues)
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError:
            raise MCPManagerError(
                "MCP client not installed. Run: pip install mcp"
            )

        server_params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env,
        )

        try:
            # Manually manage lifecycle - don't use async with
            # which would close the session when the block exits.
            # Step 1: Start the stdio client transport
            client_cm = stdio_client(server_params)
            read, write = await client_cm.__aenter__()

            try:
                # Step 2: Create and initialize session
                session_cm = ClientSession(read, write)
                session = await session_cm.__aenter__()

                try:
                    await session.initialize()

                    # Step 3: Get tool list
                    tools_result = await session.list_tools()
                    self._tools[config.id] = [
                        MCPTool(
                            server_id=config.id,
                            name=tool.name,
                            description=tool.description or "",
                            input_schema=tool.inputSchema,
                        )
                        for tool in tools_result.tools
                    ]

                    # Step 4: Store session + context managers for later cleanup
                    self._sessions[config.id] = session
                    self._configs[config.id] = config
                    self._client_contexts[config.id] = client_cm
                    self._session_contexts[config.id] = session_cm

                except Exception:
                    await session_cm.__aexit__(None, None, None)
                    raise
            except Exception:
                await client_cm.__aexit__(None, None, None)
                raise

        except Exception as e:
            breaker = self._get_or_create_breaker(config.id)
            breaker.record_failure(e)
            raise MCPManagerError(f"Failed to connect to {config.name}: {e}")

    async def execute_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        timeout: float | None = None,
    ) -> Any:
        """Execute MCP tool with circuit breaker protection.

        Args:
            server_id: Server ID.
            tool_name: Tool name to execute.
            arguments: Tool arguments.
            timeout: Execution timeout in seconds.

        Returns:
            Tool execution result.

        Raises:
            MCPServerNotConnectedError: If server not connected.
            CircuitOpenError: If circuit breaker is open.
            MCPManagerError: If execution fails.
        """
        if server_id not in self._sessions:
            raise MCPServerNotConnectedError(server_id)

        session = self._sessions[server_id]
        breaker = self._get_or_create_breaker(server_id)
        effective_timeout = timeout or self.DEFAULT_TOOL_TIMEOUT

        async def _execute() -> Any:
            return await asyncio.wait_for(
                session.call_tool(tool_name, arguments),
                timeout=effective_timeout,
            )

        try:
            result = await breaker.execute(_execute)
            return result.content
        except CircuitOpenError:
            raise
        except asyncio.TimeoutError:
            raise MCPManagerError(
                f"Tool '{tool_name}' timed out after {effective_timeout}s"
            )
        except Exception as e:
            raise MCPManagerError(f"Tool execution failed: {e}")

    def list_tools(self, server_id: str | None = None) -> list[MCPTool]:
        """List available tools.

        Args:
            server_id: Optional server ID to filter.

        Returns:
            List of tools.
        """
        if server_id:
            return self._tools.get(server_id, [])
        return [tool for tools in self._tools.values() for tool in tools]

    def list_servers(self) -> list[MCPServerConfig]:
        """List connected servers.

        Returns:
            List of server configurations.
        """
        return list(self._configs.values())

    def get_server_status(self, server_id: str) -> dict[str, Any]:
        """Get server connection status.

        Args:
            server_id: Server ID.

        Returns:
            Status dict with connected, circuit_state, tool_count.
        """
        breaker = self._circuit_breakers.get(server_id)
        return {
            "connected": server_id in self._sessions,
            "circuit_state": breaker.state.value if breaker else "unknown",
            "tool_count": len(self._tools.get(server_id, [])),
        }

    async def disconnect(self, server_id: str) -> None:
        """Disconnect from MCP server.

        Args:
            server_id: Server ID.
        """
        # Close session context manager first
        if server_id in self._session_contexts:
            try:
                await self._session_contexts[server_id].__aexit__(None, None, None)
            except Exception:
                pass
            del self._session_contexts[server_id]

        # Then close client (transport) context manager
        if server_id in self._client_contexts:
            try:
                await self._client_contexts[server_id].__aexit__(None, None, None)
            except Exception:
                pass
            del self._client_contexts[server_id]

        # Clean up references
        if server_id in self._sessions:
            del self._sessions[server_id]
        if server_id in self._tools:
            del self._tools[server_id]
        if server_id in self._configs:
            del self._configs[server_id]

    async def health_check(self, server_id: str) -> bool:
        """Check if server is healthy.

        Args:
            server_id: Server ID.

        Returns:
            True if healthy, False otherwise.
        """
        if server_id not in self._sessions:
            return False

        try:
            session = self._sessions[server_id]
            # Light-weight health check - list tools
            await asyncio.wait_for(session.list_tools(), timeout=5.0)
            return True
        except Exception:
            return False

    async def shutdown(self) -> None:
        """Disconnect all servers. Call during application shutdown."""
        server_ids = list(self._sessions.keys())
        for server_id in server_ids:
            await self.disconnect(server_id)
