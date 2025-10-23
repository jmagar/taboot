"""Middleware for Taboot API."""

from apps.api.middleware.logging import RequestLoggingMiddleware

__all__ = ["RequestLoggingMiddleware"]
