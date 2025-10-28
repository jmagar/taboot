"""Common utilities for Taboot platform.

This package provides reusable utilities like logging, config, tracing,
and environment validation.

Note: Factory functions are available via direct import to avoid circular dependencies:
    from packages.common.factories import make_ingest_youtube_use_case, make_reprocess_use_case
"""

from packages.common.env_validator import (
    ValidationError,
    validate_environment,
    validate_required_secret,
)
from packages.common.postgres_pool import PostgresPool, PostgresPoolError

__all__ = [
    "ValidationError",
    "validate_environment",
    "validate_required_secret",
    "PostgresPool",
    "PostgresPoolError",
]
