"""Structured logging setup for LlamaCrawl.

Supports configurable console output (JSON or rich text), context helpers, and
execution timing utilities used across the application.
"""

import logging
import os
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from datetime import UTC
from functools import wraps
from typing import Any, TypeVar, cast

from pythonjsonlogger import jsonlogger
from rich.logging import RichHandler

# Type variables for decorators
F = TypeVar("F", bound=Callable[..., Any])

# Sensitive field keys to redact
SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "api-key",
    "password",
    "passwd",
    "pwd",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "auth",
    "authorization",
    "credentials",
    "private_key",
    "session",
    "cookie",
}


class CustomJsonFormatter(jsonlogger.JsonFormatter):  # type: ignore
    """Custom JSON formatter with ISO 8601 timestamps and consistent fields."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        """Add custom fields to log record.

        Args:
            log_record: The log record dictionary to add fields to
            record: The LogRecord object
            message_dict: Additional message fields
        """
        super().add_fields(log_record, record, message_dict)

        # Ensure timestamp is ISO 8601 format with timezone
        if not log_record.get("timestamp"):
            from datetime import datetime

            log_record["timestamp"] = datetime.now(UTC).isoformat()

        # Add standard fields
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["message"] = record.getMessage()

        # Add any custom attributes from the record
        # This includes fields added by filters (like add_log_context)
        # Standard LogRecord attributes to exclude
        exclude_attrs = {
            "name", "msg", "args", "created", "filename", "funcName", "levelname",
            "levelno", "lineno", "module", "msecs", "message", "pathname", "process",
            "processName", "relativeCreated", "thread", "threadName", "exc_info",
            "exc_text", "stack_info", "getMessage", "taskName"
        }

        for key, value in record.__dict__.items():
            # Only add custom fields not in exclude list and not already in log_record
            if key not in exclude_attrs and not key.startswith("_") and key not in log_record:
                log_record[key] = value


class SensitiveDataFilter(logging.Filter):
    """Filter to redact sensitive data from log records."""

    def __init__(self, redact_sensitive: bool = True) -> None:
        """Initialize the filter.

        Args:
            redact_sensitive: If True, redacts sensitive fields. If False, logs everything.
        """
        super().__init__()
        self.redact_sensitive = redact_sensitive

    def _redact_value(self, value: Any) -> Any:
        """Redact a value if it appears sensitive.

        Args:
            value: Value to potentially redact

        Returns:
            Redacted value or original value if not sensitive
        """
        if (
            isinstance(value, str)
            and len(value) > 20
            and value.replace("-", "").replace("_", "").isalnum()
        ):
            return "[REDACTED]"
        return value

    def _redact_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Recursively redact sensitive fields in a dictionary.

        Args:
            data: Dictionary to redact

        Returns:
            Dictionary with sensitive fields redacted
        """
        redacted = {}
        for key, value in data.items():
            key_lower = key.lower()

            # Check if key is sensitive
            if any(sensitive_key in key_lower for sensitive_key in SENSITIVE_KEYS):
                redacted[key] = "[REDACTED]"
            elif isinstance(value, dict):
                redacted[key] = self._redact_dict(value)
            elif isinstance(value, list):
                redacted[key] = [
                    self._redact_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                redacted[key] = self._redact_value(value)

        return redacted

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log record to redact sensitive data.

        Args:
            record: Log record to filter

        Returns:
            True to allow the record to be logged
        """
        if not self.redact_sensitive:
            # Redaction disabled, pass through
            return True

        # Redact sensitive fields from record attributes
        for key in list(record.__dict__.keys()):
            if not key.startswith("_"):
                value = getattr(record, key, None)
                if isinstance(value, dict):
                    setattr(record, key, self._redact_dict(value))
                elif isinstance(value, str):
                    # Check if the key itself is sensitive
                    key_lower = key.lower()
                    if any(sensitive_key in key_lower for sensitive_key in SENSITIVE_KEYS):
                        setattr(record, key, "[REDACTED]")

        return True


def setup_logging(
    log_level: str | None = None,
    log_format: str | None = None,
    log_sensitive_data: bool = False,
) -> None:
    """Configure root logger with console output.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL). If None,
            reads from LOG_LEVEL environment variable (default INFO).
        log_format: Output format ("json" or "text"). If None, reads from
            LOG_FORMAT environment variable (default "json").
        log_sensitive_data: If False (default), redacts sensitive fields like
            api_key, password, token. If True, logs everything (NOT for production).
    """
    # Determine log level
    if log_level is None:
        log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    else:
        log_level = log_level.upper()

    # Validate log level
    numeric_level = getattr(logging, log_level, logging.INFO)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO

    # Determine log format
    if log_format is None:
        log_format = os.environ.get("LOG_FORMAT", "json")
    log_format = (log_format or "json").lower()

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    if log_format == "text":
        console_handler = RichHandler(
            rich_tracebacks=True,
            markup=True,
            show_path=False,
            show_time=True,
            log_time_format="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setLevel(numeric_level)
        formatter: logging.Formatter = logging.Formatter("%(message)s")
    else:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        formatter = CustomJsonFormatter(
            "%(timestamp)s %(level)s %(logger)s %(message)s",
            rename_fields={"levelname": "level", "name": "logger"},
        )

    console_handler.setFormatter(formatter)

    # Add sensitive data filter if redaction is enabled
    if not log_sensitive_data:
        sensitive_filter = SensitiveDataFilter(redact_sensitive=True)
        console_handler.addFilter(sensitive_filter)

    # Add handler to root logger
    root_logger.addHandler(console_handler)

    # Log initial setup message
    root_logger.info(
        "Logging configured",
        extra={
            "log_level": log_level,
            "log_format": log_format,
            "log_sensitive_data": log_sensitive_data,
        },
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with module context.

    Args:
        name: Logger name (typically __name__ of the calling module)

    Returns:
        Logger instance configured for the module
    """
    return logging.getLogger(name)


def log_execution_time(func: F) -> F:
    """Decorator to log function execution time.

    Logs the duration of function execution with the function name and result.
    Supports both sync and async functions.

    Args:
        func: Function to decorate

    Returns:
        Wrapped function that logs execution time

    Example:
        @log_execution_time
        def process_documents(source: str) -> int:
            # ... processing logic
            return doc_count
    """
    import asyncio
    import inspect

    logger = get_logger(func.__module__)

    # Check if function is async
    if asyncio.iscoroutinefunction(func) or inspect.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            """Asynchronous wrapper for execution timing."""
            start_time = time.time()
            func_name = func.__name__

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                logger.info(
                    f"Function {func_name} completed",
                    extra={
                        "function": func_name,
                        "duration_seconds": round(duration, 3),
                        "status": "success",
                    },
                )
                return result

            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Function {func_name} failed",
                    extra={
                        "function": func_name,
                        "duration_seconds": round(duration, 3),
                        "status": "error",
                        "error": str(e),
                    },
                )
                raise

        return cast(F, async_wrapper)

    # Synchronous function
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        """Synchronous wrapper for execution timing."""
        start_time = time.time()
        func_name = func.__name__

        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time

            logger.info(
                f"Function {func_name} completed",
                extra={
                    "function": func_name,
                    "duration_seconds": round(duration, 3),
                    "status": "success",
                },
            )
            return result

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Function {func_name} failed",
                extra={
                    "function": func_name,
                    "duration_seconds": round(duration, 3),
                    "status": "error",
                    "error": str(e),
                },
            )
            raise

    return cast(F, wrapper)


@contextmanager
def add_log_context(**context: Any) -> Generator[None, None, None]:
    """Context manager to add temporary context fields to all log messages.

    This uses a logging filter to inject context fields into all log records
    within the context block. The filter is added to all handlers on the root logger.

    Args:
        **context: Key-value pairs to add to log records

    Yields:
        None

    Example:
        with add_log_context(source="github", doc_id="123"):
            logger.info("Processing document")
            # Logs will include source and doc_id fields
    """

    class ContextFilter(logging.Filter):
        """Filter that adds context fields to log records."""

        def filter(self, record: logging.LogRecord) -> bool:
            """Add context fields to the log record.

            Args:
                record: Log record to modify

            Returns:
                True to allow the record to be logged
            """
            for key, value in context.items():
                setattr(record, key, value)
            return True

    # Create filter
    context_filter = ContextFilter()

    # Add filter to all handlers on root logger
    # This ensures it's applied to all log records regardless of logger
    root_logger = logging.getLogger()
    handlers = root_logger.handlers[:]

    for handler in handlers:
        handler.addFilter(context_filter)

    try:
        yield
    finally:
        # Remove filter from all handlers
        for handler in handlers:
            handler.removeFilter(context_filter)


# Export public API
__all__ = [
    "setup_logging",
    "get_logger",
    "log_execution_time",
    "add_log_context",
    "CustomJsonFormatter",
]
