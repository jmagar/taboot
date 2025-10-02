"""Placeholder metrics module for LlamaCrawl.

This module provides a simplified metrics interface that is compatible with
prometheus_client for future migration. Currently, metrics are collected but
not exported.

FUTURE WORK: Full Prometheus integration with HTTP endpoint for scraping.
This placeholder implementation allows code to use metrics decorators now
without blocking development.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, Any, TypeVar

from llamacrawl.utils.logging import get_logger

if TYPE_CHECKING:
    pass

# Type variables for decorators
F = TypeVar("F", bound=Callable[..., Any])

logger = get_logger(__name__)


class MetricRegistry:
    """Registry to store all metrics instances.

    This maintains a global registry of metrics that can be used for
    future Prometheus export functionality.
    """

    def __init__(self) -> None:
        """Initialize empty metric registry."""
        self._metrics: dict[str, BaseMetric] = {}

    def register(self, name: str, metric: BaseMetric) -> None:
        """Register a metric with the registry.

        Args:
            name: Metric name (should be unique)
            metric: Metric instance to register
        """
        if name in self._metrics:
            logger.warning(
                "Metric already registered, overwriting",
                extra={"metric_name": name}
            )
        self._metrics[name] = metric

    def get_metric(self, name: str) -> BaseMetric | None:
        """Retrieve a metric by name.

        Args:
            name: Metric name

        Returns:
            Metric instance or None if not found
        """
        return self._metrics.get(name)

    def get_all_metrics(self) -> dict[str, BaseMetric]:
        """Get all registered metrics.

        Returns:
            Dictionary mapping metric names to metric instances
        """
        return self._metrics.copy()


# Global metric registry
_REGISTRY = MetricRegistry()


class BaseMetric:
    """Base class for all metrics.

    Provides common interface compatible with prometheus_client metrics.
    """

    def __init__(self, name: str, description: str, labels: list[str] | None = None) -> None:
        """Initialize base metric.

        Args:
            name: Metric name (should be snake_case)
            description: Human-readable description
            labels: Optional list of label names
        """
        self.name = name
        self.description = description
        self.labels = labels or []
        _REGISTRY.register(name, self)


class Counter(BaseMetric):
    """Counter metric that only increases.

    Compatible with prometheus_client.Counter interface.
    Counts events like: total documents ingested, total errors, etc.
    """

    def __init__(self, name: str, description: str, labels: list[str] | None = None) -> None:
        """Initialize counter.

        Args:
            name: Metric name
            description: Human-readable description
            labels: Optional list of label names
        """
        super().__init__(name, description, labels)
        self._value: float = 0.0
        self._labeled_values: dict[tuple[str, ...], float] = {}

    def inc(self, amount: float = 1.0, **label_values: str) -> None:
        """Increment counter.

        Args:
            amount: Amount to increment (default 1.0)
            **label_values: Label key-value pairs
        """
        if self.labels and label_values:
            # Labeled counter
            label_tuple = tuple(label_values.get(label, "") for label in self.labels)
            self._labeled_values[label_tuple] = self._labeled_values.get(label_tuple, 0.0) + amount
        else:
            # Unlabeled counter
            self._value += amount

        logger.debug(
            "Counter incremented",
            extra={
                "metric": self.name,
                "amount": amount,
                "labels": label_values,
            }
        )

    def get_value(self, **label_values: str) -> float:
        """Get current counter value.

        Args:
            **label_values: Label key-value pairs

        Returns:
            Current counter value
        """
        if self.labels and label_values:
            label_tuple = tuple(label_values.get(label, "") for label in self.labels)
            return self._labeled_values.get(label_tuple, 0.0)
        return self._value


class Histogram(BaseMetric):
    """Histogram metric for tracking distributions.

    Compatible with prometheus_client.Histogram interface.
    Tracks distributions like: request durations, batch sizes, etc.
    """

    def __init__(
        self,
        name: str,
        description: str,
        labels: list[str] | None = None,
        buckets: list[float] | None = None
    ) -> None:
        """Initialize histogram.

        Args:
            name: Metric name
            description: Human-readable description
            labels: Optional list of label names
            buckets: Optional bucket boundaries
                (default: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0])
        """
        super().__init__(name, description, labels)
        self.buckets = buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        self._observations: list[float] = []
        self._labeled_observations: dict[tuple[str, ...], list[float]] = {}

    def observe(self, value: float, **label_values: str) -> None:
        """Record an observation.

        Args:
            value: Value to observe
            **label_values: Label key-value pairs
        """
        if self.labels and label_values:
            # Labeled histogram
            label_tuple = tuple(label_values.get(label, "") for label in self.labels)
            if label_tuple not in self._labeled_observations:
                self._labeled_observations[label_tuple] = []
            self._labeled_observations[label_tuple].append(value)
        else:
            # Unlabeled histogram
            self._observations.append(value)

        logger.debug(
            "Histogram observation recorded",
            extra={
                "metric": self.name,
                "value": value,
                "labels": label_values,
            }
        )

    def get_observations(self, **label_values: str) -> list[float]:
        """Get all observations.

        Args:
            **label_values: Label key-value pairs

        Returns:
            List of all observed values
        """
        if self.labels and label_values:
            label_tuple = tuple(label_values.get(label, "") for label in self.labels)
            return self._labeled_observations.get(label_tuple, []).copy()
        return self._observations.copy()


class Gauge(BaseMetric):
    """Gauge metric that can go up or down.

    Compatible with prometheus_client.Gauge interface.
    Tracks current state like: active connections, queue size, etc.
    """

    def __init__(self, name: str, description: str, labels: list[str] | None = None) -> None:
        """Initialize gauge.

        Args:
            name: Metric name
            description: Human-readable description
            labels: Optional list of label names
        """
        super().__init__(name, description, labels)
        self._value: float = 0.0
        self._labeled_values: dict[tuple[str, ...], float] = {}

    def set(self, value: float, **label_values: str) -> None:
        """Set gauge to a specific value.

        Args:
            value: Value to set
            **label_values: Label key-value pairs
        """
        if self.labels and label_values:
            # Labeled gauge
            label_tuple = tuple(label_values.get(label, "") for label in self.labels)
            self._labeled_values[label_tuple] = value
        else:
            # Unlabeled gauge
            self._value = value

        logger.debug(
            "Gauge set",
            extra={
                "metric": self.name,
                "value": value,
                "labels": label_values,
            }
        )

    def inc(self, amount: float = 1.0, **label_values: str) -> None:
        """Increment gauge.

        Args:
            amount: Amount to increment (default 1.0)
            **label_values: Label key-value pairs
        """
        if self.labels and label_values:
            label_tuple = tuple(label_values.get(label, "") for label in self.labels)
            self._labeled_values[label_tuple] = self._labeled_values.get(label_tuple, 0.0) + amount
        else:
            self._value += amount

        logger.debug(
            "Gauge incremented",
            extra={
                "metric": self.name,
                "amount": amount,
                "labels": label_values,
            }
        )

    def dec(self, amount: float = 1.0, **label_values: str) -> None:
        """Decrement gauge.

        Args:
            amount: Amount to decrement (default 1.0)
            **label_values: Label key-value pairs
        """
        if self.labels and label_values:
            label_tuple = tuple(label_values.get(label, "") for label in self.labels)
            self._labeled_values[label_tuple] = self._labeled_values.get(label_tuple, 0.0) - amount
        else:
            self._value -= amount

        logger.debug(
            "Gauge decremented",
            extra={
                "metric": self.name,
                "amount": amount,
                "labels": label_values,
            }
        )

    def get_value(self, **label_values: str) -> float:
        """Get current gauge value.

        Args:
            **label_values: Label key-value pairs

        Returns:
            Current gauge value
        """
        if self.labels and label_values:
            label_tuple = tuple(label_values.get(label, "") for label in self.labels)
            return self._labeled_values.get(label_tuple, 0.0)
        return self._value


def track_duration(
    metric_name: str,
    metric_description: str | None = None,
    labels: list[str] | None = None
) -> Callable[[F], F]:
    """Decorator to track function execution duration in a histogram.

    Creates a histogram metric and records the execution time of the decorated
    function. Compatible with future prometheus_client integration.

    Args:
        metric_name: Name of the histogram metric
        metric_description: Optional description (defaults to auto-generated)
        labels: Optional list of label names

    Returns:
        Decorator function

    Example:
        @track_duration("ingestion_duration_seconds", labels=["source"])
        def ingest_documents(source: str) -> int:
            # ... processing logic
            return doc_count

        # Call with label values via keyword args or metric context
        ingest_documents(source="github")
    """
    import asyncio
    import inspect

    # Create or retrieve metric
    description = metric_description or f"Duration of {metric_name} in seconds"
    metric = _REGISTRY.get_metric(metric_name)

    if metric is None:
        metric = Histogram(metric_name, description, labels)
    elif not isinstance(metric, Histogram):
        raise TypeError(f"Metric {metric_name} is not a Histogram")

    def decorator(func: F) -> F:
        """Decorator that wraps function with timing."""
        # Check if function is async
        if asyncio.iscoroutinefunction(func) or inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                """Asynchronous wrapper for duration tracking."""
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    # Extract label values from kwargs if labels are defined
                    label_values = {}
                    if labels:
                        for label in labels:
                            if label in kwargs:
                                label_values[label] = str(kwargs[label])
                    metric.observe(duration, **label_values)

            return async_wrapper  # type: ignore

        # Synchronous function
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            """Synchronous wrapper for duration tracking."""
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                # Extract label values from kwargs if labels are defined
                label_values = {}
                if labels:
                    for label in labels:
                        if label in kwargs:
                            label_values[label] = str(kwargs[label])
                metric.observe(duration, **label_values)

        return wrapper  # type: ignore

    return decorator


def count_calls(
    metric_name: str,
    metric_description: str | None = None,
    labels: list[str] | None = None
) -> Callable[[F], F]:
    """Decorator to count function calls in a counter.

    Creates a counter metric and increments it each time the decorated
    function is called. Compatible with future prometheus_client integration.

    Args:
        metric_name: Name of the counter metric
        metric_description: Optional description (defaults to auto-generated)
        labels: Optional list of label names

    Returns:
        Decorator function

    Example:
        @count_calls("documents_processed_total", labels=["source", "status"])
        def process_document(source: str, doc_id: str) -> bool:
            # ... processing logic
            return True

        # Label "status" can be added by calling inc() after function
    """
    import asyncio
    import inspect

    # Create or retrieve metric
    description = metric_description or f"Total count of {metric_name}"
    metric = _REGISTRY.get_metric(metric_name)

    if metric is None:
        metric = Counter(metric_name, description, labels)
    elif not isinstance(metric, Counter):
        raise TypeError(f"Metric {metric_name} is not a Counter")

    def decorator(func: F) -> F:
        """Decorator that wraps function with call counting."""
        # Check if function is async
        if asyncio.iscoroutinefunction(func) or inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                """Asynchronous wrapper for call counting."""
                # Extract label values from kwargs if labels are defined
                label_values = {}
                if labels:
                    for label in labels:
                        if label in kwargs:
                            label_values[label] = str(kwargs[label])

                try:
                    result = await func(*args, **kwargs)
                    # Add success status if status label exists
                    if labels and "status" in labels and "status" not in label_values:
                        label_values["status"] = "success"
                    metric.inc(**label_values)  # type: ignore
                    return result
                except Exception:
                    # Add error status if status label exists
                    if labels and "status" in labels and "status" not in label_values:
                        label_values["status"] = "error"
                    metric.inc(**label_values)  # type: ignore
                    raise

            return async_wrapper  # type: ignore

        # Synchronous function
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            """Synchronous wrapper for call counting."""
            # Extract label values from kwargs if labels are defined
            label_values = {}
            if labels:
                for label in labels:
                    if label in kwargs:
                        label_values[label] = str(kwargs[label])

            try:
                result = func(*args, **kwargs)
                # Add success status if status label exists
                if labels and "status" in labels and "status" not in label_values:
                    label_values["status"] = "success"
                metric.inc(**label_values)  # type: ignore
                return result
            except Exception:
                # Add error status if status label exists
                if labels and "status" in labels and "status" not in label_values:
                    label_values["status"] = "error"
                metric.inc(**label_values)  # type: ignore
                raise

        return wrapper  # type: ignore

    return decorator


# Export public API
__all__ = [
    "Counter",
    "Histogram",
    "Gauge",
    "MetricRegistry",
    "track_duration",
    "count_calls",
]
