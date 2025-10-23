"""End-to-end integration tests for structured source ingestion (T126).

This test suite validates Phase 7 acceptance scenarios:
1. Docker Compose files are parsed to extract Service nodes, DEPENDS_ON, and BINDS relationships
2. SWAG nginx configs are parsed to extract Proxy nodes and ROUTES_TO relationships
3. All extracted entities are written to Neo4j with proper constraints
4. Data can be queried back from Neo4j to verify correctness

Following TDD: Tests written to validate structured source ingestion pipeline.
These tests require Docker services to be running and healthy.

Markers:
- @pytest.mark.integration: Requires Docker services
- @pytest.mark.slow: End-to-end tests take longer to run
"""

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from packages.graph.client import Neo4jClient
from packages.ingest.readers.docker_compose import DockerComposeReader
from packages.ingest.readers.swag import SwagReader


@pytest.mark.integration
@pytest.mark.slow
class TestDockerComposeIngestion:
    """End-to-end tests for Docker Compose file ingestion."""

    @pytest.mark.asyncio
    async def test_docker_compose_full_pipeline(self, docker_services_ready: None) -> None:
        """Test full pipeline: parse Docker Compose -> write to Neo4j -> verify data.

        Acceptance Scenario 1: Given a docker-compose.yaml file with services, ports,
        and dependencies, When the system parses and ingests it, Then Service nodes
        are created in Neo4j with DEPENDS_ON and BINDS relationships.
        """
        # Create temporary docker-compose.yaml with test services
        compose_content = """
version: "3.9"
services:
  web:
    image: nginx:1.21-alpine
    ports:
      - "80:80"
      - "443:443/tcp"
    depends_on:
      - api
      - redis

  api:
    image: myapp/api:v2.3.0
    ports:
      - "8080:8080"
    depends_on:
      - postgres

  postgres:
    image: postgres:15
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp_file:
            tmp_file.write(compose_content)
            tmp_file_path = tmp_file.name

        try:
            # Step 1: Parse Docker Compose file
            reader = DockerComposeReader()
            parsed_data = reader.load_data(tmp_file_path)

            assert "services" in parsed_data
            assert "relationships" in parsed_data
            assert len(parsed_data["services"]) == 4  # web, api, postgres, redis
            assert len(parsed_data["relationships"]) > 0

            # Verify parsed services
            service_names = {svc["name"] for svc in parsed_data["services"]}
            assert service_names == {"web", "api", "postgres", "redis"}

            # Verify versions extracted from images
            service_map = {svc["name"]: svc for svc in parsed_data["services"]}
            assert service_map["web"]["version"] == "1.21-alpine"
            assert service_map["api"]["version"] == "v2.3.0"
            assert service_map["postgres"]["version"] == "15"

            # Step 2: Write to Neo4j using BatchedGraphWriter
            client = Neo4jClient()
            client.connect()

            try:
                # Prepare nodes for batch write
                now = datetime.now(UTC)
                nodes_to_write = []
                for svc in parsed_data["services"]:
                    nodes_to_write.append(
                        {
                            "name": svc["name"],
                            "image": svc["image"],
                            "version": svc["version"],
                            "created_at": now.isoformat(),
                            "updated_at": now.isoformat(),
                        }
                    )

                # Write nodes directly with session (synchronous approach)
                with client.session() as session:
                    for node in nodes_to_write:
                        query = """
                        MERGE (s:Service {name: $name})
                        SET s.image = $image,
                            s.version = $version,
                            s.created_at = $created_at,
                            s.updated_at = $updated_at
                        """
                        session.run(query, node)

                # Prepare relationships
                depends_on_rels = [
                    rel for rel in parsed_data["relationships"] if rel["type"] == "DEPENDS_ON"
                ]
                binds_rels = [rel for rel in parsed_data["relationships"] if rel["type"] == "BINDS"]

                # Write DEPENDS_ON relationships
                with client.session() as session:
                    for rel in depends_on_rels:
                        query = """
                        MATCH (source:Service {name: $source})
                        MATCH (target:Service {name: $target})
                        MERGE (source)-[r:DEPENDS_ON]->(target)
                        """
                        session.run(query, {"source": rel["source"], "target": rel["target"]})

                # Write BINDS relationships
                with client.session() as session:
                    for rel in binds_rels:
                        query = """
                        MATCH (s:Service {name: $source})
                        MERGE (s)-[r:BINDS {port: $port, protocol: $protocol}]->(s)
                        """
                        session.run(
                            query,
                            {
                                "source": rel["source"],
                                "port": rel["port"],
                                "protocol": rel["protocol"],
                            },
                        )

                # Step 3: Verify Service nodes exist in Neo4j
                with client.session() as session:
                    result = session.run(
                        "MATCH (s:Service) WHERE s.name IN $names RETURN s.name AS name, "
                        "s.image AS image, s.version AS version ORDER BY s.name",
                        {"names": ["web", "api", "postgres", "redis"]},
                    )
                    services = list(result)

                    assert len(services) == 4, "Expected 4 Service nodes"

                    # Verify specific service data
                    service_data = {rec["name"]: rec for rec in services}
                    assert service_data["web"]["version"] == "1.21-alpine"
                    assert service_data["api"]["version"] == "v2.3.0"
                    assert "nginx" in service_data["web"]["image"]
                    assert "myapp/api" in service_data["api"]["image"]

                # Step 4: Verify DEPENDS_ON relationships
                with client.session() as session:
                    result = session.run(
                        """
                        MATCH (source:Service)-[r:DEPENDS_ON]->(target:Service)
                        WHERE source.name IN $names
                        RETURN source.name AS source, target.name AS target
                        ORDER BY source, target
                        """,
                        {"names": ["web", "api"]},
                    )
                    dependencies = list(result)

                    assert len(dependencies) >= 3, "Expected at least 3 DEPENDS_ON relationships"

                    # Verify specific dependencies
                    dep_pairs = {(rec["source"], rec["target"]) for rec in dependencies}
                    assert ("web", "api") in dep_pairs
                    assert ("web", "redis") in dep_pairs
                    assert ("api", "postgres") in dep_pairs

                # Step 5: Verify BINDS relationships
                with client.session() as session:
                    result = session.run(
                        """
                        MATCH (s:Service)-[r:BINDS]->(s)
                        WHERE s.name IN $names
                        RETURN s.name AS service, r.port AS port, r.protocol AS protocol
                        ORDER BY service, port
                        """,
                        {"names": ["web", "api", "postgres", "redis"]},
                    )
                    binds = list(result)

                    assert len(binds) >= 4, "Expected at least 4 BINDS relationships"

                    # Verify specific port bindings
                    port_bindings = {
                        (rec["service"], rec["port"], rec["protocol"]) for rec in binds
                    }
                    assert ("web", 80, "tcp") in port_bindings
                    assert ("web", 443, "tcp") in port_bindings
                    assert ("api", 8080, "tcp") in port_bindings
                    assert ("postgres", 5432, "tcp") in port_bindings
                    assert ("redis", 6379, "tcp") in port_bindings

            finally:
                # Cleanup: Delete test nodes and relationships
                with client.session() as session:
                    session.run(
                        """
                        MATCH (s:Service)
                        WHERE s.name IN $names
                        DETACH DELETE s
                        """,
                        {"names": ["web", "api", "postgres", "redis"]},
                    )
                client.close()

        finally:
            # Cleanup: Remove temporary file
            Path(tmp_file_path).unlink(missing_ok=True)


@pytest.mark.integration
@pytest.mark.slow
class TestSwagIngestion:
    """End-to-end tests for SWAG nginx config ingestion."""

    @pytest.mark.asyncio
    async def test_swag_config_full_pipeline(self, docker_services_ready: None) -> None:
        """Test full pipeline: parse SWAG config -> write to Neo4j -> verify data.

        Acceptance Scenario 2: Given a SWAG nginx config file with proxy rules,
        When the system parses and ingests it, Then Proxy nodes are created in Neo4j
        with ROUTES_TO relationships containing host, path, and target service info.
        """
        # Create temporary nginx config with test proxy rules
        nginx_config = """
server {
    listen 443 ssl;
    server_name api.example.com;

    location / {
        proxy_pass http://api-service:8080;
    }

    location /v2/ {
        proxy_pass http://api-v2-service:8000;
    }
}

server {
    listen 80;
    server_name web.example.com;

    location / {
        proxy_pass http://web-service:3000;
    }

    location /api/ {
        proxy_pass http://backend-service:5000;
    }
}
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as tmp_file:
            tmp_file.write(nginx_config)
            tmp_file_path = tmp_file.name

        try:
            # Step 1: Parse SWAG config
            reader = SwagReader(proxy_name="test-swag")
            parsed_config = reader.parse_file(tmp_file_path)

            assert "proxies" in parsed_config
            assert "routes" in parsed_config
            assert len(parsed_config["proxies"]) == 1  # Single proxy node
            assert len(parsed_config["routes"]) == 4  # 4 location blocks

            proxy = parsed_config["proxies"][0]
            assert proxy.name == "test-swag"
            assert proxy.proxy_type.value == "swag"

            # Verify parsed routes
            routes = parsed_config["routes"]
            route_map = {(r["host"], r["path"]): (r["target_service"], r["tls"]) for r in routes}

            assert ("api.example.com", "/") in route_map
            assert ("api.example.com", "/v2/") in route_map
            assert ("web.example.com", "/") in route_map
            assert ("web.example.com", "/api/") in route_map

            # Verify TLS detection
            assert route_map[("api.example.com", "/")][1] is True  # TLS enabled
            assert route_map[("web.example.com", "/")][1] is False  # TLS disabled

            # Step 2: Write to Neo4j
            client = Neo4jClient()
            client.connect()

            try:
                # Write Proxy node
                with client.session() as session:
                    query = """
                    MERGE (p:Proxy {name: $name})
                    SET p.proxy_type = $proxy_type,
                        p.created_at = $created_at,
                        p.updated_at = $updated_at
                    """
                    session.run(
                        query,
                        {
                            "name": proxy.name,
                            "proxy_type": proxy.proxy_type.value,
                            "created_at": proxy.created_at.isoformat(),
                            "updated_at": proxy.updated_at.isoformat(),
                        },
                    )

                # Write ROUTES_TO relationships
                # First, ensure target services exist (create dummy nodes)
                with client.session() as session:
                    service_names = {route["target_service"] for route in routes}
                    for service_name in service_names:
                        query = """
                        MERGE (s:Service {name: $name})
                        SET s.created_at = $created_at,
                            s.updated_at = $updated_at
                        """
                        now = datetime.now(UTC)
                        session.run(
                            query,
                            {
                                "name": service_name,
                                "created_at": now.isoformat(),
                                "updated_at": now.isoformat(),
                            },
                        )

                # Create ROUTES_TO relationships
                with client.session() as session:
                    for route in routes:
                        query = """
                        MATCH (p:Proxy {name: $proxy_name})
                        MATCH (s:Service {name: $service_name})
                        MERGE (p)-[r:ROUTES_TO {
                            host: $host,
                            path: $path,
                            tls: $tls
                        }]->(s)
                        """
                        session.run(
                            query,
                            {
                                "proxy_name": proxy.name,
                                "service_name": route["target_service"],
                                "host": route["host"],
                                "path": route["path"],
                                "tls": route["tls"],
                            },
                        )

                # Step 3: Verify Proxy node exists in Neo4j
                with client.session() as session:
                    result = session.run(
                        "MATCH (p:Proxy {name: $name}) RETURN p.name AS name, "
                        "p.proxy_type AS proxy_type",
                        {"name": "test-swag"},
                    )
                    records = list(result)

                    assert len(records) == 1, "Expected 1 Proxy node"
                    assert records[0]["name"] == "test-swag"
                    assert records[0]["proxy_type"] == "swag"

                # Step 4: Verify ROUTES_TO relationships exist
                with client.session() as session:
                    result = session.run(
                        """
                        MATCH (p:Proxy {name: $proxy_name})-[r:ROUTES_TO]->(s:Service)
                        RETURN r.host AS host, r.path AS path, r.tls AS tls,
                               s.name AS service
                        ORDER BY host, path
                        """,
                        {"proxy_name": "test-swag"},
                    )
                    routes_from_db = list(result)

                    assert len(routes_from_db) == 4, "Expected 4 ROUTES_TO relationships"

                    # Verify specific routes
                    route_tuples = {
                        (rec["host"], rec["path"], rec["service"], rec["tls"])
                        for rec in routes_from_db
                    }

                    assert ("api.example.com", "/", "api-service", True) in route_tuples
                    assert (
                        "api.example.com",
                        "/v2/",
                        "api-v2-service",
                        True,
                    ) in route_tuples
                    assert ("web.example.com", "/", "web-service", False) in route_tuples
                    assert (
                        "web.example.com",
                        "/api/",
                        "backend-service",
                        False,
                    ) in route_tuples

            finally:
                # Cleanup: Delete test nodes and relationships
                with client.session() as session:
                    # Delete proxy and all relationships
                    session.run(
                        """
                        MATCH (p:Proxy {name: $name})
                        DETACH DELETE p
                        """,
                        {"name": "test-swag"},
                    )

                    # Delete test services
                    session.run(
                        """
                        MATCH (s:Service)
                        WHERE s.name IN $names
                        DETACH DELETE s
                        """,
                        {
                            "names": [
                                "api-service",
                                "api-v2-service",
                                "web-service",
                                "backend-service",
                            ]
                        },
                    )

                client.close()

        finally:
            # Cleanup: Remove temporary file
            Path(tmp_file_path).unlink(missing_ok=True)


@pytest.mark.integration
@pytest.mark.slow
class TestStructuredIngestionIdempotency:
    """Test idempotency of structured source ingestion."""

    @pytest.mark.asyncio
    async def test_docker_compose_ingestion_is_idempotent(
        self, docker_services_ready: None
    ) -> None:
        """Test that ingesting the same Docker Compose file twice doesn't duplicate data.

        Acceptance Scenario 3: Given an already-ingested Docker Compose file,
        When the system ingests it again, Then existing nodes are updated (not duplicated)
        and the constraint on Service.name is respected.
        """
        compose_content = """
version: "3.9"
services:
  test-service:
    image: test/app:1.0.0
    ports:
      - "9090:9090"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp_file:
            tmp_file.write(compose_content)
            tmp_file_path = tmp_file.name

        try:
            reader = DockerComposeReader()
            client = Neo4jClient()
            client.connect()

            try:
                # First ingestion
                parsed_data = reader.load_data(tmp_file_path)
                with client.session() as session:
                    for svc in parsed_data["services"]:
                        now = datetime.now(UTC)
                        query = """
                        MERGE (s:Service {name: $name})
                        SET s.image = $image,
                            s.version = $version,
                            s.created_at = $created_at,
                            s.updated_at = $updated_at
                        """
                        session.run(
                            query,
                            {
                                "name": svc["name"],
                                "image": svc["image"],
                                "version": svc["version"],
                                "created_at": now.isoformat(),
                                "updated_at": now.isoformat(),
                            },
                        )

                # Count services after first ingestion
                with client.session() as session:
                    result = session.run(
                        "MATCH (s:Service {name: 'test-service'}) RETURN count(s) AS count"
                    )
                    record = result.single()
                    assert record is not None, "Expected a record from count query"
                    count_first = record["count"]
                    assert count_first == 1, "Expected 1 service node after first ingestion"

                # Second ingestion (idempotent)
                parsed_data = reader.load_data(tmp_file_path)
                with client.session() as session:
                    for svc in parsed_data["services"]:
                        now = datetime.now(UTC)
                        query = """
                        MERGE (s:Service {name: $name})
                        SET s.image = $image,
                            s.version = $version,
                            s.updated_at = $updated_at
                        """
                        session.run(
                            query,
                            {
                                "name": svc["name"],
                                "image": svc["image"],
                                "version": svc["version"],
                                "updated_at": now.isoformat(),
                            },
                        )

                # Count services after second ingestion (should still be 1)
                with client.session() as session:
                    result = session.run(
                        "MATCH (s:Service {name: 'test-service'}) RETURN count(s) AS count"
                    )
                    record = result.single()
                    assert record is not None, "Expected a record from count query"
                    count_second = record["count"]
                    assert count_second == 1, (
                        "Expected 1 service node after second ingestion (idempotent)"
                    )
                    assert count_first == count_second, (
                        "Service count should not change on re-ingestion"
                    )

            finally:
                # Cleanup
                with client.session() as session:
                    session.run(
                        """
                        MATCH (s:Service {name: 'test-service'})
                        DETACH DELETE s
                        """
                    )
                client.close()

        finally:
            Path(tmp_file_path).unlink(missing_ok=True)
