"""Global logging configuration."""

from __future__ import annotations

from typing import Any

from agentweave.logging.logger import LogLevel, AgentWeaveLogger


# Global logger instance
_logger: AgentWeaveLogger | None = None


def get_logger() -> AgentWeaveLogger:
    """Get the global logger instance.

    Creates a default logger if none exists.

    Returns:
        The global AgentWeaveLogger instance.
    """
    global _logger
    if _logger is None:
        _logger = AgentWeaveLogger()
    return _logger


def configure_logging(
    level: LogLevel | str = LogLevel.INFO,
    enabled: bool = True,
    show_timestamps: bool = True,
    show_level: bool = True,
    **kwargs: Any,
) -> AgentWeaveLogger:
    """Configure the global logger.

    Args:
        level: Minimum log level (LogLevel or string).
        enabled: Whether logging is enabled.
        show_timestamps: Whether to show timestamps.
        show_level: Whether to show log level.
        **kwargs: Additional arguments passed to AgentWeaveLogger.

    Returns:
        The configured logger instance.

    Example:
        >>> configure_logging(level="debug", show_timestamps=False)
        >>> logger = get_logger()
        >>> logger.info("Hello")
    """
    global _logger

    # Convert string to LogLevel if needed
    if isinstance(level, str):
        level = LogLevel(level.lower())

    _logger = AgentWeaveLogger(
        level=level,
        enabled=enabled,
        show_timestamps=show_timestamps,
        show_level=show_level,
        **kwargs,
    )

    return _logger


def disable_logging() -> None:
    """Disable all logging."""
    logger = get_logger()
    logger.enabled = False


def enable_logging() -> None:
    """Enable logging."""
    logger = get_logger()
    logger.enabled = True
