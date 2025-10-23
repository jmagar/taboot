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
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all HTTP requests with correlation IDs."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and log details.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware/handler in chain.

        Returns:
            Response: HTTP response from handler.
        """
        # Generate correlation ID for request tracing
        request_id = str(uuid4())
        start_time = time.time()

        # Log request start
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_host": request.client.host if request.client else None,
            },
        )

        # Store request_id in state for access in handlers
        request.state.request_id = request_id

        try:
            # Execute request
            response = await call_next(request)

            # Calculate elapsed time
            elapsed_ms = int((time.time() - start_time) * 1000)

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
            elapsed_ms = int((time.time() - start_time) * 1000)

            # Log failed request
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "elapsed_ms": elapsed_ms,
                    "error": str(e),
                },
                exc_info=True,
            )

            # Re-raise to allow FastAPI error handlers to process
            raise
