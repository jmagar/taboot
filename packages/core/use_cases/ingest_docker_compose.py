"""IngestDockerComposeUseCase - orchestrates Docker Compose graph ingestion.

Transforms raw reader output into strongly-typed schema models and writes them
through the DockerComposeWriter while capturing ingestion statistics.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence, TypeVar

from packages.graph.writers.docker_compose_writer import DockerComposeWriter
from packages.ingest.readers.docker_compose import DockerComposeReader
from packages.schemas.docker_compose import (
    BuildContext,
    ComposeFile,
    ComposeNetwork,
    ComposeProject,
    ComposeService,
    ComposeVolume,
    DeviceMapping,
    EnvironmentVariable,
    HealthCheck,
    ImageDetails,
    PortBinding,
    ServiceDependency,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DockerComposeIngestionResult:
    """Aggregate ingestion statistics returned by the use case."""

    compose_files: int = 0
    compose_projects: int = 0
    compose_services: int = 0
    compose_networks: int = 0
    compose_volumes: int = 0
    port_bindings: int = 0
    environment_variables: int = 0
    service_dependencies: int = 0
    image_details: int = 0
    health_checks: int = 0
    build_contexts: int = 0
    device_mappings: int = 0

    @property
    def total_nodes(self) -> int:
        """Return the total number of node entities written."""
        return (
            self.compose_files
            + self.compose_projects
            + self.compose_services
            + self.compose_networks
            + self.compose_volumes
            + self.port_bindings
            + self.environment_variables
            + self.image_details
            + self.health_checks
            + self.build_contexts
            + self.device_mappings
        )

    @property
    def total_relationships(self) -> int:
        """Return the total number of relationships written."""
        return self.service_dependencies


T = TypeVar("T")


class IngestDockerComposeUseCase:
    """Use case for ingesting Docker Compose entities into Neo4j."""

    def __init__(self, reader: DockerComposeReader, writer: DockerComposeWriter) -> None:
        self._reader = reader
        self._writer = writer

    def execute(self, file_path: str) -> DockerComposeIngestionResult:
        """Execute the ingestion pipeline for a docker-compose file.

        Args:
            file_path: Path to docker-compose YAML file.

        Returns:
            DockerComposeIngestionResult summarising persisted entities.
        """
        logger.info("docker_compose_ingest.start file_path=%s", file_path)
        raw_data = self._reader.load_data(file_path=file_path)

        result = DockerComposeIngestionResult()

        compose_file = ComposeFile.model_validate(raw_data["compose_file"])
        result.compose_files = self._writer.write_compose_files([compose_file])["total_written"]

        compose_project_data = raw_data.get("compose_project")
        if compose_project_data:
            compose_project = ComposeProject.model_validate(compose_project_data)
            result.compose_projects = self._writer.write_compose_projects([compose_project])[
                "total_written"
            ]

        compose_services = self._model_list(raw_data.get("compose_services", []), ComposeService)
        if compose_services:
            result.compose_services = self._writer.write_compose_services(compose_services)[
                "total_written"
            ]

        compose_networks = self._model_list(raw_data.get("compose_networks", []), ComposeNetwork)
        if compose_networks:
            result.compose_networks = self._writer.write_compose_networks(compose_networks)[
                "total_written"
            ]

        compose_volumes = self._model_list(raw_data.get("compose_volumes", []), ComposeVolume)
        if compose_volumes:
            result.compose_volumes = self._writer.write_compose_volumes(compose_volumes)[
                "total_written"
            ]

        port_bindings = self._model_list(raw_data.get("port_bindings", []), PortBinding)
        if port_bindings:
            result.port_bindings = self._writer.write_port_bindings(port_bindings)["total_written"]

        env_vars = self._model_list(raw_data.get("environment_variables", []), EnvironmentVariable)
        if env_vars:
            result.environment_variables = self._writer.write_environment_variables(env_vars)[
                "total_written"
            ]

        dependencies = self._model_list(raw_data.get("service_dependencies", []), ServiceDependency)
        if dependencies:
            result.service_dependencies = self._writer.write_service_dependencies(dependencies)[
                "total_written"
            ]

        image_details = self._model_list(raw_data.get("image_details", []), ImageDetails)
        if image_details:
            result.image_details = self._writer.write_image_details(image_details)["total_written"]

        health_checks = self._model_list(raw_data.get("health_checks", []), HealthCheck)
        if health_checks:
            result.health_checks = self._writer.write_health_checks(health_checks)["total_written"]

        build_contexts = self._model_list(raw_data.get("build_contexts", []), BuildContext)
        if build_contexts:
            result.build_contexts = self._writer.write_build_contexts(build_contexts)[
                "total_written"
            ]

        device_mappings = self._model_list(raw_data.get("device_mappings", []), DeviceMapping)
        if device_mappings:
            result.device_mappings = self._writer.write_device_mappings(device_mappings)[
                "total_written"
            ]

        logger.info(
            "docker_compose_ingest.complete file_path=%s nodes=%s relationships=%s",
            file_path,
            result.total_nodes,
            result.total_relationships,
        )
        return result

    @staticmethod
    def _model_list(
        raw_items: Sequence[dict[str, object]],
        model_cls: type[T],
    ) -> list[T]:
        """Helper to convert dictionaries into Pydantic models."""
        return [model_cls.model_validate(item) for item in raw_items]
