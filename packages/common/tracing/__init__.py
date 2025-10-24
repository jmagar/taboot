"""Correlation ID tracking for distributed tracing.

Provides utilities for managing correlation IDs throughout the request/extraction chain.
Implements the tracing chain: doc_id → section → window_id → triple_id → neo4j_txid
as specified in FR-035.
"""

import uuid
from contextvars import ContextVar
from types import TracebackType

# Context variable for storing the current correlation ID
_correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def generate_correlation_id() -> str:
    """Generate a new correlation ID.

    Returns:
        str: A new UUID4 correlation ID as a string.

    Example:
        >>> corr_id = generate_correlation_id()
        >>> print(corr_id)
        '123e4567-e89b-12d3-a456-426614174000'
    """
    return str(uuid.uuid4())


def set_correlation_id(correlation_id: str | None = None) -> str:
    """Set the correlation ID for the current context.

    If no correlation ID is provided, generates a new one.

    Args:
        correlation_id: Optional correlation ID to set. If None, generates a new one.

    Returns:
        str: The correlation ID that was set.

    Example:
        >>> corr_id = set_correlation_id()
        >>> print(get_correlation_id())
        '123e4567-e89b-12d3-a456-426614174000'
    """
    if correlation_id is None:
        correlation_id = generate_correlation_id()

    _correlation_id_var.set(correlation_id)
    return correlation_id


def get_correlation_id() -> str | None:
    """Get the correlation ID for the current context.

    Returns:
        str | None: The current correlation ID, or None if not set.

    Example:
        >>> set_correlation_id("test-123")
        >>> print(get_correlation_id())
        'test-123'
    """
    return _correlation_id_var.get()


def clear_correlation_id() -> None:
    """Clear the correlation ID for the current context.

    Useful for cleanup between requests or test cases.

    Example:
        >>> set_correlation_id("test-123")
        >>> clear_correlation_id()
        >>> print(get_correlation_id())
        None
    """
    _correlation_id_var.set(None)


class TracingContext:
    """Context manager for managing correlation IDs.

    Automatically sets and clears correlation IDs for a code block.

    Example:
        >>> with TracingContext() as corr_id:
        ...     print(f"Processing with ID: {corr_id}")
        ...     # All logging within this block will include the correlation ID
    """

    def __init__(self, correlation_id: str | None = None) -> None:
        """Initialize the tracing context.

        Args:
            correlation_id: Optional correlation ID. If None, generates a new one.
        """
        self.correlation_id = correlation_id
        self.previous_id: str | None = None

    def __enter__(self) -> str:
        """Enter the context and set the correlation ID.

        Returns:
            str: The correlation ID for this context.
        """
        self.previous_id = get_correlation_id()
        self.correlation_id = set_correlation_id(self.correlation_id)
        return self.correlation_id

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Exit the context and restore the previous correlation ID.

        Args:
            exc_type: Exception type if an exception was raised.
            exc: Exception instance if an exception was raised.
            tb: Traceback if an exception was raised.
        """
        if self.previous_id is None:
            clear_correlation_id()
        else:
            set_correlation_id(self.previous_id)


def build_trace_chain(
    doc_id: str | None = None,
    section: str | None = None,
    window_id: str | None = None,
    triple_id: str | None = None,
    neo4j_txid: str | None = None,
) -> dict[str, str | None]:
    """Build a trace chain dictionary for logging.

    Creates a structured dictionary representing the full extraction chain
    from document to Neo4j transaction as specified in FR-035.

    Args:
        doc_id: Document UUID.
        section: Section/heading path within document.
        window_id: Extraction window UUID.
        triple_id: Triple/relationship UUID.
        neo4j_txid: Neo4j transaction ID.

    Returns:
        dict[str, str | None]: Trace chain dictionary with all provided IDs.

    Example:
        >>> trace = build_trace_chain(
        ...     doc_id="abc-123",
        ...     section="Installation > Prerequisites",
        ...     window_id="win-456"
        ... )
        >>> print(trace)
        {'doc_id': 'abc-123', 'section': 'Installation > Prerequisites', 'window_id': 'win-456', 'triple_id': None, 'neo4j_txid': None}
    """
    return {
        "doc_id": doc_id,
        "section": section,
        "window_id": window_id,
        "triple_id": triple_id,
        "neo4j_txid": neo4j_txid,
    }


# Export public API
__all__ = [
    "TracingContext",
    "build_trace_chain",
    "clear_correlation_id",
    "generate_correlation_id",
    "get_correlation_id",
    "set_correlation_id",
]
