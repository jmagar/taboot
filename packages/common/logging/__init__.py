"""JSON structured logging for Taboot platform.

Provides structured logging with correlation IDs, severity levels, and contextual metadata.
Uses python-json-logger for JSON formatting as required by FR-035.
"""

import logging
import sys
from typing import Any

from pythonjsonlogger import jsonlogger

from packages.common.config import get_config


class CorrelationIdFilter(logging.Filter):
    """Logging filter that injects correlation ID into log records.

    The correlation ID is stored in a context variable and automatically
    added to all log records for request tracing.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Inject correlation ID into the log record.

        Args:
            record: The log record to modify.

        Returns:
            bool: Always True (doesn't filter out records).
        """
        # Import here to avoid circular dependency
        from packages.common.tracing import get_correlation_id

        record.correlation_id = get_correlation_id()
        return True


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields.

    Adds timestamp, level, module, and correlation_id to all log records.
    """

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        """Add custom fields to the JSON log record.

        Args:
            log_record: The dictionary that will be serialized to JSON.
            record: The original logging.LogRecord.
            message_dict: Dictionary from the log message.
        """
        super().add_fields(log_record, record, message_dict)

        # Add standard fields
        log_record["timestamp"] = record.created
        log_record["level"] = record.levelname
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno

        # Add correlation ID if present
        if hasattr(record, "correlation_id"):
            log_record["correlation_id"] = record.correlation_id


def setup_logging(level: str | None = None) -> None:
    """Configure JSON structured logging for the application.

    Sets up:
    - JSON formatter with correlation IDs
    - Console handler writing to stdout
    - Log level from config or parameter

    Args:
        level: Optional log level override (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               If not provided, uses LOG_LEVEL from config.

    Example:
        >>> setup_logging("DEBUG")
        >>> logger = get_logger(__name__)
        >>> logger.info("Starting ingestion", doc_id="abc123", source="web")
    """
    config = get_config()
    log_level = level or config.log_level

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level.upper())

    # Apply JSON formatter
    json_formatter = CustomJsonFormatter(
        "%(timestamp)s %(level)s %(module)s %(function)s %(message)s"
    )
    console_handler.setFormatter(json_formatter)

    # Add correlation ID filter
    console_handler.addFilter(CorrelationIdFilter())

    # Add handler to root logger
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given module.

    Args:
        name: The logger name (typically __name__ from the calling module).

    Returns:
        logging.Logger: Configured logger instance.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing document", doc_id="abc123")
    """
    return logging.getLogger(name)


# Export public API
__all__ = ["CorrelationIdFilter", "CustomJsonFormatter", "get_logger", "setup_logging"]
