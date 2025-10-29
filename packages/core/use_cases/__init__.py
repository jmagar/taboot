"""Core use cases - Application service orchestration.

Use cases orchestrate workflows across adapters without containing framework-specific code.
"""

from __future__ import annotations

from packages.core.use_cases.extract_pending import DocumentStore, ExtractPendingUseCase
from packages.core.use_cases.get_status import (
    GetStatusUseCase,
    MetricsSnapshot,
    QueueDepth,
    ServiceHealth,
    SystemStatus,
)
from packages.core.use_cases.ingest_docker_compose import (
    DockerComposeIngestionResult,
    IngestDockerComposeUseCase,
)
from packages.core.use_cases.ingest_web import IngestWebUseCase

__all__ = [
    "DocumentStore",
    "ExtractPendingUseCase",
    "GetStatusUseCase",
    "IngestDockerComposeUseCase",
    "IngestWebUseCase",
    "MetricsSnapshot",
    "QueueDepth",
    "ServiceHealth",
    "SystemStatus",
    "DockerComposeIngestionResult",
]
