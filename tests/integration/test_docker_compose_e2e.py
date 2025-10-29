"""End-to-end test for Docker Compose ingestion use case."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List

from packages.core.use_cases.ingest_docker_compose import (
    DockerComposeIngestionResult,
    IngestDockerComposeUseCase,
)
from packages.ingest.readers.docker_compose import DockerComposeReader


class RecordingDockerComposeWriter:
    """Lightweight writer stub that records entities passed to each write method."""

    def __init__(self) -> None:
        self.calls: Dict[str, List[Any]] = {}

    def _record(self, key: str, items: List[Any]) -> Dict[str, int]:
        self.calls[key] = list(items)
        return {
            "total_written": len(items),
            "batches_executed": 1 if items else 0,
        }

    def write_compose_files(self, items: List[Any]) -> Dict[str, int]:
        return self._record("compose_files", items)

    def write_compose_projects(self, items: List[Any]) -> Dict[str, int]:
        return self._record("compose_projects", items)

    def write_compose_services(self, items: List[Any]) -> Dict[str, int]:
        return self._record("compose_services", items)

    def write_compose_networks(self, items: List[Any]) -> Dict[str, int]:
        return self._record("compose_networks", items)

    def write_compose_volumes(self, items: List[Any]) -> Dict[str, int]:
        return self._record("compose_volumes", items)

    def write_port_bindings(self, items: List[Any]) -> Dict[str, int]:
        return self._record("port_bindings", items)

    def write_environment_variables(self, items: List[Any]) -> Dict[str, int]:
        return self._record("environment_variables", items)

    def write_service_dependencies(self, items: List[Any]) -> Dict[str, int]:
        return self._record("service_dependencies", items)

    def write_image_details(self, items: List[Any]) -> Dict[str, int]:
        return self._record("image_details", items)

    def write_health_checks(self, items: List[Any]) -> Dict[str, int]:
        return self._record("health_checks", items)

    def write_build_contexts(self, items: List[Any]) -> Dict[str, int]:
        return self._record("build_contexts", items)

    def write_device_mappings(self, items: List[Any]) -> Dict[str, int]:
        return self._record("device_mappings", items)


def _create_sample_compose_yaml(tmp_path: Path) -> Path:
    """Create a comprehensive docker-compose.yaml for testing."""
    compose_content = """
version: '3.8'
name: sample-project

networks:
  frontend:
    driver: bridge
  backend:
    driver: overlay
    external: true

volumes:
  db-data:
    driver: local
  app-logs:
    driver: local
    driver_opts:
      type: none
      device: /mnt/logs
      o: bind

services:
  web:
    image: nginx:alpine
    build:
      context: ./web
      dockerfile: Dockerfile.prod
      target: production
      args:
        NODE_ENV: production
    ports:
      - "80:80"
      - "443:443/tcp"
    environment:
      - NGINX_HOST=example.com
      - NGINX_PORT=80
    depends_on:
      api:
        condition: service_healthy
      cache:
        condition: service_started
    healthcheck:
      test: "CMD-SHELL curl -f http://localhost/ || exit 1"
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  api:
    image: myapp/api:v1.2.3
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgres://db:5432/app
      - REDIS_URL=redis://cache:6379
    depends_on:
      - db
    healthcheck:
      test: "CMD curl -f http://localhost:4207/health"
      interval: 15s
      timeout: 5s
      retries: 5

  db:
    image: postgres:15
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_PASSWORD=secret
      - POSTGRES_USER=app
    volumes:
      - db-data:/var/lib/postgresql/data

  cache:
    image: redis:7
    ports:
      - "6379:6379"

  gpu-service:
    image: tensorflow/tensorflow:latest-gpu
    devices:
      - /dev/nvidia0:/dev/nvidia0:rwm
      - /dev/nvidiactl:/dev/nvidiactl:rwm
"""
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text(compose_content, encoding="utf-8")
    return compose_file


def test_ingest_docker_compose_use_case_end_to_end(tmp_path: Path) -> None:
    """Ensure use case converts reader output and invokes writer with all entities."""
    compose_path = _create_sample_compose_yaml(tmp_path)
    reader = DockerComposeReader()
    writer = RecordingDockerComposeWriter()

    use_case = IngestDockerComposeUseCase(reader=reader, writer=writer)
    result = use_case.execute(file_path=str(compose_path))

    # Validate counts against fixture
    assert result.compose_files == 1
    assert result.compose_projects == 1
    assert result.compose_services == 5
    assert result.compose_networks == 2
    assert result.compose_volumes == 2
    assert result.port_bindings == 5
    assert result.environment_variables == 6
    assert result.service_dependencies == 3
    assert result.image_details == 5
    assert result.health_checks == 2
    assert result.build_contexts == 1
    assert result.device_mappings == 2
    assert result.total_nodes == 32
    assert result.total_relationships == 3

    # Writer should have received strongly-typed models in each call.
    for key, items in writer.calls.items():
        assert items, f"{key} should receive at least one item"
