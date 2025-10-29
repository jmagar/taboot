"""Docker Compose YAML reader for Taboot platform.

Parses docker-compose.yaml files and extracts all 12 entity types:
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

Per Phase 4 tasks: Extracts structured sources to Pydantic entity models.
"""

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Extractor version for all entities
EXTRACTOR_VERSION = "1.0.0"


class DockerComposeError(Exception):
    """Base exception for DockerComposeReader errors."""

    pass


class InvalidYAMLError(DockerComposeError):
    """Raised when YAML file is malformed."""

    pass


class InvalidPortError(DockerComposeError):
    """Raised when port number is out of valid range."""

    pass


class DockerComposeReader:
    """Docker Compose YAML reader.

    Parses docker-compose.yaml files and extracts all 12 entity types.
    """

    def __init__(self) -> None:
        """Initialize DockerComposeReader."""
        logger.info("Initialized DockerComposeReader")

    def load_data(self, file_path: str) -> dict[str, Any]:
        """Load and parse docker-compose.yaml file.

        Args:
            file_path: Path to docker-compose.yaml file.

        Returns:
            dict[str, Any]: Structured data with all 12 entity types:
                {
                    "compose_file": {...},
                    "compose_project": {...},
                    "compose_services": [...],
                    "compose_networks": [...],
                    "compose_volumes": [...],
                    "port_bindings": [...],
                    "environment_variables": [...],
                    "service_dependencies": [...],
                    "image_details": [...],
                    "health_checks": [...],
                    "build_contexts": [...],
                    "device_mappings": [...],
                }

        Raises:
            ValueError: If file_path is empty.
            DockerComposeError: If file not found.
            InvalidYAMLError: If YAML is malformed.
            InvalidPortError: If port number is invalid.
        """
        if not file_path:
            raise ValueError("file_path cannot be empty")

        path = Path(file_path)
        if not path.exists():
            raise DockerComposeError(f"File not found: {file_path}")

        logger.info(f"Loading docker-compose.yaml from {file_path}")

        # Parse YAML
        try:
            with path.open("r") as f:
                compose_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise InvalidYAMLError(f"Invalid YAML in {file_path}: {e}") from e

        if not compose_data or not isinstance(compose_data, dict):
            raise InvalidYAMLError(f"Invalid compose file structure: {file_path}")

        # Get current timestamp for entity creation
        now = datetime.now(UTC)

        # Extract top-level metadata
        version = compose_data.get("version")
        project_name = compose_data.get("name")

        # Initialize result structure with all 12 entity types
        result: dict[str, Any] = {
            "compose_file": self._create_compose_file_entity(file_path, version, project_name, now),
            "compose_project": self._create_compose_project_entity(
                file_path, version, project_name, now
            ),
            "compose_services": [],
            "compose_networks": [],
            "compose_volumes": [],
            "port_bindings": [],
            "environment_variables": [],
            "service_dependencies": [],
            "image_details": [],
            "health_checks": [],
            "build_contexts": [],
            "device_mappings": [],
        }

        # Extract networks
        networks_data = compose_data.get("networks", {})
        if isinstance(networks_data, dict):
            for network_name, network_config in networks_data.items():
                result["compose_networks"].append(
                    self._create_compose_network_entity(network_name, network_config, now)
                )

        # Extract volumes
        volumes_data = compose_data.get("volumes", {})
        if isinstance(volumes_data, dict):
            for volume_name, volume_config in volumes_data.items():
                result["compose_volumes"].append(
                    self._create_compose_volume_entity(volume_name, volume_config, now)
                )

        # Extract services and related entities
        services_data = compose_data.get("services", {})
        if not isinstance(services_data, dict):
            raise InvalidYAMLError("'services' must be a dictionary")

        for service_name, service_config in services_data.items():
            if not isinstance(service_config, dict):
                logger.warning(f"Skipping invalid service config for {service_name}")
                continue

            # Extract service entity
            result["compose_services"].append(
                self._create_compose_service_entity(service_name, service_config, now)
            )

            # Extract image details
            image = service_config.get("image", "")
            if image:
                result["image_details"].append(
                    self._create_image_details_entity(image, service_name, now)
                )

            # Extract port bindings
            ports = service_config.get("ports", [])
            if isinstance(ports, list):
                for port_mapping in ports:
                    port_binding = self._create_port_binding_entity(
                        port_mapping, service_name, now
                    )
                    if port_binding:
                        result["port_bindings"].append(port_binding)

            # Extract environment variables
            environment = service_config.get("environment", [])
            if isinstance(environment, dict):
                # Dict format: {KEY: VALUE}
                for key, value in environment.items():
                    result["environment_variables"].append(
                        self._create_environment_variable_entity(
                            key, str(value), service_name, now
                        )
                    )
            elif isinstance(environment, list):
                # List format: ["KEY=VALUE", "KEY2=VALUE2"]
                for env_item in environment:
                    if isinstance(env_item, str) and "=" in env_item:
                        key, value = env_item.split("=", 1)
                        result["environment_variables"].append(
                            self._create_environment_variable_entity(key, value, service_name, now)
                        )

            # Extract service dependencies
            depends_on = service_config.get("depends_on", [])
            if isinstance(depends_on, list):
                # Simple list format: ["service1", "service2"]
                for target in depends_on:
                    result["service_dependencies"].append(
                        self._create_service_dependency_entity(
                            service_name, target, None, now
                        )
                    )
            elif isinstance(depends_on, dict):
                # Extended format: {service1: {condition: ...}}
                for target, dep_config in depends_on.items():
                    condition = None
                    if isinstance(dep_config, dict):
                        condition = dep_config.get("condition")
                    result["service_dependencies"].append(
                        self._create_service_dependency_entity(
                            service_name, target, condition, now
                        )
                    )

            # Extract health check
            healthcheck = service_config.get("healthcheck")
            if healthcheck and isinstance(healthcheck, dict):
                result["health_checks"].append(
                    self._create_health_check_entity(healthcheck, service_name, now)
                )

            # Extract build context
            build = service_config.get("build")
            if build:
                result["build_contexts"].append(
                    self._create_build_context_entity(build, service_name, now)
                )

            # Extract device mappings
            devices = service_config.get("devices", [])
            if isinstance(devices, list):
                for device_mapping in devices:
                    device = self._create_device_mapping_entity(device_mapping, service_name, now)
                    if device:
                        result["device_mappings"].append(device)

        logger.info(
            f"Extracted {len(result['compose_services'])} services, "
            f"{len(result['compose_networks'])} networks, "
            f"{len(result['compose_volumes'])} volumes, "
            f"{len(result['port_bindings'])} port bindings, "
            f"{len(result['environment_variables'])} environment variables, "
            f"{len(result['service_dependencies'])} dependencies, "
            f"{len(result['image_details'])} images, "
            f"{len(result['health_checks'])} health checks, "
            f"{len(result['build_contexts'])} build contexts, "
            f"{len(result['device_mappings'])} device mappings"
        )

        return result

    def _create_base_metadata(self, now: datetime) -> dict[str, Any]:
        """Create base temporal and extraction metadata for all entities.

        Args:
            now: Current timestamp.

        Returns:
            dict[str, Any]: Base metadata fields.
        """
        return {
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "source_timestamp": None,
            "extraction_tier": "A",
            "extraction_method": "docker_compose_reader",
            "confidence": 1.0,
            "extractor_version": EXTRACTOR_VERSION,
        }

    def _create_compose_file_entity(
        self, file_path: str, version: str | None, project_name: str | None, now: datetime
    ) -> dict[str, Any]:
        """Create ComposeFile entity."""
        return {
            "file_path": file_path,
            "version": version,
            "project_name": project_name,
            **self._create_base_metadata(now),
        }

    def _create_compose_project_entity(
        self, file_path: str, version: str | None, project_name: str | None, now: datetime
    ) -> dict[str, Any]:
        """Create ComposeProject entity."""
        # If no project name, derive from directory name
        if not project_name:
            project_name = Path(file_path).parent.name or "default"

        return {
            "name": project_name,
            "version": version,
            "file_path": file_path,
            **self._create_base_metadata(now),
        }

    def _create_compose_service_entity(
        self, service_name: str, service_config: dict[str, Any], now: datetime
    ) -> dict[str, Any]:
        """Create ComposeService entity."""
        # Extract resource limits
        deploy_config = service_config.get("deploy", {})
        resources = deploy_config.get("resources", {}) if isinstance(deploy_config, dict) else {}
        limits = resources.get("limits", {}) if isinstance(resources, dict) else {}

        # Try to get cpus and memory from deploy.resources.limits
        cpus = limits.get("cpus") if isinstance(limits, dict) else None
        memory = limits.get("memory") if isinstance(limits, dict) else None

        # Also check top-level keys (Docker Compose v2 format)
        if cpus is None:
            cpus = service_config.get("cpus")
        if memory is None:
            memory = service_config.get("mem_limit") or service_config.get("memory")

        return {
            "name": service_name,
            "image": service_config.get("image"),
            "command": service_config.get("command"),
            "entrypoint": service_config.get("entrypoint"),
            "restart": service_config.get("restart"),
            "cpus": cpus,
            "memory": memory,
            "user": service_config.get("user"),
            "working_dir": service_config.get("working_dir"),
            "hostname": service_config.get("hostname"),
            **self._create_base_metadata(now),
        }

    def _create_compose_network_entity(
        self, network_name: str, network_config: dict[str, Any] | None, now: datetime
    ) -> dict[str, Any]:
        """Create ComposeNetwork entity."""
        if network_config is None:
            network_config = {}

        # Extract IPAM config if present
        ipam = network_config.get("ipam", {})
        ipam_config = None
        if isinstance(ipam, dict):
            ipam_driver = ipam.get("driver")
            config_list = ipam.get("config", [])
            if config_list and isinstance(config_list, list) and len(config_list) > 0:
                ipam_config = config_list[0]  # Use first config
        else:
            ipam_driver = None

        return {
            "name": network_name,
            "driver": network_config.get("driver"),
            "external": network_config.get("external"),
            "enable_ipv6": network_config.get("enable_ipv6"),
            "ipam_driver": ipam_driver,
            "ipam_config": ipam_config,
            **self._create_base_metadata(now),
        }

    def _create_compose_volume_entity(
        self, volume_name: str, volume_config: dict[str, Any] | None, now: datetime
    ) -> dict[str, Any]:
        """Create ComposeVolume entity."""
        if volume_config is None:
            volume_config = {}

        return {
            "name": volume_name,
            "driver": volume_config.get("driver"),
            "external": volume_config.get("external"),
            "driver_opts": volume_config.get("driver_opts"),
            **self._create_base_metadata(now),
        }

    def _create_port_binding_entity(
        self, port_mapping: str | int, service_name: str, now: datetime
    ) -> dict[str, Any] | None:
        """Create PortBinding entity."""
        host_ip = None
        host_port = None
        container_port = None
        protocol = "tcp"

        if isinstance(port_mapping, int):
            # Direct port number
            container_port = port_mapping
            host_port = port_mapping
        elif isinstance(port_mapping, str):
            # Parse string format: "host:container" or "host:container/protocol"
            # or "ip:host:container"
            parts = port_mapping.split(":")

            if len(parts) == 1:
                # Just "8080" or "8080/tcp"
                port_part = parts[0]
                if "/" in port_part:
                    port_str, protocol = port_part.split("/", 1)
                    protocol = protocol.lower()
                    try:
                        container_port = int(port_str)
                        host_port = container_port
                    except ValueError:
                        logger.warning(f"Invalid port number: {port_part}")
                        return None
                else:
                    try:
                        container_port = int(port_part)
                        host_port = container_port
                    except ValueError:
                        logger.warning(f"Invalid port number: {port_part}")
                        return None
            elif len(parts) == 2:
                # "host:container" format
                host_port_str = parts[0].strip()
                container_part = parts[1].strip()

                # Parse container port and protocol
                if "/" in container_part:
                    container_port_str, protocol = container_part.split("/", 1)
                    protocol = protocol.lower()
                else:
                    container_port_str = container_part

                try:
                    host_port = int(host_port_str)
                    container_port = int(container_port_str)
                except ValueError:
                    logger.warning(f"Invalid port mapping: {port_mapping}")
                    return None
            elif len(parts) == 3:
                # "ip:host:container" format
                host_ip = parts[0].strip()
                host_port_str = parts[1].strip()
                container_part = parts[2].strip()

                # Parse container port and protocol
                if "/" in container_part:
                    container_port_str, protocol = container_part.split("/", 1)
                    protocol = protocol.lower()
                else:
                    container_port_str = container_part

                try:
                    host_port = int(host_port_str)
                    container_port = int(container_port_str)
                except ValueError:
                    logger.warning(f"Invalid port mapping: {port_mapping}")
                    return None
            else:
                logger.warning(f"Invalid port mapping format: {port_mapping}")
                return None
        else:
            logger.warning(f"Unsupported port mapping type: {type(port_mapping)}")
            return None

        # Validate port range
        if container_port and (container_port < 1 or container_port > 65535):
            raise InvalidPortError(f"Port {container_port} must be between 1 and 65535")
        if host_port and (host_port < 1 or host_port > 65535):
            raise InvalidPortError(f"Port {host_port} must be between 1 and 65535")

        return {
            "host_ip": host_ip,
            "host_port": host_port,
            "container_port": container_port,
            "protocol": protocol,
            "service_name": service_name,
            **self._create_base_metadata(now),
        }

    def _create_environment_variable_entity(
        self, key: str, value: str, service_name: str, now: datetime
    ) -> dict[str, Any]:
        """Create EnvironmentVariable entity."""
        return {
            "key": key,
            "value": value,
            "service_name": service_name,
            **self._create_base_metadata(now),
        }

    def _create_service_dependency_entity(
        self, source_service: str, target_service: str, condition: str | None, now: datetime
    ) -> dict[str, Any]:
        """Create ServiceDependency entity."""
        return {
            "source_service": source_service,
            "target_service": target_service,
            "condition": condition,
            **self._create_base_metadata(now),
        }

    def _create_image_details_entity(
        self, image: str, service_name: str, now: datetime
    ) -> dict[str, Any]:
        """Create ImageDetails entity."""
        # Parse image string: [registry/]name[:tag][@digest]
        registry = None
        image_name = image
        tag = None
        digest = None

        # Check for digest
        if "@" in image:
            image, digest = image.split("@", 1)

        # Check for tag
        if ":" in image:
            parts = image.rsplit(":", 1)
            image_name = parts[0]
            tag = parts[1]

        # Check for registry (contains slash and not just namespace/repo)
        if "/" in image_name:
            parts = image_name.split("/")
            # If first part contains a dot or port, it's a registry
            if "." in parts[0] or ":" in parts[0]:
                registry = parts[0]
                image_name = "/".join(parts[1:])

        return {
            "image_name": image_name,
            "tag": tag,
            "registry": registry,
            "digest": digest,
            "service_name": service_name,
            **self._create_base_metadata(now),
        }

    def _create_health_check_entity(
        self, healthcheck: dict[str, Any], service_name: str, now: datetime
    ) -> dict[str, Any]:
        """Create HealthCheck entity."""
        # Test can be a list or string
        test = healthcheck.get("test")
        if isinstance(test, list):
            test = " ".join(test)

        return {
            "test": test or "",
            "interval": healthcheck.get("interval"),
            "timeout": healthcheck.get("timeout"),
            "retries": healthcheck.get("retries"),
            "start_period": healthcheck.get("start_period"),
            "service_name": service_name,
            **self._create_base_metadata(now),
        }

    def _create_build_context_entity(
        self, build: str | dict[str, Any], service_name: str, now: datetime
    ) -> dict[str, Any]:
        """Create BuildContext entity."""
        if isinstance(build, str):
            # Simple string format: just context path
            context_path = build
            dockerfile = None
            target = None
            args = None
        elif isinstance(build, dict):
            # Extended format
            context_path = build.get("context", ".")
            dockerfile = build.get("dockerfile")
            target = build.get("target")
            args = build.get("args")
        else:
            context_path = "."
            dockerfile = None
            target = None
            args = None

        return {
            "context_path": context_path,
            "dockerfile": dockerfile,
            "target": target,
            "args": args,
            "service_name": service_name,
            **self._create_base_metadata(now),
        }

    def _create_device_mapping_entity(
        self, device_mapping: str, service_name: str, now: datetime
    ) -> dict[str, Any] | None:
        """Create DeviceMapping entity."""
        if not isinstance(device_mapping, str):
            logger.warning(f"Unsupported device mapping type: {type(device_mapping)}")
            return None

        # Parse format: "host_device:container_device:permissions"
        parts = device_mapping.split(":")

        if len(parts) < 2:
            logger.warning(f"Invalid device mapping format: {device_mapping}")
            return None

        host_device = parts[0]
        container_device = parts[1]
        permissions = parts[2] if len(parts) >= 3 else None

        return {
            "host_device": host_device,
            "container_device": container_device,
            "permissions": permissions,
            "service_name": service_name,
            **self._create_base_metadata(now),
        }
