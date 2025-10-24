"""Prometheus metrics middleware for HTTP request instrumentation.

Automatically instruments all HTTP requests with Prometheus metrics:
- Request counts by method, path, and status
- Request duration histograms by method and path

Follows OBSERVABILITY.md requirements for HTTP request metrics.
"""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from apps.api.routes.metrics import http_request_duration_seconds, http_requests_total


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to instrument HTTP requests with Prometheus metrics.

    Records request counts and latencies for all HTTP requests.
    Metrics are exposed via the /metrics endpoint.

    Attributes:
        None

    Example:
        >>> app = FastAPI()
        >>> app.add_middleware(PrometheusMiddleware)
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore
        """Process request and record metrics.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware or route handler.

        Returns:
            Response: HTTP response from downstream handler.
        """
        # Skip metrics endpoint to avoid recursion
        if request.url.path == "/metrics":
            return await call_next(request)

        start_time = time.time()

        # Call next middleware/handler
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Record metrics
        http_requests_total.labels(
            method=request.method, path=request.url.path, status=response.status_code
        ).inc()

        http_request_duration_seconds.labels(method=request.method, path=request.url.path).observe(
            duration
        )

        return response


# Export public API
__all__ = ["PrometheusMiddleware"]
