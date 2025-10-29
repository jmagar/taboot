"""DockerComposeWriter - Batched Neo4j writer for Docker Compose ingestion.

Implements batched UNWIND operations for all 12 Docker Compose entity types.
Follows the pattern from packages/graph/writers/swag_writer.py.

Performance target: ≥20k edges/min with 2k-row UNWIND batches.
"""

import logging

from packages.graph.client import Neo4jClient
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


class DockerComposeWriter:
    """Batched Neo4j writer for Docker Compose ingestion.

    Implements batched UNWIND operations for all 12 Docker Compose entity types:
    - ComposeFile, ComposeProject, ComposeService, ComposeNetwork, ComposeVolume
    - PortBinding, EnvironmentVariable, ServiceDependency, ImageDetails
    - HealthCheck, BuildContext, DeviceMapping

    Ensures atomic writes and high throughput (target ≥20k edges/min).

    Attributes:
        neo4j_client: Neo4j client instance with connection pooling.
        batch_size: Number of rows per UNWIND batch (default 2000).
    """

    def __init__(self, neo4j_client: Neo4jClient, batch_size: int = 2000) -> None:
        """Initialize DockerComposeWriter with Neo4j client.

        Args:
            neo4j_client: Neo4j client instance (must be connected).
            batch_size: Number of rows per UNWIND batch (default 2000).
        """
        self.neo4j_client = neo4j_client
        self.batch_size = batch_size

        logger.info(f"Initialized DockerComposeWriter (batch_size={batch_size})")

    def write_compose_files(self, files: list[ComposeFile]) -> dict[str, int]:
        """Write ComposeFile nodes to Neo4j using batched UNWIND.

        Creates or updates ComposeFile nodes with all properties.
        Uses MERGE on unique key (file_path) for idempotency.

        Args:
            files: List of ComposeFile entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total files written
                - batches_executed: Number of batches executed

        Raises:
            Exception: If Neo4j write operation fails.
        """
        if not files:
            logger.info("No compose files to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare file parameters
        file_params = [
            {
                "file_path": f.file_path,
                "version": f.version,
                "project_name": f.project_name,
                "created_at": f.created_at.isoformat(),
                "updated_at": f.updated_at.isoformat(),
                "source_timestamp": f.source_timestamp.isoformat() if f.source_timestamp else None,
                "extraction_tier": f.extraction_tier,
                "extraction_method": f.extraction_method,
                "confidence": f.confidence,
                "extractor_version": f.extractor_version,
            }
            for f in files
        ]

        # Execute in batches
        with self.neo4j_client.session() as session:
            for i in range(0, len(file_params), self.batch_size):
                batch = file_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MERGE (f:ComposeFile {file_path: row.file_path})
                SET f.version = row.version,
                    f.project_name = row.project_name,
                    f.created_at = row.created_at,
                    f.updated_at = row.updated_at,
                    f.source_timestamp = row.source_timestamp,
                    f.extraction_tier = row.extraction_tier,
                    f.extraction_method = row.extraction_method,
                    f.confidence = row.confidence,
                    f.extractor_version = row.extractor_version
                RETURN count(f) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote ComposeFile batch {batches_executed}: "
                    f"{len(batch)} rows, "
                    f"counters={summary.counters}"
                )

        logger.info(
            f"Wrote {total_written} ComposeFile node(s) in {batches_executed} batch(es)"
        )

        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_compose_projects(self, projects: list[ComposeProject]) -> dict[str, int]:
        """Write ComposeProject nodes to Neo4j using batched UNWIND.

        Args:
            projects: List of ComposeProject entities to write.

        Returns:
            dict[str, int]: Statistics (total_written, batches_executed).
        """
        if not projects:
            logger.info("No compose projects to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        project_params = [
            {
                "name": p.name,
                "version": p.version,
                "file_path": p.file_path,
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat(),
                "source_timestamp": p.source_timestamp.isoformat() if p.source_timestamp else None,
                "extraction_tier": p.extraction_tier,
                "extraction_method": p.extraction_method,
                "confidence": p.confidence,
                "extractor_version": p.extractor_version,
            }
            for p in projects
        ]

        with self.neo4j_client.session() as session:
            for i in range(0, len(project_params), self.batch_size):
                batch = project_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MERGE (p:ComposeProject {name: row.name})
                SET p.version = row.version,
                    p.file_path = row.file_path,
                    p.created_at = row.created_at,
                    p.updated_at = row.updated_at,
                    p.source_timestamp = row.source_timestamp,
                    p.extraction_tier = row.extraction_tier,
                    p.extraction_method = row.extraction_method,
                    p.confidence = row.confidence,
                    p.extractor_version = row.extractor_version
                RETURN count(p) AS created_count
                """

                result = session.run(query, {"rows": batch})
                result.consume()

                total_written += len(batch)
                batches_executed += 1

        logger.info(
            f"Wrote {total_written} ComposeProject node(s) in {batches_executed} batch(es)"
        )
        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_compose_services(self, services: list[ComposeService]) -> dict[str, int]:
        """Write ComposeService nodes to Neo4j using batched UNWIND.

        Args:
            services: List of ComposeService entities to write.

        Returns:
            dict[str, int]: Statistics (total_written, batches_executed).
        """
        if not services:
            logger.info("No compose services to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        service_params = [
            {
                "name": s.name,
                "compose_file_path": s.compose_file_path,
                "image": s.image,
                "command": s.command,
                "entrypoint": s.entrypoint,
                "restart": s.restart,
                "cpus": s.cpus,
                "memory": s.memory,
                "user": s.user,
                "working_dir": s.working_dir,
                "hostname": s.hostname,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
                "source_timestamp": s.source_timestamp.isoformat() if s.source_timestamp else None,
                "extraction_tier": s.extraction_tier,
                "extraction_method": s.extraction_method,
                "confidence": s.confidence,
                "extractor_version": s.extractor_version,
            }
            for s in services
        ]

        with self.neo4j_client.session() as session:
            for i in range(0, len(service_params), self.batch_size):
                batch = service_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MERGE (s:ComposeService {compose_file_path: row.compose_file_path, name: row.name})
                SET s.image = row.image,
                    s.command = row.command,
                    s.entrypoint = row.entrypoint,
                    s.restart = row.restart,
                    s.cpus = row.cpus,
                    s.memory = row.memory,
                    s.user = row.user,
                    s.working_dir = row.working_dir,
                    s.hostname = row.hostname,
                    s.created_at = row.created_at,
                    s.updated_at = row.updated_at,
                    s.source_timestamp = row.source_timestamp,
                    s.extraction_tier = row.extraction_tier,
                    s.extraction_method = row.extraction_method,
                    s.confidence = row.confidence,
                    s.extractor_version = row.extractor_version
                RETURN count(s) AS created_count
                """

                result = session.run(query, {"rows": batch})
                result.consume()

                total_written += len(batch)
                batches_executed += 1

        logger.info(
            f"Wrote {total_written} ComposeService node(s) in {batches_executed} batch(es)"
        )
        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_compose_networks(self, networks: list[ComposeNetwork]) -> dict[str, int]:
        """Write ComposeNetwork nodes to Neo4j using batched UNWIND.

        Args:
            networks: List of ComposeNetwork entities to write.

        Returns:
            dict[str, int]: Statistics (total_written, batches_executed).
        """
        if not networks:
            logger.info("No compose networks to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        network_params = [
            {
                "name": n.name,
                "compose_file_path": n.compose_file_path,
                "driver": n.driver,
                "external": n.external,
                "enable_ipv6": n.enable_ipv6,
                "ipam_driver": n.ipam_driver,
                "ipam_config": n.ipam_config,
                "created_at": n.created_at.isoformat(),
                "updated_at": n.updated_at.isoformat(),
                "source_timestamp": n.source_timestamp.isoformat() if n.source_timestamp else None,
                "extraction_tier": n.extraction_tier,
                "extraction_method": n.extraction_method,
                "confidence": n.confidence,
                "extractor_version": n.extractor_version,
            }
            for n in networks
        ]

        with self.neo4j_client.session() as session:
            for i in range(0, len(network_params), self.batch_size):
                batch = network_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MERGE (n:ComposeNetwork {compose_file_path: row.compose_file_path, name: row.name})
                SET n.driver = row.driver,
                    n.external = row.external,
                    n.enable_ipv6 = row.enable_ipv6,
                    n.ipam_driver = row.ipam_driver,
                    n.ipam_config = row.ipam_config,
                    n.created_at = row.created_at,
                    n.updated_at = row.updated_at,
                    n.source_timestamp = row.source_timestamp,
                    n.extraction_tier = row.extraction_tier,
                    n.extraction_method = row.extraction_method,
                    n.confidence = row.confidence,
                    n.extractor_version = row.extractor_version
                RETURN count(n) AS created_count
                """

                result = session.run(query, {"rows": batch})
                result.consume()

                total_written += len(batch)
                batches_executed += 1

        logger.info(
            f"Wrote {total_written} ComposeNetwork node(s) in {batches_executed} batch(es)"
        )
        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_compose_volumes(self, volumes: list[ComposeVolume]) -> dict[str, int]:
        """Write ComposeVolume nodes to Neo4j using batched UNWIND.

        Args:
            volumes: List of ComposeVolume entities to write.

        Returns:
            dict[str, int]: Statistics (total_written, batches_executed).
        """
        if not volumes:
            logger.info("No compose volumes to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        volume_params = [
            {
                "name": v.name,
                "compose_file_path": v.compose_file_path,
                "driver": v.driver,
                "external": v.external,
                "driver_opts": v.driver_opts,
                "created_at": v.created_at.isoformat(),
                "updated_at": v.updated_at.isoformat(),
                "source_timestamp": v.source_timestamp.isoformat() if v.source_timestamp else None,
                "extraction_tier": v.extraction_tier,
                "extraction_method": v.extraction_method,
                "confidence": v.confidence,
                "extractor_version": v.extractor_version,
            }
            for v in volumes
        ]

        with self.neo4j_client.session() as session:
            for i in range(0, len(volume_params), self.batch_size):
                batch = volume_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MERGE (v:ComposeVolume {compose_file_path: row.compose_file_path, name: row.name})
                SET v.driver = row.driver,
                    v.external = row.external,
                    v.driver_opts = row.driver_opts,
                    v.created_at = row.created_at,
                    v.updated_at = row.updated_at,
                    v.source_timestamp = row.source_timestamp,
                    v.extraction_tier = row.extraction_tier,
                    v.extraction_method = row.extraction_method,
                    v.confidence = row.confidence,
                    v.extractor_version = row.extractor_version
                RETURN count(v) AS created_count
                """

                result = session.run(query, {"rows": batch})
                result.consume()

                total_written += len(batch)
                batches_executed += 1

        logger.info(
            f"Wrote {total_written} ComposeVolume node(s) in {batches_executed} batch(es)"
        )
        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_port_bindings(self, port_bindings: list[PortBinding]) -> dict[str, int]:
        """Write PortBinding nodes to Neo4j using batched UNWIND.

        Args:
            port_bindings: List of PortBinding entities to write.

        Returns:
            dict[str, int]: Statistics (total_written, batches_executed).
        """
        if not port_bindings:
            logger.info("No port bindings to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        port_params = [
            {
                "compose_file_path": p.compose_file_path,
                "service_name": p.service_name,
                "host_ip": p.host_ip or "0.0.0.0",
                "host_port": p.host_port if p.host_port is not None else 0,
                "container_port": p.container_port,
                "protocol": p.protocol or "tcp",
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat(),
                "source_timestamp": p.source_timestamp.isoformat() if p.source_timestamp else None,
                "extraction_tier": p.extraction_tier,
                "extraction_method": p.extraction_method,
                "confidence": p.confidence,
                "extractor_version": p.extractor_version,
            }
            for p in port_bindings
        ]

        with self.neo4j_client.session() as session:
            for i in range(0, len(port_params), self.batch_size):
                batch = port_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MERGE (p:PortBinding {
                    compose_file_path: row.compose_file_path,
                    service_name: row.service_name,
                    host_ip: row.host_ip,
                    host_port: row.host_port,
                    container_port: row.container_port,
                    protocol: row.protocol
                })
                SET p.created_at = row.created_at,
                    p.updated_at = row.updated_at,
                    p.source_timestamp = row.source_timestamp,
                    p.extraction_tier = row.extraction_tier,
                    p.extraction_method = row.extraction_method,
                    p.confidence = row.confidence,
                    p.extractor_version = row.extractor_version
                RETURN count(p) AS created_count
                """

                result = session.run(query, {"rows": batch})
                result.consume()

                total_written += len(batch)
                batches_executed += 1

        logger.info(
            f"Wrote {total_written} PortBinding node(s) in {batches_executed} batch(es)"
        )
        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_environment_variables(
        self, env_vars: list[EnvironmentVariable]
    ) -> dict[str, int]:
        """Write EnvironmentVariable nodes to Neo4j using batched UNWIND.

        Args:
            env_vars: List of EnvironmentVariable entities to write.

        Returns:
            dict[str, int]: Statistics (total_written, batches_executed).
        """
        if not env_vars:
            logger.info("No environment variables to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        env_params = [
            {
                "compose_file_path": e.compose_file_path,
                "key": e.key,
                "value": e.value,
                "service_name": e.service_name or "__global__",
                "created_at": e.created_at.isoformat(),
                "updated_at": e.updated_at.isoformat(),
                "source_timestamp": e.source_timestamp.isoformat() if e.source_timestamp else None,
                "extraction_tier": e.extraction_tier,
                "extraction_method": e.extraction_method,
                "confidence": e.confidence,
                "extractor_version": e.extractor_version,
            }
            for e in env_vars
        ]

        with self.neo4j_client.session() as session:
            for i in range(0, len(env_params), self.batch_size):
                batch = env_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MERGE (e:EnvironmentVariable {
                    compose_file_path: row.compose_file_path,
                    service_name: row.service_name,
                    key: row.key
                })
                SET e.value = row.value,
                    e.created_at = row.created_at,
                    e.updated_at = row.updated_at,
                    e.source_timestamp = row.source_timestamp,
                    e.extraction_tier = row.extraction_tier,
                    e.extraction_method = row.extraction_method,
                    e.confidence = row.confidence,
                    e.extractor_version = row.extractor_version
                RETURN count(e) AS created_count
                """

                result = session.run(query, {"rows": batch})
                result.consume()

                total_written += len(batch)
                batches_executed += 1

        logger.info(
            f"Wrote {total_written} EnvironmentVariable node(s) in {batches_executed} batch(es)"
        )
        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_service_dependencies(
        self, dependencies: list[ServiceDependency]
    ) -> dict[str, int]:
        """Write ServiceDependency relationships to Neo4j using batched UNWIND.

        Args:
            dependencies: List of ServiceDependency entities to write.

        Returns:
            dict[str, int]: Statistics (total_written, batches_executed).
        """
        if not dependencies:
            logger.info("No service dependencies to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        dep_params = [
            {
                "compose_file_path": d.compose_file_path,
                "source_service": d.source_service,
                "target_service": d.target_service,
                "condition": d.condition,
                "created_at": d.created_at.isoformat(),
                "updated_at": d.updated_at.isoformat(),
                "source_timestamp": d.source_timestamp.isoformat()
                if d.source_timestamp
                else None,
                "extraction_tier": d.extraction_tier,
                "extraction_method": d.extraction_method,
                "confidence": d.confidence,
                "extractor_version": d.extractor_version,
            }
            for d in dependencies
        ]

        with self.neo4j_client.session() as session:
            for i in range(0, len(dep_params), self.batch_size):
                batch = dep_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                OPTIONAL MATCH (
                    source:ComposeService {
                        compose_file_path: row.compose_file_path,
                        name: row.source_service
                    }
                )
                OPTIONAL MATCH (
                    target:ComposeService {
                        compose_file_path: row.compose_file_path,
                        name: row.target_service
                    }
                )
                WITH row, source, target
                WHERE source IS NOT NULL AND target IS NOT NULL
                MERGE (source)-[r:DEPENDS_ON]->(target)
                SET r.condition = row.condition,
                    r.created_at = row.created_at,
                    r.updated_at = row.updated_at,
                    r.source_timestamp = row.source_timestamp,
                    r.extraction_tier = row.extraction_tier,
                    r.extraction_method = row.extraction_method,
                    r.confidence = row.confidence,
                    r.extractor_version = row.extractor_version
                RETURN count(r) AS created_count
                """

                result = session.run(query, {"rows": batch})
                created_count = len(batch)
                if hasattr(result, "single"):
                    record = result.single()
                    try:
                        value = record["created_count"] if record else None
                        if isinstance(value, (int, float)):
                            created_count = int(value)
                    except (KeyError, TypeError):
                        pass

                total_written += created_count
                batches_executed += 1

                skipped = max(len(batch) - created_count, 0)
                if skipped > 0:
                    affected_files = sorted(
                        {row["compose_file_path"] for row in batch}
                    )
                    logger.warning(
                        "Skipped %s ServiceDependency relationship(s) because "
                        "ComposeService nodes were missing (compose_file_path(s)=%s)",
                        skipped,
                        ", ".join(affected_files),
                    )

        logger.info(
            f"Wrote {total_written} ServiceDependency relationship(s) "
            f"in {batches_executed} batch(es)"
        )
        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_image_details(self, images: list[ImageDetails]) -> dict[str, int]:
        """Write ImageDetails nodes to Neo4j using batched UNWIND.

        Args:
            images: List of ImageDetails entities to write.

        Returns:
            dict[str, int]: Statistics (total_written, batches_executed).
        """
        if not images:
            logger.info("No image details to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        image_params = [
            {
                "compose_file_path": i.compose_file_path,
                "service_name": i.service_name,
                "image_name": i.image_name,
                "tag": i.tag or "latest",
                "registry": i.registry,
                "digest": i.digest,
                "created_at": i.created_at.isoformat(),
                "updated_at": i.updated_at.isoformat(),
                "source_timestamp": i.source_timestamp.isoformat() if i.source_timestamp else None,
                "extraction_tier": i.extraction_tier,
                "extraction_method": i.extraction_method,
                "confidence": i.confidence,
                "extractor_version": i.extractor_version,
            }
            for i in images
        ]

        with self.neo4j_client.session() as session:
            for i in range(0, len(image_params), self.batch_size):
                batch = image_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MERGE (i:ImageDetails {
                    compose_file_path: row.compose_file_path,
                    service_name: row.service_name,
                    image_name: row.image_name,
                    tag: row.tag,
                    registry: row.registry
                })
                SET i.digest = row.digest,
                    i.created_at = row.created_at,
                    i.updated_at = row.updated_at,
                    i.source_timestamp = row.source_timestamp,
                    i.extraction_tier = row.extraction_tier,
                    i.extraction_method = row.extraction_method,
                    i.confidence = row.confidence,
                    i.extractor_version = row.extractor_version
                RETURN count(i) AS created_count
                """

                result = session.run(query, {"rows": batch})
                result.consume()

                total_written += len(batch)
                batches_executed += 1

        logger.info(
            f"Wrote {total_written} ImageDetails node(s) in {batches_executed} batch(es)"
        )
        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_health_checks(self, health_checks: list[HealthCheck]) -> dict[str, int]:
        """Write HealthCheck nodes to Neo4j using batched UNWIND.

        Args:
            health_checks: List of HealthCheck entities to write.

        Returns:
            dict[str, int]: Statistics (total_written, batches_executed).
        """
        if not health_checks:
            logger.info("No health checks to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        health_params = [
            {
                "compose_file_path": h.compose_file_path,
                "service_name": h.service_name,
                "test": h.test,
                "interval": h.interval,
                "timeout": h.timeout,
                "retries": h.retries,
                "start_period": h.start_period,
                "created_at": h.created_at.isoformat(),
                "updated_at": h.updated_at.isoformat(),
                "source_timestamp": h.source_timestamp.isoformat() if h.source_timestamp else None,
                "extraction_tier": h.extraction_tier,
                "extraction_method": h.extraction_method,
                "confidence": h.confidence,
                "extractor_version": h.extractor_version,
            }
            for h in health_checks
        ]

        with self.neo4j_client.session() as session:
            for i in range(0, len(health_params), self.batch_size):
                batch = health_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MERGE (h:HealthCheck {
                    compose_file_path: row.compose_file_path,
                    service_name: row.service_name,
                    test: row.test
                })
                SET h.interval = row.interval,
                    h.timeout = row.timeout,
                    h.retries = row.retries,
                    h.start_period = row.start_period,
                    h.created_at = row.created_at,
                    h.updated_at = row.updated_at,
                    h.source_timestamp = row.source_timestamp,
                    h.extraction_tier = row.extraction_tier,
                    h.extraction_method = row.extraction_method,
                    h.confidence = row.confidence,
                    h.extractor_version = row.extractor_version
                RETURN count(h) AS created_count
                """

                result = session.run(query, {"rows": batch})
                result.consume()

                total_written += len(batch)
                batches_executed += 1

        logger.info(
            f"Wrote {total_written} HealthCheck node(s) in {batches_executed} batch(es)"
        )
        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_build_contexts(self, build_contexts: list[BuildContext]) -> dict[str, int]:
        """Write BuildContext nodes to Neo4j using batched UNWIND.

        Args:
            build_contexts: List of BuildContext entities to write.

        Returns:
            dict[str, int]: Statistics (total_written, batches_executed).
        """
        if not build_contexts:
            logger.info("No build contexts to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        build_params = []
        for b in build_contexts:
            dockerfile = b.dockerfile or "Dockerfile"
            build_params.append(
                {
                    "compose_file_path": b.compose_file_path,
                    "service_name": b.service_name,
                    "context_path": b.context_path,
                    "dockerfile": dockerfile,
                    "target": b.target,
                    "args": b.args,
                    "created_at": b.created_at.isoformat(),
                    "updated_at": b.updated_at.isoformat(),
                    "source_timestamp": b.source_timestamp.isoformat()
                    if b.source_timestamp
                    else None,
                    "extraction_tier": b.extraction_tier,
                    "extraction_method": b.extraction_method,
                    "confidence": b.confidence,
                    "extractor_version": b.extractor_version,
                }
            )

        with self.neo4j_client.session() as session:
            for i in range(0, len(build_params), self.batch_size):
                batch = build_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MERGE (b:BuildContext {
                    compose_file_path: row.compose_file_path,
                    service_name: row.service_name,
                    context_path: row.context_path,
                    dockerfile: row.dockerfile
                })
                SET b.dockerfile = row.dockerfile,
                    b.target = row.target,
                    b.args = row.args,
                    b.created_at = row.created_at,
                    b.updated_at = row.updated_at,
                    b.source_timestamp = row.source_timestamp,
                    b.extraction_tier = row.extraction_tier,
                    b.extraction_method = row.extraction_method,
                    b.confidence = row.confidence,
                    b.extractor_version = row.extractor_version
                RETURN count(b) AS created_count
                """

                result = session.run(query, {"rows": batch})
                result.consume()

                total_written += len(batch)
                batches_executed += 1

        logger.info(
            f"Wrote {total_written} BuildContext node(s) in {batches_executed} batch(es)"
        )
        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_device_mappings(self, device_mappings: list[DeviceMapping]) -> dict[str, int]:
        """Write DeviceMapping nodes to Neo4j using batched UNWIND.

        Args:
            device_mappings: List of DeviceMapping entities to write.

        Returns:
            dict[str, int]: Statistics (total_written, batches_executed).
        """
        if not device_mappings:
            logger.info("No device mappings to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        device_params = [
            {
                "compose_file_path": d.compose_file_path,
                "service_name": d.service_name,
                "host_device": d.host_device,
                "container_device": d.container_device,
                "permissions": d.permissions,
                "created_at": d.created_at.isoformat(),
                "updated_at": d.updated_at.isoformat(),
                "source_timestamp": d.source_timestamp.isoformat() if d.source_timestamp else None,
                "extraction_tier": d.extraction_tier,
                "extraction_method": d.extraction_method,
                "confidence": d.confidence,
                "extractor_version": d.extractor_version,
            }
            for d in device_mappings
        ]

        with self.neo4j_client.session() as session:
            for i in range(0, len(device_params), self.batch_size):
                batch = device_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MERGE (d:DeviceMapping {
                    compose_file_path: row.compose_file_path,
                    service_name: row.service_name,
                    host_device: row.host_device,
                    container_device: row.container_device
                })
                SET d.permissions = row.permissions,
                    d.created_at = row.created_at,
                    d.updated_at = row.updated_at,
                    d.source_timestamp = row.source_timestamp,
                    d.extraction_tier = row.extraction_tier,
                    d.extraction_method = row.extraction_method,
                    d.confidence = row.confidence,
                    d.extractor_version = row.extractor_version
                RETURN count(d) AS created_count
                """

                result = session.run(query, {"rows": batch})
                result.consume()

                total_written += len(batch)
                batches_executed += 1

        logger.info(
            f"Wrote {total_written} DeviceMapping node(s) in {batches_executed} batch(es)"
        )
        return {"total_written": total_written, "batches_executed": batches_executed}


# Export public API
__all__ = ["DockerComposeWriter"]
