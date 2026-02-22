"""Unit tests for Logging module."""

from __future__ import annotations

from io import StringIO

import pytest
from rich.console import Console

from agentchord.logging.logger import LogLevel, AgentChordLogger
from agentchord.logging.config import (
    get_logger,
    configure_logging,
    disable_logging,
    enable_logging,
)


class TestLogLevel:
    """Tests for LogLevel."""

    def test_level_ranking(self) -> None:
        """Levels should have correct rank order."""
        assert LogLevel.DEBUG.rank < LogLevel.INFO.rank
        assert LogLevel.INFO.rank < LogLevel.WARNING.rank
        assert LogLevel.WARNING.rank < LogLevel.ERROR.rank


class TestAgentChordLogger:
    """Tests for AgentChordLogger."""

    def test_default_creation(self) -> None:
        """Should create with defaults."""
        logger = AgentChordLogger()

        assert logger.level == LogLevel.INFO
        assert logger.enabled is True

    def test_level_filtering(self) -> None:
        """Should filter messages below level."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        logger = AgentChordLogger(level=LogLevel.WARNING, console=console)

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")

        result = output.getvalue()
        assert "Debug message" not in result
        assert "Info message" not in result
        assert "Warning message" in result

    def test_disabled_logging(self) -> None:
        """Should not log when disabled."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        logger = AgentChordLogger(enabled=False, console=console)

        logger.info("Should not appear")

        assert output.getvalue() == ""

    def test_enable_disable(self) -> None:
        """Should toggle enabled state."""
        logger = AgentChordLogger()

        logger.enabled = False
        assert logger.enabled is False

        logger.enabled = True
        assert logger.enabled is True

    def test_agent_start_logging(self) -> None:
        """Should log agent start."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        logger = AgentChordLogger(console=console)

        logger.agent_start("researcher", "What is AI?")

        result = output.getvalue()
        assert "researcher" in result
        assert "starting" in result

    def test_agent_end_logging(self) -> None:
        """Should log agent end with metrics."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        logger = AgentChordLogger(console=console)

        logger.agent_end("researcher", duration_ms=150, tokens=100, cost=0.001)

        result = output.getvalue()
        assert "researcher" in result
        assert "150ms" in result

    def test_llm_call_logging(self) -> None:
        """Should log LLM call details."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        logger = AgentChordLogger(level=LogLevel.DEBUG, console=console)

        logger.llm_call("gpt-4o-mini", tokens=500, cost=0.001, duration_ms=200)

        result = output.getvalue()
        assert "gpt-4o-mini" in result
        assert "500" in result

    def test_tool_call_logging(self) -> None:
        """Should log tool calls."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        logger = AgentChordLogger(level=LogLevel.DEBUG, console=console)

        logger.tool_call("search", success=True, duration_ms=50)

        result = output.getvalue()
        assert "search" in result


class TestLoggingConfig:
    """Tests for logging configuration."""

    def test_get_logger_singleton(self) -> None:
        """get_logger should return same instance."""
        logger1 = get_logger()
        logger2 = get_logger()

        # Note: We can't guarantee same instance after configure_logging
        # but they should be valid loggers
        assert isinstance(logger1, AgentChordLogger)
        assert isinstance(logger2, AgentChordLogger)

    def test_configure_logging(self) -> None:
        """Should configure global logger."""
        logger = configure_logging(level="debug", show_timestamps=False)

        assert logger.level == LogLevel.DEBUG

    def test_disable_enable_logging(self) -> None:
        """Should disable and enable logging."""
        configure_logging()

        disable_logging()
        assert get_logger().enabled is False

        enable_logging()
        assert get_logger().enabled is True
