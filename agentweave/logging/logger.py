"""AgentWeave logger implementation."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


class LogLevel(str, Enum):
    """Log levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

    @property
    def rank(self) -> int:
        """Get numeric rank for comparison."""
        ranks = {"debug": 0, "info": 1, "warning": 2, "error": 3}
        return ranks[self.value]


class AgentWeaveLogger:
    """Structured logger for AgentWeave.

    Provides Rich-formatted logging for agent execution tracking.

    Example:
        >>> logger = AgentWeaveLogger(level=LogLevel.DEBUG)
        >>> logger.info("Processing started", agent="researcher")
        >>> logger.agent_start("researcher", "What is AI?")
    """

    def __init__(
        self,
        level: LogLevel = LogLevel.INFO,
        console: Console | None = None,
        show_timestamps: bool = True,
        show_level: bool = True,
        enabled: bool = True,
    ) -> None:
        """Initialize logger.

        Args:
            level: Minimum log level to display.
            console: Rich console instance (created if None).
            show_timestamps: Whether to show timestamps.
            show_level: Whether to show log level.
            enabled: Whether logging is enabled.
        """
        self._level = level
        self._console = console or Console()
        self._show_timestamps = show_timestamps
        self._show_level = show_level
        self._enabled = enabled

    @property
    def level(self) -> LogLevel:
        """Current log level."""
        return self._level

    @level.setter
    def level(self, value: LogLevel) -> None:
        """Set log level."""
        self._level = value

    @property
    def enabled(self) -> bool:
        """Whether logging is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Enable or disable logging."""
        self._enabled = value

    def _should_log(self, level: LogLevel) -> bool:
        """Check if message should be logged."""
        return self._enabled and level.rank >= self._level.rank

    def _format_prefix(self, level: LogLevel) -> str:
        """Format log prefix with timestamp and level."""
        parts = []

        if self._show_timestamps:
            timestamp = datetime.now().strftime("%H:%M:%S")
            parts.append(f"[dim]{timestamp}[/]")

        if self._show_level:
            level_colors = {
                LogLevel.DEBUG: "dim",
                LogLevel.INFO: "blue",
                LogLevel.WARNING: "yellow",
                LogLevel.ERROR: "red bold",
            }
            color = level_colors.get(level, "white")
            parts.append(f"[{color}]{level.value.upper():7}[/]")

        return " ".join(parts)

    def _log(self, level: LogLevel, message: str, **context: Any) -> None:
        """Internal log method."""
        if not self._should_log(level):
            return

        prefix = self._format_prefix(level)

        # Add context if provided
        if context:
            context_str = " ".join(f"[dim]{k}=[/]{v}" for k, v in context.items())
            message = f"{message} {context_str}"

        self._console.print(f"{prefix} {message}")

    def debug(self, message: str, **context: Any) -> None:
        """Log debug message."""
        self._log(LogLevel.DEBUG, message, **context)

    def info(self, message: str, **context: Any) -> None:
        """Log info message."""
        self._log(LogLevel.INFO, message, **context)

    def warning(self, message: str, **context: Any) -> None:
        """Log warning message."""
        self._log(LogLevel.WARNING, message, **context)

    def error(self, message: str, **context: Any) -> None:
        """Log error message."""
        self._log(LogLevel.ERROR, message, **context)

    # Agent-specific logging methods

    def agent_start(self, agent_name: str, input_preview: str | None = None) -> None:
        """Log agent start."""
        if not self._should_log(LogLevel.INFO):
            return

        preview = ""
        if input_preview:
            preview = input_preview[:50] + "..." if len(input_preview) > 50 else input_preview
            preview = f' "{preview}"'

        self._console.print(
            f"{self._format_prefix(LogLevel.INFO)} "
            f"[bold blue]▶ {agent_name}[/] starting{preview}"
        )

    def agent_end(
        self,
        agent_name: str,
        duration_ms: int,
        tokens: int | None = None,
        cost: float | None = None,
    ) -> None:
        """Log agent completion."""
        if not self._should_log(LogLevel.INFO):
            return

        details = [f"{duration_ms}ms"]
        if tokens:
            details.append(f"{tokens:,} tokens")
        if cost:
            details.append(f"${cost:.4f}")

        detail_str = " | ".join(details)

        self._console.print(
            f"{self._format_prefix(LogLevel.INFO)} "
            f"[bold green]✓ {agent_name}[/] completed ({detail_str})"
        )

    def agent_error(self, agent_name: str, error: str) -> None:
        """Log agent error."""
        if not self._should_log(LogLevel.ERROR):
            return

        self._console.print(
            f"{self._format_prefix(LogLevel.ERROR)} "
            f"[bold red]✗ {agent_name}[/] failed: {error}"
        )

    def llm_call(
        self,
        model: str,
        tokens: int,
        cost: float,
        duration_ms: int,
    ) -> None:
        """Log LLM API call."""
        if not self._should_log(LogLevel.DEBUG):
            return

        self._console.print(
            f"{self._format_prefix(LogLevel.DEBUG)} "
            f"  [dim]LLM:[/] {model} | {tokens:,} tokens | ${cost:.4f} | {duration_ms}ms"
        )

    def tool_call(self, tool_name: str, success: bool, duration_ms: int | None = None) -> None:
        """Log tool call."""
        if not self._should_log(LogLevel.DEBUG):
            return

        status = "[green]✓[/]" if success else "[red]✗[/]"
        duration = f" ({duration_ms}ms)" if duration_ms else ""

        self._console.print(
            f"{self._format_prefix(LogLevel.DEBUG)} "
            f"  [dim]Tool:[/] {tool_name} {status}{duration}"
        )

    def workflow_start(self, workflow_name: str, agent_count: int) -> None:
        """Log workflow start."""
        if not self._should_log(LogLevel.INFO):
            return

        self._console.print(
            f"{self._format_prefix(LogLevel.INFO)} "
            f"[bold cyan]◆ Workflow[/] starting with {agent_count} agents"
        )

    def workflow_step(self, step: int, agent_name: str) -> None:
        """Log workflow step."""
        if not self._should_log(LogLevel.DEBUG):
            return

        self._console.print(
            f"{self._format_prefix(LogLevel.DEBUG)} "
            f"  [dim]Step {step}:[/] {agent_name}"
        )

    def workflow_end(self, duration_ms: int, total_cost: float) -> None:
        """Log workflow completion."""
        if not self._should_log(LogLevel.INFO):
            return

        self._console.print(
            f"{self._format_prefix(LogLevel.INFO)} "
            f"[bold cyan]◆ Workflow[/] completed ({duration_ms}ms | ${total_cost:.4f})"
        )
