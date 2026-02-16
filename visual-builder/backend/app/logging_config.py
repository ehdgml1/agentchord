"""Structured logging configuration."""
from __future__ import annotations

import logging
import logging.config
from typing import Any

from app.config import get_settings


def setup_logging() -> None:
    """Configure structured logging based on settings."""
    settings = get_settings()

    config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "text": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {
                "format": '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
                "datefmt": "%Y-%m-%dT%H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": settings.log_format if settings.log_format in ("text", "json") else "text",
            },
        },
        "root": {
            "level": settings.log_level.upper(),
            "handlers": ["console"],
        },
        "loggers": {
            "uvicorn": {"level": settings.log_level.upper()},
            "sqlalchemy.engine": {"level": "WARNING"},
            "app": {"level": settings.log_level.upper()},
        },
    }

    logging.config.dictConfig(config)
