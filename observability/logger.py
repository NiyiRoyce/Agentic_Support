"""Structured logging configuration using structlog."""

import structlog
from typing import Any


def configure_logging(level: str = "INFO") -> None:
    """
    Configure structured JSON logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    import logging

    # Set standard library logging level
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, level.upper()),
        stream=None,  # We'll use structlog's handler
    )

    # Configure structlog processors for JSON output
    shared_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=shared_processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> Any:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return structlog.get_logger(name)


def log_with_context(logger: Any, level: str, message: str, **context: Any) -> None:
    """
    Log a message with additional context.

    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **context: Additional context key-value pairs
    """
    log_method = getattr(logger, level.lower(), logger.info)
    log_method(message, **context)
