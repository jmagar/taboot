"""Tests for DockerComposeWriter.

Tests batched Neo4j writes for all 12 Docker Compose entity types using UNWIND operations.
Follows TDD approach with coverage ≥95%.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from packages.graph.writers.docker_compose_writer import DockerComposeWriter
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


@pytest.fixture
def mock_neo4j_client() -> MagicMock:
    """Create a mock Neo4j client."""
    client = MagicMock()
    session = MagicMock()
    result = MagicMock()
    result.consume.return_value = MagicMock(counters={"nodes_created": 1})
    session.run.return_value = result
    client.session.return_value.__enter__.return_value = session
    client.session.return_value.__exit__.return_value = None
    return client


@pytest.fixture
def writer(mock_neo4j_client: MagicMock) -> DockerComposeWriter:
    """Create DockerComposeWriter instance with mocked client."""
    return DockerComposeWriter(mock_neo4j_client, batch_size=2)


# Test data fixtures
@pytest.fixture
def sample_compose_file() -> ComposeFile:
    """Create sample ComposeFile entity."""
    return ComposeFile(
        file_path="/home/user/docker-compose.yml",
        version="3.8",
        project_name="test-project",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="yaml_parser",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_compose_project() -> ComposeProject:
    """Create sample ComposeProject entity."""
    return ComposeProject(
        name="test-project",
        version="3.8",
        file_path="/home/user/docker-compose.yml",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="yaml_parser",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_compose_service() -> ComposeService:
    """Create sample ComposeService entity."""
    return ComposeService(
        name="web",
        compose_file_path="/home/user/docker-compose.yml",
        image="nginx:alpine",
        restart="unless-stopped",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="yaml_parser",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_compose_network() -> ComposeNetwork:
    """Create sample ComposeNetwork entity."""
    return ComposeNetwork(
        name="backend",
        compose_file_path="/home/user/docker-compose.yml",
        driver="bridge",
        external=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="yaml_parser",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_compose_volume() -> ComposeVolume:
    """Create sample ComposeVolume entity."""
    return ComposeVolume(
        name="data",
        compose_file_path="/home/user/docker-compose.yml",
        driver="local",
        external=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="yaml_parser",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_port_binding() -> PortBinding:
    """Create sample PortBinding entity."""
    return PortBinding(
        compose_file_path="/home/user/docker-compose.yml",
        service_name="web",
        host_ip="0.0.0.0",
        host_port=8080,
        container_port=80,
        protocol="tcp",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="yaml_parser",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_env_var() -> EnvironmentVariable:
    """Create sample EnvironmentVariable entity."""
    return EnvironmentVariable(
        compose_file_path="/home/user/docker-compose.yml",
        key="DATABASE_URL",
        value="postgres://localhost/db",
        service_name="api",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="yaml_parser",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_service_dependency() -> ServiceDependency:
    """Create sample ServiceDependency entity."""
    return ServiceDependency(
        compose_file_path="/home/user/docker-compose.yml",
        source_service="web",
        target_service="api",
        condition="service_started",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="yaml_parser",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_image_details() -> ImageDetails:
    """Create sample ImageDetails entity."""
    return ImageDetails(
        compose_file_path="/home/user/docker-compose.yml",
        service_name="web",
        image_name="nginx",
        tag="alpine",
        registry="docker.io",
        digest=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="yaml_parser",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_health_check() -> HealthCheck:
    """Create sample HealthCheck entity."""
    return HealthCheck(
        compose_file_path="/home/user/docker-compose.yml",
        service_name="web",
        test="curl -f http://localhost/ || exit 1",
        interval="30s",
        timeout="10s",
        retries=3,
        start_period="40s",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="yaml_parser",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_build_context() -> BuildContext:
    """Create sample BuildContext entity."""
    return BuildContext(
        compose_file_path="/home/user/docker-compose.yml",
        service_name="web",
        context_path="./web",
        dockerfile="Dockerfile",
        target="production",
        args={"NODE_ENV": "production"},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="yaml_parser",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_device_mapping() -> DeviceMapping:
    """Create sample DeviceMapping entity."""
    return DeviceMapping(
        compose_file_path="/home/user/docker-compose.yml",
        service_name="web",
        host_device="/dev/video0",
        container_device="/dev/video0",
        permissions="rwm",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="yaml_parser",
        confidence=1.0,
        extractor_version="1.0.0",
    )


# Test cases
class TestDockerComposeWriterInit:
    """Test DockerComposeWriter initialization."""

    def test_init_with_default_batch_size(self, mock_neo4j_client: MagicMock) -> None:
        """Test writer initialization with default batch size."""
        writer = DockerComposeWriter(mock_neo4j_client)
        assert writer.neo4j_client == mock_neo4j_client
        assert writer.batch_size == 2000

    def test_init_with_custom_batch_size(self, mock_neo4j_client: MagicMock) -> None:
        """Test writer initialization with custom batch size."""
        writer = DockerComposeWriter(mock_neo4j_client, batch_size=500)
        assert writer.neo4j_client == mock_neo4j_client
        assert writer.batch_size == 500


class TestWriteComposeFiles:
    """Test write_compose_files method."""

    def test_write_empty_list(self, writer: DockerComposeWriter) -> None:
        """Test writing empty list returns zeros."""
        result = writer.write_compose_files([])
        assert result == {"total_written": 0, "batches_executed": 0}

    def test_write_single_compose_file(
        self, writer: DockerComposeWriter, sample_compose_file: ComposeFile
    ) -> None:
        """Test writing single ComposeFile."""
        result = writer.write_compose_files([sample_compose_file])
        assert result["total_written"] == 1
        assert result["batches_executed"] == 1

    def test_write_multiple_compose_files(
        self, writer: DockerComposeWriter, sample_compose_file: ComposeFile
    ) -> None:
        """Test writing multiple ComposeFiles in batches."""
        files = [sample_compose_file, sample_compose_file, sample_compose_file]
        result = writer.write_compose_files(files)
        assert result["total_written"] == 3
        assert result["batches_executed"] == 2  # batch_size=2

    def test_compose_file_cypher_query(
        self, writer: DockerComposeWriter, sample_compose_file: ComposeFile
    ) -> None:
        """Test ComposeFile UNWIND query structure."""
        writer.write_compose_files([sample_compose_file])
        mock_session = writer.neo4j_client.session().__enter__()
        call_args = mock_session.run.call_args_list[0]
        query = call_args[0][0]
        assert "UNWIND $rows AS row" in query
        assert "MERGE (f:ComposeFile {file_path: row.file_path})" in query
        assert "SET f.version = row.version" in query


class TestWriteComposeProjects:
    """Test write_compose_projects method."""

    def test_write_empty_list(self, writer: DockerComposeWriter) -> None:
        """Test writing empty list returns zeros."""
        result = writer.write_compose_projects([])
        assert result == {"total_written": 0, "batches_executed": 0}

    def test_write_single_project(
        self, writer: DockerComposeWriter, sample_compose_project: ComposeProject
    ) -> None:
        """Test writing single ComposeProject."""
        result = writer.write_compose_projects([sample_compose_project])
        assert result["total_written"] == 1
        assert result["batches_executed"] == 1


class TestWriteComposeServices:
    """Test write_compose_services method."""

    def test_write_empty_list(self, writer: DockerComposeWriter) -> None:
        """Test writing empty list returns zeros."""
        result = writer.write_compose_services([])
        assert result == {"total_written": 0, "batches_executed": 0}

    def test_write_single_service(
        self, writer: DockerComposeWriter, sample_compose_service: ComposeService
    ) -> None:
        """Test writing single ComposeService."""
        result = writer.write_compose_services([sample_compose_service])
        assert result["total_written"] == 1
        assert result["batches_executed"] == 1


class TestWriteComposeNetworks:
    """Test write_compose_networks method."""

    def test_write_empty_list(self, writer: DockerComposeWriter) -> None:
        """Test writing empty list returns zeros."""
        result = writer.write_compose_networks([])
        assert result == {"total_written": 0, "batches_executed": 0}

    def test_write_single_network(
        self, writer: DockerComposeWriter, sample_compose_network: ComposeNetwork
    ) -> None:
        """Test writing single ComposeNetwork."""
        result = writer.write_compose_networks([sample_compose_network])
        assert result["total_written"] == 1
        assert result["batches_executed"] == 1


class TestWriteComposeVolumes:
    """Test write_compose_volumes method."""

    def test_write_empty_list(self, writer: DockerComposeWriter) -> None:
        """Test writing empty list returns zeros."""
        result = writer.write_compose_volumes([])
        assert result == {"total_written": 0, "batches_executed": 0}

    def test_write_single_volume(
        self, writer: DockerComposeWriter, sample_compose_volume: ComposeVolume
    ) -> None:
        """Test writing single ComposeVolume."""
        result = writer.write_compose_volumes([sample_compose_volume])
        assert result["total_written"] == 1
        assert result["batches_executed"] == 1


class TestWritePortBindings:
    """Test write_port_bindings method."""

    def test_write_empty_list(self, writer: DockerComposeWriter) -> None:
        """Test writing empty list returns zeros."""
        result = writer.write_port_bindings([])
        assert result == {"total_written": 0, "batches_executed": 0}

    def test_write_single_port_binding(
        self, writer: DockerComposeWriter, sample_port_binding: PortBinding
    ) -> None:
        """Test writing single PortBinding."""
        result = writer.write_port_bindings([sample_port_binding])
        assert result["total_written"] == 1
        assert result["batches_executed"] == 1


class TestWriteEnvironmentVariables:
    """Test write_environment_variables method."""

    def test_write_empty_list(self, writer: DockerComposeWriter) -> None:
        """Test writing empty list returns zeros."""
        result = writer.write_environment_variables([])
        assert result == {"total_written": 0, "batches_executed": 0}

    def test_write_single_env_var(
        self, writer: DockerComposeWriter, sample_env_var: EnvironmentVariable
    ) -> None:
        """Test writing single EnvironmentVariable."""
        result = writer.write_environment_variables([sample_env_var])
        assert result["total_written"] == 1
        assert result["batches_executed"] == 1


class TestWriteServiceDependencies:
    """Test write_service_dependencies method."""

    def test_write_empty_list(self, writer: DockerComposeWriter) -> None:
        """Test writing empty list returns zeros."""
        result = writer.write_service_dependencies([])
        assert result == {"total_written": 0, "batches_executed": 0}

    def test_write_single_dependency(
        self, writer: DockerComposeWriter, sample_service_dependency: ServiceDependency
    ) -> None:
        """Test writing single ServiceDependency."""
        result = writer.write_service_dependencies([sample_service_dependency])
        assert result["total_written"] == 1
        assert result["batches_executed"] == 1


class TestWriteImageDetails:
    """Test write_image_details method."""

    def test_write_empty_list(self, writer: DockerComposeWriter) -> None:
        """Test writing empty list returns zeros."""
        result = writer.write_image_details([])
        assert result == {"total_written": 0, "batches_executed": 0}

    def test_write_single_image_details(
        self, writer: DockerComposeWriter, sample_image_details: ImageDetails
    ) -> None:
        """Test writing single ImageDetails."""
        result = writer.write_image_details([sample_image_details])
        assert result["total_written"] == 1
        assert result["batches_executed"] == 1


class TestWriteHealthChecks:
    """Test write_health_checks method."""

    def test_write_empty_list(self, writer: DockerComposeWriter) -> None:
        """Test writing empty list returns zeros."""
        result = writer.write_health_checks([])
        assert result == {"total_written": 0, "batches_executed": 0}

    def test_write_single_health_check(
        self, writer: DockerComposeWriter, sample_health_check: HealthCheck
    ) -> None:
        """Test writing single HealthCheck."""
        result = writer.write_health_checks([sample_health_check])
        assert result["total_written"] == 1
        assert result["batches_executed"] == 1


class TestWriteBuildContexts:
    """Test write_build_contexts method."""

    def test_write_empty_list(self, writer: DockerComposeWriter) -> None:
        """Test writing empty list returns zeros."""
        result = writer.write_build_contexts([])
        assert result == {"total_written": 0, "batches_executed": 0}

    def test_write_single_build_context(
        self, writer: DockerComposeWriter, sample_build_context: BuildContext
    ) -> None:
        """Test writing single BuildContext."""
        result = writer.write_build_contexts([sample_build_context])
        assert result["total_written"] == 1
        assert result["batches_executed"] == 1


class TestWriteDeviceMappings:
    """Test write_device_mappings method."""

    def test_write_empty_list(self, writer: DockerComposeWriter) -> None:
        """Test writing empty list returns zeros."""
        result = writer.write_device_mappings([])
        assert result == {"total_written": 0, "batches_executed": 0}

    def test_write_single_device_mapping(
        self, writer: DockerComposeWriter, sample_device_mapping: DeviceMapping
    ) -> None:
        """Test writing single DeviceMapping."""
        result = writer.write_device_mappings([sample_device_mapping])
        assert result["total_written"] == 1
        assert result["batches_executed"] == 1
