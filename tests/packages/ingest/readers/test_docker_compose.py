"""Integration tests for DockerComposeReader with new entity types.

Tests extraction of all 12 Docker Compose entity types:
1. ComposeFile
2. ComposeProject
3. ComposeService
4. ComposeNetwork
5. ComposeVolume
6. PortBinding
7. EnvironmentVariable
8. ServiceDependency
9. ImageDetails
10. HealthCheck
11. BuildContext
12. DeviceMapping

Following TDD methodology (RED-GREEN-REFACTOR).
"""

from pathlib import Path

import pytest


class TestDockerComposeReaderEntities:
    """Integration tests for DockerComposeReader outputting new entity types."""

    @pytest.fixture
    def comprehensive_compose_yaml(self, tmp_path: Path) -> Path:
        """Create a comprehensive docker-compose.yaml covering all entity types.

        Args:
            tmp_path: pytest temporary directory fixture.

        Returns:
            Path: Path to the created docker-compose.yaml file.
        """
        compose_content = """
version: '3.8'
name: test-project

networks:
  frontend:
    driver: bridge
    ipam:
      driver: default
      config:
        - subnet: 172.28.0.0/16
          gateway: 172.28.0.1
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
        VERSION: "1.0.0"
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
    networks:
      - frontend
    restart: unless-stopped
    cpus: 2.0
    memory: 2048m
    user: nginx
    working_dir: /app
    hostname: web.local
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
    networks:
      - frontend
      - backend
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
    networks:
      - backend

  cache:
    image: redis:7
    ports:
      - "6379:6379"
    networks:
      - backend

  gpu-service:
    image: tensorflow/tensorflow:latest-gpu
    devices:
      - /dev/nvidia0:/dev/nvidia0:rwm
      - /dev/nvidiactl:/dev/nvidiactl:rwm
"""
        compose_file = tmp_path / "docker-compose.yaml"
        compose_file.write_text(compose_content)
        return compose_file

    def test_reader_extracts_compose_file_entity(self, comprehensive_compose_yaml: Path) -> None:
        """Test that DockerComposeReader extracts ComposeFile entity."""
        from packages.ingest.readers.docker_compose import DockerComposeReader

        reader = DockerComposeReader()
        result = reader.load_data(str(comprehensive_compose_yaml))

        # Should have compose_file entity
        assert "compose_file" in result
        compose_file = result["compose_file"]

        # Verify ComposeFile fields
        assert compose_file["file_path"] == str(comprehensive_compose_yaml)
        assert compose_file["version"] == "3.8"
        assert compose_file["project_name"] == "test-project"

        # Verify temporal fields
        assert "created_at" in compose_file
        assert "updated_at" in compose_file

        # Verify extraction metadata
        assert compose_file["extraction_tier"] == "A"
        assert compose_file["extraction_method"] == "docker_compose_reader"
        assert compose_file["confidence"] == 1.0
        assert "extractor_version" in compose_file

    def test_reader_extracts_compose_project_entity(
        self, comprehensive_compose_yaml: Path
    ) -> None:
        """Test that DockerComposeReader extracts ComposeProject entity."""
        from packages.ingest.readers.docker_compose import DockerComposeReader

        reader = DockerComposeReader()
        result = reader.load_data(str(comprehensive_compose_yaml))

        # Should have compose_project entity
        assert "compose_project" in result
        compose_project = result["compose_project"]

        # Verify ComposeProject fields
        assert compose_project["name"] == "test-project"
        assert compose_project["version"] == "3.8"
        assert compose_project["file_path"] == str(comprehensive_compose_yaml)

        # Verify temporal and extraction metadata
        assert "created_at" in compose_project
        assert compose_project["extraction_tier"] == "A"

    def test_reader_extracts_compose_service_entities(
        self, comprehensive_compose_yaml: Path
    ) -> None:
        """Test that DockerComposeReader extracts ComposeService entities."""
        from packages.ingest.readers.docker_compose import DockerComposeReader

        reader = DockerComposeReader()
        result = reader.load_data(str(comprehensive_compose_yaml))

        # Should have compose_services list
        assert "compose_services" in result
        services = result["compose_services"]

        # Should extract 5 services: web, api, db, cache, gpu-service
        assert len(services) == 5

        # Verify service names
        service_names = {svc["name"] for svc in services}
        assert service_names == {"web", "api", "db", "cache", "gpu-service"}

        # Verify web service details
        web = next(s for s in services if s["name"] == "web")
        assert web["image"] == "nginx:alpine"
        assert web["restart"] == "unless-stopped"
        assert web["cpus"] == 2.0
        assert web["memory"] == "2048m"
        assert web["user"] == "nginx"
        assert web["working_dir"] == "/app"
        assert web["hostname"] == "web.local"

        # Verify extraction metadata on all services
        for service in services:
            assert service["extraction_tier"] == "A"
            assert "created_at" in service

    def test_reader_extracts_compose_network_entities(
        self, comprehensive_compose_yaml: Path
    ) -> None:
        """Test that DockerComposeReader extracts ComposeNetwork entities."""
        from packages.ingest.readers.docker_compose import DockerComposeReader

        reader = DockerComposeReader()
        result = reader.load_data(str(comprehensive_compose_yaml))

        # Should have compose_networks list
        assert "compose_networks" in result
        networks = result["compose_networks"]

        # Should extract 2 networks: frontend, backend
        assert len(networks) == 2

        # Verify network names
        network_names = {net["name"] for net in networks}
        assert network_names == {"frontend", "backend"}

        # Verify frontend network details
        frontend = next(n for n in networks if n["name"] == "frontend")
        assert frontend["driver"] == "bridge"
        assert frontend["external"] is None or frontend["external"] is False
        assert "ipam_config" in frontend
        assert frontend["ipam_config"] is not None

        # Verify backend network details
        backend = next(n for n in networks if n["name"] == "backend")
        assert backend["driver"] == "overlay"
        assert backend["external"] is True

    def test_reader_extracts_compose_volume_entities(
        self, comprehensive_compose_yaml: Path
    ) -> None:
        """Test that DockerComposeReader extracts ComposeVolume entities."""
        from packages.ingest.readers.docker_compose import DockerComposeReader

        reader = DockerComposeReader()
        result = reader.load_data(str(comprehensive_compose_yaml))

        # Should have compose_volumes list
        assert "compose_volumes" in result
        volumes = result["compose_volumes"]

        # Should extract 2 volumes: db-data, app-logs
        assert len(volumes) == 2

        # Verify volume names
        volume_names = {vol["name"] for vol in volumes}
        assert volume_names == {"db-data", "app-logs"}

        # Verify app-logs volume details
        app_logs = next(v for v in volumes if v["name"] == "app-logs")
        assert app_logs["driver"] == "local"
        assert "driver_opts" in app_logs
        assert app_logs["driver_opts"] is not None

    def test_reader_extracts_port_binding_entities(
        self, comprehensive_compose_yaml: Path
    ) -> None:
        """Test that DockerComposeReader extracts PortBinding entities."""
        from packages.ingest.readers.docker_compose import DockerComposeReader

        reader = DockerComposeReader()
        result = reader.load_data(str(comprehensive_compose_yaml))

        # Should have port_bindings list
        assert "port_bindings" in result
        port_bindings = result["port_bindings"]

        # web: 2 ports, api: 1 port, db: 1 port, cache: 1 port = 5 total
        assert len(port_bindings) >= 5

        # Verify web port bindings exist
        web_ports = [pb for pb in port_bindings if pb.get("service_name") == "web"]
        assert len(web_ports) >= 2

        # Check port details
        port_numbers = {pb["container_port"] for pb in web_ports}
        assert 80 in port_numbers
        assert 443 in port_numbers

        # Verify protocol field exists
        for pb in port_bindings:
            assert "protocol" in pb
            assert pb["protocol"] in ["tcp", "udp"] or pb["protocol"] is None

    def test_reader_extracts_environment_variable_entities(
        self, comprehensive_compose_yaml: Path
    ) -> None:
        """Test that DockerComposeReader extracts EnvironmentVariable entities."""
        from packages.ingest.readers.docker_compose import DockerComposeReader

        reader = DockerComposeReader()
        result = reader.load_data(str(comprehensive_compose_yaml))

        # Should have environment_variables list
        assert "environment_variables" in result
        env_vars = result["environment_variables"]

        # Should have multiple env vars from web, api, db services
        assert len(env_vars) >= 6

        # Verify web env vars
        web_envs = [ev for ev in env_vars if ev["service_name"] == "web"]
        assert len(web_envs) == 2
        web_env_keys = {ev["key"] for ev in web_envs}
        assert web_env_keys == {"NGINX_HOST", "NGINX_PORT"}

        # Verify api env vars
        api_envs = [ev for ev in env_vars if ev["service_name"] == "api"]
        assert len(api_envs) == 2
        api_env_keys = {ev["key"] for ev in api_envs}
        assert api_env_keys == {"DATABASE_URL", "REDIS_URL"}

        # Verify extraction metadata
        for ev in env_vars:
            assert ev["extraction_tier"] == "A"
            assert "created_at" in ev

    def test_reader_extracts_service_dependency_entities(
        self, comprehensive_compose_yaml: Path
    ) -> None:
        """Test that DockerComposeReader extracts ServiceDependency entities."""
        from packages.ingest.readers.docker_compose import DockerComposeReader

        reader = DockerComposeReader()
        result = reader.load_data(str(comprehensive_compose_yaml))

        # Should have service_dependencies list
        assert "service_dependencies" in result
        deps = result["service_dependencies"]

        # web depends on api and cache, api depends on db = 3 total
        assert len(deps) >= 3

        # Verify web dependencies
        web_deps = [d for d in deps if d["source_service"] == "web"]
        assert len(web_deps) == 2

        web_targets = {d["target_service"] for d in web_deps}
        assert web_targets == {"api", "cache"}

        # Check for conditions
        api_dep = next(d for d in web_deps if d["target_service"] == "api")
        assert api_dep["condition"] == "service_healthy"

        cache_dep = next(d for d in web_deps if d["target_service"] == "cache")
        assert cache_dep["condition"] == "service_started"

    def test_reader_extracts_image_details_entities(
        self, comprehensive_compose_yaml: Path
    ) -> None:
        """Test that DockerComposeReader extracts ImageDetails entities."""
        from packages.ingest.readers.docker_compose import DockerComposeReader

        reader = DockerComposeReader()
        result = reader.load_data(str(comprehensive_compose_yaml))

        # Should have image_details list
        assert "image_details" in result
        images = result["image_details"]

        # Should have 5 images (one per service)
        assert len(images) == 5

        # Verify nginx image details
        nginx_image = next(img for img in images if img["image_name"] == "nginx")
        assert nginx_image["tag"] == "alpine"

        # Verify myapp/api image details
        api_image = next(img for img in images if img["image_name"] == "myapp/api")
        assert api_image["tag"] == "v1.2.3"

        # Verify postgres image details
        postgres_image = next(img for img in images if img["image_name"] == "postgres")
        assert postgres_image["tag"] == "15"

    def test_reader_extracts_health_check_entities(
        self, comprehensive_compose_yaml: Path
    ) -> None:
        """Test that DockerComposeReader extracts HealthCheck entities."""
        from packages.ingest.readers.docker_compose import DockerComposeReader

        reader = DockerComposeReader()
        result = reader.load_data(str(comprehensive_compose_yaml))

        # Should have health_checks list
        assert "health_checks" in result
        health_checks = result["health_checks"]

        # web and api have health checks = 2 total
        assert len(health_checks) == 2

        # Verify web health check
        web_health = next(
            hc for hc in health_checks if hc.get("service_name") == "web"
        )
        assert "CMD-SHELL curl" in web_health["test"]
        assert web_health["interval"] == "30s"
        assert web_health["timeout"] == "10s"
        assert web_health["retries"] == 3
        assert web_health["start_period"] == "60s"

        # Verify api health check
        api_health = next(
            hc for hc in health_checks if hc.get("service_name") == "api"
        )
        assert "curl" in api_health["test"]
        assert api_health["interval"] == "15s"
        assert api_health["timeout"] == "5s"
        assert api_health["retries"] == 5

    def test_reader_extracts_build_context_entities(
        self, comprehensive_compose_yaml: Path
    ) -> None:
        """Test that DockerComposeReader extracts BuildContext entities."""
        from packages.ingest.readers.docker_compose import DockerComposeReader

        reader = DockerComposeReader()
        result = reader.load_data(str(comprehensive_compose_yaml))

        # Should have build_contexts list
        assert "build_contexts" in result
        builds = result["build_contexts"]

        # Only web service has build config = 1 total
        assert len(builds) == 1

        # Verify web build context
        web_build = builds[0]
        assert web_build["service_name"] == "web"
        assert web_build["context_path"] == "./web"
        assert web_build["dockerfile"] == "Dockerfile.prod"
        assert web_build["target"] == "production"
        assert "args" in web_build
        assert web_build["args"]["NODE_ENV"] == "production"
        assert web_build["args"]["VERSION"] == "1.0.0"

    def test_reader_extracts_device_mapping_entities(
        self, comprehensive_compose_yaml: Path
    ) -> None:
        """Test that DockerComposeReader extracts DeviceMapping entities."""
        from packages.ingest.readers.docker_compose import DockerComposeReader

        reader = DockerComposeReader()
        result = reader.load_data(str(comprehensive_compose_yaml))

        # Should have device_mappings list
        assert "device_mappings" in result
        devices = result["device_mappings"]

        # gpu-service has 2 device mappings = 2 total
        assert len(devices) == 2

        # Verify device mapping details
        gpu_devices = [d for d in devices if d["service_name"] == "gpu-service"]
        assert len(gpu_devices) == 2

        # Check specific devices
        device_paths = {d["host_device"] for d in gpu_devices}
        assert device_paths == {"/dev/nvidia0", "/dev/nvidiactl"}

        # Verify permissions
        for device in gpu_devices:
            assert device["permissions"] == "rwm"
            assert device["extraction_tier"] == "A"

    def test_reader_validates_all_entities_have_required_fields(
        self, comprehensive_compose_yaml: Path
    ) -> None:
        """Test that all extracted entities have required temporal and extraction fields."""
        from packages.ingest.readers.docker_compose import DockerComposeReader

        reader = DockerComposeReader()
        result = reader.load_data(str(comprehensive_compose_yaml))

        # Define entity lists to check
        entity_lists = [
            "compose_services",
            "compose_networks",
            "compose_volumes",
            "port_bindings",
            "environment_variables",
            "service_dependencies",
            "image_details",
            "health_checks",
            "build_contexts",
            "device_mappings",
        ]

        # Check each entity type
        for entity_type in entity_lists:
            entities = result[entity_type]
            for entity in entities:
                # Temporal fields
                assert "created_at" in entity
                assert "updated_at" in entity

                # Extraction metadata
                assert "extraction_tier" in entity
                assert entity["extraction_tier"] in ["A", "B", "C"]
                assert "extraction_method" in entity
                assert "confidence" in entity
                assert 0.0 <= entity["confidence"] <= 1.0
                assert "extractor_version" in entity

    def test_reader_maintains_service_name_associations(
        self, comprehensive_compose_yaml: Path
    ) -> None:
        """Test that entities are properly associated with their service names."""
        from packages.ingest.readers.docker_compose import DockerComposeReader

        reader = DockerComposeReader()
        result = reader.load_data(str(comprehensive_compose_yaml))

        # Check port_bindings have service_name
        for pb in result["port_bindings"]:
            assert "service_name" in pb
            assert pb["service_name"] in ["web", "api", "db", "cache", "gpu-service"]

        # Check environment_variables have service_name
        for ev in result["environment_variables"]:
            assert "service_name" in ev
            assert ev["service_name"] in ["web", "api", "db"]

        # Check health_checks have service_name
        for hc in result["health_checks"]:
            assert "service_name" in hc
            assert hc["service_name"] in ["web", "api"]

        # Check build_contexts have service_name
        for bc in result["build_contexts"]:
            assert "service_name" in bc
            assert bc["service_name"] == "web"

        # Check device_mappings have service_name
        for dm in result["device_mappings"]:
            assert "service_name" in dm
            assert dm["service_name"] == "gpu-service"
