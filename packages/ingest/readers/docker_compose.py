"""Docker Compose YAML reader for Taboot platform.

Parses docker-compose.yaml files and extracts:
- Service nodes (name, image, version)
- DEPENDS_ON relationships
- BINDS relationships (port bindings)

Per data-model.md: Extracts structured sources to nodes/edges deterministically.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


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

    Parses docker-compose.yaml files and extracts Service nodes,
    DEPENDS_ON relationships, and BINDS relationships.
    """

    def __init__(self) -> None:
        """Initialize DockerComposeReader."""
        logger.info("Initialized DockerComposeReader")

    def load_data(self, file_path: str) -> dict[str, Any]:
        """Load and parse docker-compose.yaml file.

        Args:
            file_path: Path to docker-compose.yaml file.

        Returns:
            dict[str, Any]: Structured data with services and relationships.
                {
                    "services": [
                        {
                            "name": str,
                            "image": str,
                            "version": str,
                        },
                        ...
                    ],
                    "relationships": [
                        {
                            "type": "DEPENDS_ON" | "BINDS",
                            "source": str,
                            "target": str,  # for DEPENDS_ON
                            "port": int,    # for BINDS
                            "protocol": str # for BINDS
                        },
                        ...
                    ]
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

        # Extract services
        services_data = compose_data.get("services", {})
        if not isinstance(services_data, dict):
            raise InvalidYAMLError("'services' must be a dictionary")

        services: list[dict[str, Any]] = []
        relationships: list[dict[str, Any]] = []

        for service_name, service_config in services_data.items():
            if not isinstance(service_config, dict):
                logger.warning(f"Skipping invalid service config for {service_name}")
                continue

            # Extract service node
            image = service_config.get("image", "")
            version = self._extract_version_from_image(image)

            services.append(
                {
                    "name": service_name,
                    "image": image,
                    "version": version,
                }
            )

            # Extract DEPENDS_ON relationships
            depends_on = service_config.get("depends_on", [])
            if isinstance(depends_on, list):
                for target in depends_on:
                    relationships.append(
                        {
                            "type": "DEPENDS_ON",
                            "source": service_name,
                            "target": target,
                        }
                    )
            elif isinstance(depends_on, dict):
                # Docker Compose v3+ format: depends_on can be dict
                for target in depends_on:
                    relationships.append(
                        {
                            "type": "DEPENDS_ON",
                            "source": service_name,
                            "target": target,
                        }
                    )

            # Extract BINDS relationships (port bindings)
            ports = service_config.get("ports", [])
            if isinstance(ports, list):
                for port_mapping in ports:
                    port_info = self._parse_port_mapping(port_mapping)
                    if port_info:
                        relationships.append(
                            {
                                "type": "BINDS",
                                "source": service_name,
                                "port": port_info["port"],
                                "protocol": port_info["protocol"],
                            }
                        )

        logger.info(f"Extracted {len(services)} services and {len(relationships)} relationships")

        return {
            "services": services,
            "relationships": relationships,
        }

    def _extract_version_from_image(self, image: str) -> str:
        """Extract version tag from Docker image string.

        Args:
            image: Docker image string (e.g., "nginx:latest", "myapp/api:v1.2.3").

        Returns:
            str: Version tag (e.g., "latest", "v1.2.3", "15").
        """
        if not image:
            return ""

        # Split on colon to get tag
        if ":" in image:
            return image.split(":")[-1]

        # No tag specified - default to empty
        return ""

    def _parse_port_mapping(self, port_mapping: str | int) -> dict[str, Any] | None:
        """Parse port mapping string into port number and protocol.

        Args:
            port_mapping: Port mapping string (e.g., "80:80", "8080:8080/tcp",
                          "53:53/udp") or integer (e.g., 8080).

        Returns:
            dict[str, Any] | None: Port info with 'port' and 'protocol' keys,
                                   or None if invalid.

        Raises:
            InvalidPortError: If port number is out of valid range (1-65535).
        """
        if isinstance(port_mapping, int):
            # Direct port number
            port = port_mapping
            protocol = "tcp"
        elif isinstance(port_mapping, str):
            # Parse string format: "host:container" or "host:container/protocol"
            parts = port_mapping.split(":")
            if len(parts) < 2:
                logger.warning(f"Invalid port mapping format: {port_mapping}")
                return None

            # Get host port (first part)
            host_port = parts[0].strip()

            # Get container port and optional protocol (second part)
            container_part = parts[1].strip()

            # Check for protocol suffix (e.g., "8080/tcp")
            if "/" in container_part:
                _, protocol = container_part.split("/", 1)
                protocol = protocol.lower()
            else:
                protocol = "tcp"

            # Use host port for BINDS relationship
            try:
                port = int(host_port)
            except ValueError:
                logger.warning(f"Invalid port number in mapping: {port_mapping}")
                return None
        else:
            logger.warning(f"Unsupported port mapping type: {type(port_mapping)}")
            return None

        # Validate port range
        if port < 1 or port > 65535:
            raise InvalidPortError(f"Port {port} must be between 1 and 65535")

        return {
            "port": port,
            "protocol": protocol,
        }
