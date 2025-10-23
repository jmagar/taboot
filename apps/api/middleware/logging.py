"""Request logging middleware for Taboot API.

Provides structured JSON logging for all HTTP requests with:
- Request ID correlation
- Method, path, query parameters
- Response status code
- Elapsed time in milliseconds
- Error details on failures

Conforms to observability requirements in docs/OBSERVABILITY.md.
"""

import logging
import time
from typing import Awaitable, Callable
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all HTTP requests with correlation IDs."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request and log details.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware/handler in chain.

        Returns:
            Response: HTTP response from handler.
        """
        # Generate correlation ID for request tracing
        request_id = str(uuid4())
        start_ns = time.perf_counter_ns()

        # Log request start
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                # Avoid raw query params; optionally whitelist keys
                "query_params": None,
                "client_host": request.client.host if request.client else None,
            },
        )

        # Store request_id in state for access in handlers
        request.state.request_id = request_id

        try:
            # Execute request
            response = await call_next(request)

            # Calculate elapsed time
            elapsed_ms = (time.perf_counter_ns() - start_ns) // 1_000_000

            # Log successful request
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "elapsed_ms": elapsed_ms,
                },
            )

            # Add request_id to response headers for client correlation
            response.headers["X-Request-ID"] = request_id
            return response

        except Exception as e:
            # Calculate elapsed time
            elapsed_ms = (time.perf_counter_ns() - start_ns) // 1_000_000

            # Log failed request
            logger.exception(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "elapsed_ms": elapsed_ms,
                },
            )

            # Re-raise to allow FastAPI error handlers to process
            raise
