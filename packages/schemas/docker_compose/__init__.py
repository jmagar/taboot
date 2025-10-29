"""Docker Compose entity schemas.

This module contains Pydantic models for all Docker Compose entities extracted
from docker-compose.yaml files.

Entities:
- ComposeFile: Root Docker Compose file entity
- ComposeProject: Project configuration
- ComposeService: Service definition
- ComposeNetwork: Network configuration
- ComposeVolume: Volume definition
- PortBinding: Port mapping (host:container)
- EnvironmentVariable: Environment variable declaration
- ServiceDependency: Service dependency relationship
- ImageDetails: Parsed Docker image information
- HealthCheck: Health check configuration
- BuildContext: Build configuration
- DeviceMapping: Device mapping (host device to container)
"""

from packages.schemas.docker_compose.build_context import BuildContext
from packages.schemas.docker_compose.compose_file import ComposeFile
from packages.schemas.docker_compose.compose_network import ComposeNetwork
from packages.schemas.docker_compose.compose_project import ComposeProject
from packages.schemas.docker_compose.compose_service import ComposeService
from packages.schemas.docker_compose.compose_volume import ComposeVolume
from packages.schemas.docker_compose.device_mapping import DeviceMapping
from packages.schemas.docker_compose.environment_variable import EnvironmentVariable
from packages.schemas.docker_compose.health_check import HealthCheck
from packages.schemas.docker_compose.image_details import ImageDetails
from packages.schemas.docker_compose.port_binding import PortBinding
from packages.schemas.docker_compose.service_dependency import ServiceDependency

__all__ = [
    "BuildContext",
    "ComposeFile",
    "ComposeNetwork",
    "ComposeProject",
    "ComposeService",
    "ComposeVolume",
    "DeviceMapping",
    "EnvironmentVariable",
    "HealthCheck",
    "ImageDetails",
    "PortBinding",
    "ServiceDependency",
]
