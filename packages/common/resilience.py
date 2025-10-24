"""Resilience utilities for external service calls with retry logic.

Provides decorators for wrapping external service calls with exponential backoff
and retry logic using tenacity. Designed for Firecrawl, Ollama, Neo4j, and TEI.

Required by FR-047: API MUST provide circuit breakers for external services.
"""

import logging
from collections.abc import Callable
from typing import TypeVar

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


def resilient_external_call(
    max_attempts: int = 3,
    min_wait: int = 1,
    max_wait: int = 10,
    retry_on: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry decorator for synchronous external service calls.

    Wraps external calls with exponential backoff retry logic. Logs warnings
    before each retry attempt.

    Args:
        max_attempts: Maximum retry attempts (default: 3).
        min_wait: Minimum wait time in seconds (default: 1).
        max_wait: Maximum wait time in seconds (default: 10).
        retry_on: Exception types to retry on (default: all exceptions).

    Returns:
        Callable: Decorated function with retry logic.

    Example:
        >>> @resilient_external_call(max_attempts=3, min_wait=2, max_wait=15)
        ... def fetch_data(url: str) -> dict:
        ...     return requests.get(url).json()
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(retry_on),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


def resilient_async_call(
    max_attempts: int = 3,
    min_wait: int = 1,
    max_wait: int = 10,
    retry_on: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry decorator for asynchronous external service calls.

    Wraps async external calls with exponential backoff retry logic. Logs warnings
    before each retry attempt.

    Args:
        max_attempts: Maximum retry attempts (default: 3).
        min_wait: Minimum wait time in seconds (default: 1).
        max_wait: Maximum wait time in seconds (default: 10).
        retry_on: Exception types to retry on (default: all exceptions).

    Returns:
        Callable: Decorated async function with retry logic.

    Example:
        >>> @resilient_async_call(max_attempts=3, min_wait=2, max_wait=15)
        ... async def fetch_data_async(url: str) -> dict:
        ...     async with httpx.AsyncClient() as client:
        ...         response = await client.get(url)
        ...         return response.json()
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(retry_on),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


__all__ = ["resilient_external_call", "resilient_async_call"]
