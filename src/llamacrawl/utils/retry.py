"""Retry utilities with exponential backoff for LlamaCrawl.

This module provides retry decorators with exponential backoff for handling
transient failures in API calls and network operations. Supports both sync
and async functions, respects HTTP Retry-After headers, and includes jitter
to prevent thundering herd problems.
"""

import asyncio
import random
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

from llamacrawl.config import RetryConfig
from llamacrawl.utils.logging import get_logger

# Type variables for decorators
F = TypeVar("F", bound=Callable[..., Any])

# Default exceptions to catch (transient network/API errors)
DEFAULT_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)

logger = get_logger(__name__)


def _extract_retry_after(exception: Exception) -> float | None:
    """Extract Retry-After value from HTTP exception if available.

    Args:
        exception: Exception that may contain Retry-After header

    Returns:
        Retry delay in seconds, or None if not found
    """
    # Try to extract from common HTTP client exceptions
    if hasattr(exception, "response") and exception.response is not None:
        response = exception.response

        # Check for Retry-After header (case-insensitive)
        if hasattr(response, "headers"):
            headers = response.headers

            # Try different case variations
            for key in ("Retry-After", "retry-after", "RETRY-AFTER"):
                if key in headers:
                    retry_after = headers[key]

                    # Retry-After can be either seconds or HTTP date
                    # For simplicity, we only handle seconds (integer)
                    try:
                        return float(retry_after)
                    except (ValueError, TypeError):
                        # If it's a date string, we can't easily parse it
                        # Fall back to exponential backoff
                        pass

    return None


def _is_auth_error(exception: Exception) -> bool:
    """Check if exception is an authentication/authorization error.

    Auth errors should fail fast without retry.

    Args:
        exception: Exception to check

    Returns:
        True if this is an auth error that should not be retried
    """
    # Check for HTTP status codes 401, 403
    if hasattr(exception, "response") and exception.response is not None:
        response = exception.response

        if hasattr(response, "status_code"):
            status_code = response.status_code
            if status_code in (401, 403):
                return True

    # Check for common auth-related exception messages
    error_msg = str(exception).lower()
    auth_keywords = [
        "unauthorized",
        "forbidden",
        "authentication",
        "auth failed",
        "invalid token",
        "invalid api key",
        "access denied",
    ]

    return any(keyword in error_msg for keyword in auth_keywords)


def _calculate_delay(
    attempt: int,
    initial_delay: float,
    max_delay: float,
    jitter: bool = True,
) -> float:
    """Calculate delay with exponential backoff and optional jitter.

    Args:
        attempt: Current attempt number (0-indexed)
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Whether to add random jitter (0-20% variation)

    Returns:
        Delay in seconds before next retry
    """
    # Exponential backoff: delay *= 2 for each attempt
    delay: float = initial_delay * (2 ** attempt)

    # Cap at max_delay
    delay = min(delay, max_delay)

    # Add jitter (random 0-20% variation) to prevent thundering herd
    if jitter:
        jitter_range = delay * 0.2
        jitter_value = random.uniform(0, jitter_range)
        delay += jitter_value

    return delay


def retry_with_backoff(
    max_attempts: int | None = None,
    initial_delay: float | None = None,
    max_delay: float | None = None,
    exceptions: tuple[type[Exception], ...] = DEFAULT_EXCEPTIONS,
    config: RetryConfig | None = None,
) -> Callable[[F], F]:
    """Decorator for retrying functions with exponential backoff.

    Retries the decorated function on transient failures with exponential
    backoff. Respects HTTP Retry-After headers and fails fast on
    authentication errors (401, 403).

    If config is provided, uses values from RetryConfig. Otherwise uses
    provided parameters or defaults.

    Args:
        max_attempts: Maximum number of attempts (including initial call), or None to use config
        initial_delay: Initial delay in seconds before first retry, or None to use config
        max_delay: Maximum delay in seconds between retries, or None to use config
        exceptions: Tuple of exception types to catch and retry
        config: Optional RetryConfig to use for all parameters

    Returns:
        Decorator function

    Example:
        @retry_with_backoff(max_attempts=3, initial_delay=2.0)
        def fetch_data(url: str) -> dict:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()

        # Or use config from get_config()
        from llamacrawl.config import get_config
        cfg = get_config()
        @retry_with_backoff(config=cfg.ingestion.retry)
        def fetch_data_with_config(url: str) -> dict:
            ...
    """
    # Use config values if provided, otherwise use parameters or defaults
    if config is not None:
        _max_attempts = config.max_attempts
        _initial_delay = config.initial_delay_seconds
        _max_delay = config.max_delay_seconds
    else:
        _max_attempts = max_attempts if max_attempts is not None else 3
        _initial_delay = initial_delay if initial_delay is not None else 1.0
        _max_delay = max_delay if max_delay is not None else 60.0
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            """Synchronous wrapper with retry logic."""
            last_exception: Exception | None = None

            for attempt in range(_max_attempts):
                try:
                    # Attempt the function call
                    result = func(*args, **kwargs)

                    # Log success if this was a retry
                    if attempt > 0:
                        logger.info(
                            f"Function {func.__name__} succeeded on retry",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_attempts": _max_attempts,
                            },
                        )

                    return result

                except exceptions as e:
                    last_exception = e

                    # Fail fast on authentication errors
                    if _is_auth_error(e):
                        logger.error(
                            f"Authentication error in {func.__name__}, failing without retry",
                            extra={
                                "function": func.__name__,
                                "error": str(e),
                                "attempt": attempt + 1,
                            },
                        )
                        raise

                    # If this was the last attempt, raise the exception
                    if attempt >= _max_attempts - 1:
                        logger.error(
                            f"Function {func.__name__} failed after {_max_attempts} attempts",
                            extra={
                                "function": func.__name__,
                                "max_attempts": _max_attempts,
                                "final_error": str(e),
                                "error_type": type(e).__name__,
                            },
                        )
                        raise

                    # Check for Retry-After header
                    retry_after = _extract_retry_after(e)

                    if retry_after is not None:
                        delay = retry_after
                        logger.info(
                            f"Respecting Retry-After header for {func.__name__}",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_attempts": _max_attempts,
                                "delay_seconds": delay,
                                "error": str(e),
                            },
                        )
                    else:
                        # Calculate exponential backoff with jitter
                        delay = _calculate_delay(attempt, _initial_delay, _max_delay)
                        logger.warning(
                            f"Function {func.__name__} failed, retrying",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_attempts": _max_attempts,
                                "delay_seconds": round(delay, 2),
                                "error": str(e),
                                "error_type": type(e).__name__,
                            },
                        )

                    # Sleep before retry
                    time.sleep(delay)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

            raise RuntimeError(f"Retry logic failed for {func.__name__}")

        return cast(F, wrapper)

    return decorator


def async_retry_with_backoff(
    max_attempts: int | None = None,
    initial_delay: float | None = None,
    max_delay: float | None = None,
    exceptions: tuple[type[Exception], ...] = DEFAULT_EXCEPTIONS,
    config: RetryConfig | None = None,
) -> Callable[[F], F]:
    """Decorator for retrying async functions with exponential backoff.

    Async version of retry_with_backoff. Retries the decorated async function
    on transient failures with exponential backoff. Respects HTTP Retry-After
    headers and fails fast on authentication errors (401, 403).

    If config is provided, uses values from RetryConfig. Otherwise uses
    provided parameters or defaults.

    Args:
        max_attempts: Maximum number of attempts (including initial call), or None to use config
        initial_delay: Initial delay in seconds before first retry, or None to use config
        max_delay: Maximum delay in seconds between retries, or None to use config
        exceptions: Tuple of exception types to catch and retry
        config: Optional RetryConfig to use for all parameters

    Returns:
        Decorator function

    Example:
        @async_retry_with_backoff(max_attempts=3, initial_delay=2.0)
        async def fetch_data(url: str) -> dict:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()

        # Or use config from get_config()
        from llamacrawl.config import get_config
        cfg = get_config()
        @async_retry_with_backoff(config=cfg.ingestion.retry)
        async def fetch_data_with_config(url: str) -> dict:
            ...
    """
    # Use config values if provided, otherwise use parameters or defaults
    if config is not None:
        _max_attempts = config.max_attempts
        _initial_delay = config.initial_delay_seconds
        _max_delay = config.max_delay_seconds
    else:
        _max_attempts = max_attempts if max_attempts is not None else 3
        _initial_delay = initial_delay if initial_delay is not None else 1.0
        _max_delay = max_delay if max_delay is not None else 60.0
    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            """Asynchronous wrapper with retry logic."""
            last_exception: Exception | None = None

            for attempt in range(_max_attempts):
                try:
                    # Attempt the async function call
                    result = await func(*args, **kwargs)

                    # Log success if this was a retry
                    if attempt > 0:
                        logger.info(
                            f"Async function {func.__name__} succeeded on retry",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_attempts": _max_attempts,
                            },
                        )

                    return result

                except exceptions as e:
                    last_exception = e

                    # Fail fast on authentication errors
                    if _is_auth_error(e):
                        logger.error(
                            f"Authentication error in async {func.__name__}, failing without retry",
                            extra={
                                "function": func.__name__,
                                "error": str(e),
                                "attempt": attempt + 1,
                            },
                        )
                        raise

                    # If this was the last attempt, raise the exception
                    if attempt >= _max_attempts - 1:
                        logger.error(
                            f"Async function {func.__name__} failed after {max_attempts} attempts",
                            extra={
                                "function": func.__name__,
                                "max_attempts": _max_attempts,
                                "final_error": str(e),
                                "error_type": type(e).__name__,
                            },
                        )
                        raise

                    # Check for Retry-After header
                    retry_after = _extract_retry_after(e)

                    if retry_after is not None:
                        delay = retry_after
                        logger.info(
                            f"Respecting Retry-After header for async {func.__name__}",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_attempts": _max_attempts,
                                "delay_seconds": delay,
                                "error": str(e),
                            },
                        )
                    else:
                        # Calculate exponential backoff with jitter
                        delay = _calculate_delay(attempt, _initial_delay, _max_delay)
                        logger.warning(
                            f"Async function {func.__name__} failed, retrying",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_attempts": _max_attempts,
                                "delay_seconds": round(delay, 2),
                                "error": str(e),
                                "error_type": type(e).__name__,
                            },
                        )

                    # Async sleep before retry
                    await asyncio.sleep(delay)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

            raise RuntimeError(f"Async retry logic failed for {func.__name__}")

        return cast(F, async_wrapper)

    return decorator


# Export public API
__all__ = [
    "retry_with_backoff",
    "async_retry_with_backoff",
    "DEFAULT_EXCEPTIONS",
]
