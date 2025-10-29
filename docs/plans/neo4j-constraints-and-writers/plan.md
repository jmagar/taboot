# Plan: Neo4j Constraints Update and Graph Writer Implementation

## Summary

**Goal:** Complete Neo4j constraint schema and implement missing batched graph writers for all entity types in the Taboot RAG platform.

**Executive Summary:** This plan addresses gaps in the Neo4j schema layer by adding 7 missing entity constraints (Container, Network, User, Repository, Package, Document, Credential) and implementing 5 missing graph writers (DocumentGraphWriter, DockerComposeGraphWriter, HostGraphWriter, EndpointGraphWriter, ContainerGraphWriter) following the proven SwagGraphWriter pattern. The implementation uses Test-Driven Development (TDD) with strict red-green-refactor cycles, leveraging parallel execution for maximum efficiency. Performance target: ≥20k edges/min with 2000-row UNWIND batches.

**Success Criteria:**
- All 11 entity constraints implemented and verified in Neo4j
- 5 new graph writers implemented with 100% test coverage
- All writers achieve ≥20k edges/min throughput target
- Refactor ingest_docker_compose.py to use DockerComposeGraphWriter
- Zero breaking changes to existing SwagGraphWriter functionality

**Estimated Effort:** ~16-20 hours distributed across 3 parallel agents
- Phase 1 (Constraints): 2 hours (sequential)
- Phase 2 (Writers): 8-10 hours (parallel: 3 agents)
- Phase 3 (Integration): 4-6 hours (parallel: 3 agents)
- Phase 4 (Testing): 2-4 hours (parallel: unit/integration/performance)

## Relevant Context

**Investigation Documents:**
- `/home/jmagar/code/taboot/docs/neo4j-graph-patterns-research.md` - Comprehensive research on UNWIND patterns, constraints, composite keys, performance optimization
- `/home/jmagar/code/taboot/packages/graph/docs/GRAPH_SCHEMA.md` - Canonical graph schema documentation with all node labels and relationships

**Init-Project Documentation:**
- Not present (no PRD/user flows/feature specs for this infrastructure work)

**Existing Implementations:**
- `/home/jmagar/code/taboot/packages/graph/writers/swag_writer.py` - Template for new writers (lines 1-217)
- `/home/jmagar/code/taboot/packages/graph/writers/batched.py` - Abstract batched writer (lines 1-99)
- `/home/jmagar/code/taboot/packages/graph/client.py` - Neo4j client with connection pooling (lines 1-272)

**Schema Files:**
- `/home/jmagar/code/taboot/specs/001-taboot-rag-platform/contracts/neo4j-constraints.cypher` - Current constraints (4 entities only)
- `/home/jmagar/code/taboot/packages/schemas/models/__init__.py` - Pydantic models (lines 1-403)

## Investigation Artifacts

No external investigation artifacts - all context gathered from existing codebase and research documents.

## Current System Overview

**Implemented Constraints (4/11 entities):**
- `Service.name` (UNIQUE) - lines 6-9 in neo4j-constraints.cypher
- `Host.hostname` (UNIQUE) - lines 11-15
- `IP.addr` (UNIQUE) - lines 17-22
- `Proxy.name` (UNIQUE) - lines 23-28

**Missing Constraints (7/11 entities):**
- `Container` - composite unique on (compose_project, compose_service)
- `Network` - unique on cidr
- `User` - composite unique on (provider, username)
- `Repository` - composite unique on (platform, org, name)
- `Package` - composite unique on (name, version, source)
- `Document` - unique on doc_id (currently named "Doc" - needs renaming)
- `Credential` - unique on id

**Implemented Writers (1/6 needed):**
- `SwagGraphWriter` - Proxy nodes + ROUTES_TO relationships (lines 1-217 in swag_writer.py)

**Missing Writers (5/6 needed):**
- `DocumentGraphWriter` - Document nodes + MENTIONS relationships
- `DockerComposeGraphWriter` - Container/Service nodes + RUNS/EXPOSES/DEPENDS_ON relationships
- `HostGraphWriter` - Host nodes + HAS_IP relationships
- `EndpointGraphWriter` - Endpoint nodes + BINDS_TO/RESOLVES_TO relationships
- `ContainerGraphWriter` - Container nodes + EXPOSES relationships

**Performance Baseline:**
- SwagGraphWriter achieves ≥20k edges/min with 2000-row UNWIND batches
- Neo4j client connection pooling configured (max 50 connections, 30s timeout)
- Batched operations use MERGE-on-ID pattern for idempotency

**Key Files:**
- `/home/jmagar/code/taboot/packages/graph/client.py` - Neo4j client (272 lines)
- `/home/jmagar/code/taboot/packages/graph/writers/swag_writer.py` - Writer template (217 lines)
- `/home/jmagar/code/taboot/apps/cli/taboot_cli/commands/ingest_docker_compose.py` - CLI command needing refactor (196 lines)
- `/home/jmagar/code/taboot/packages/schemas/models/__init__.py` - Pydantic models (403 lines)

## Implementation Plan

### Architectural Decisions

**1. Constraint Schema Consistency:**
- **Decision:** Add all 7 missing entity constraints for complete schema coverage
- **Rationale:** Infrastructure graphs require referential integrity; partial constraints lead to data quality issues
- **Implementation:** Follow Neo4j best practices from research doc (key constraints for composite IDs, unique constraints for single properties)

**2. Node Label Naming:**
- **Decision:** Keep "Doc" label as-is (do NOT rename to "Document")
- **Rationale:** Breaking change with no functional benefit; "Doc" is already established in constraint files and schema docs
- **Impact:** Pydantic model named "Document" maps to Neo4j label "Doc"

**3. Endpoint Schema Inconsistency:**
- **Decision:** Use composite index on (service, method, path) as per current constraint file
- **Rationale:** GRAPH_SCHEMA.md shows alternate schema (scheme, fqdn, port, path) but constraint file is source of truth
- **Follow-up:** File issue to resolve schema documentation inconsistency (out of scope for this plan)

**4. Writer Pattern:**
- **Decision:** Follow SwagGraphWriter pattern exactly (not abstract BatchedGraphWriter)
- **Rationale:** SwagGraphWriter is battle-tested with proven performance; BatchedGraphWriter is async stub with no usage
- **Pattern:** Direct Neo4jClient.session() usage, synchronous UNWIND, 2000-row batches

**5. New Pydantic Models:**
- **Decision:** Add missing entity models (Container, Network, User, Repository, Package, Credential)
- **Rationale:** Type-safe writer inputs prevent runtime errors; follows existing Service/Host/IP/Proxy pattern
- **Location:** `/home/jmagar/code/taboot/packages/schemas/models/__init__.py`

### Phase 1: Constraint Schema Update (Sequential - Foundation)

**Objective:** Update neo4j-constraints.cypher with all 7 missing entity constraints and verify idempotent application.

**Dependencies:** None (foundation phase - blocks all writer implementations)

#### Task 1.1: Add Missing Pydantic Models

**Agent:** programmer

**Files:**
- `/home/jmagar/code/taboot/packages/schemas/models/__init__.py` (lines 298-403)

**Changes:**
```python
# Add after line 374 (after Endpoint class):

class Container(GraphNodeBase):
    """Container node entity (Neo4j).

    Per data-model.md: Represents a containerized runtime unit.
    Composite unique index on (compose_project, compose_service).
    """

    name: str = Field(..., min_length=1, max_length=256, description="Container name")
    image: str = Field(..., min_length=1, max_length=512, description="Docker image")
    tag: str | None = Field(default=None, max_length=128, description="Image tag")
    compose_service: str = Field(..., min_length=1, max_length=256, description="Compose service name")
    compose_project: str = Field(..., min_length=1, max_length=256, description="Compose project name")
    ports: list[int] | None = Field(default=None, description="Exposed ports")
    environment: list[str] | None = Field(default=None, description="Environment variables")


class Network(GraphNodeBase):
    """Network node entity (Neo4j).

    Per data-model.md: Represents an L2/L3 network segment.
    Unique constraint on cidr.
    """

    name: str = Field(..., min_length=1, max_length=256, description="Network name")
    cidr: str = Field(..., min_length=1, max_length=64, description="CIDR notation (unique)")
    vlan: int | None = Field(default=None, ge=1, le=4094, description="VLAN ID")


class User(GraphNodeBase):
    """User node entity (Neo4j).

    Per data-model.md: Represents a human or service principal.
    Composite unique index on (provider, username).
    """

    username: str = Field(..., min_length=1, max_length=256, description="Username")
    provider: str = Field(..., min_length=1, max_length=64, description="Auth provider (local|unifi|tailscale|github|oidc)")
    active: bool = Field(default=True, description="Account active status")


class Repository(GraphNodeBase):
    """Repository node entity (Neo4j).

    Per data-model.md: Represents a code repository.
    Composite unique index on (platform, org, name).
    """

    platform: str = Field(..., min_length=1, max_length=64, description="Platform (github|gitlab|bitbucket)")
    org: str = Field(..., min_length=1, max_length=256, description="Organization/owner name")
    name: str = Field(..., min_length=1, max_length=256, description="Repository name")
    default_branch: str | None = Field(default=None, max_length=128, description="Default branch")
    visibility: str | None = Field(default=None, max_length=32, description="Visibility (public|private|internal)")


class Package(GraphNodeBase):
    """Package node entity (Neo4j).

    Per data-model.md: Represents a software package or container image.
    Composite unique index on (name, version, source).
    """

    name: str = Field(..., min_length=1, max_length=256, description="Package name")
    version: str = Field(..., min_length=1, max_length=128, description="Package version")
    source: str = Field(..., min_length=1, max_length=64, description="Package source (pypi|npm|dockerhub|ghcr)")
    license: str | None = Field(default=None, max_length=128, description="License identifier")


class Credential(GraphNodeBase):
    """Credential node entity (Neo4j).

    Per data-model.md: Represents an API key or secret reference (metadata only).
    Unique constraint on id.
    """

    id: str = Field(..., min_length=1, max_length=128, description="Credential ID (unique)")
    kind: str = Field(..., min_length=1, max_length=64, description="Credential kind (token|key|password)")
    scope: str | None = Field(default=None, max_length=256, description="Access scope")
    rotates_after: datetime | None = Field(default=None, description="Rotation deadline")


# Update __all__ export (line 378):
__all__ = [
    # ... existing exports ...
    "Container",
    "Network",
    "User",
    "Repository",
    "Package",
    "Credential",
]
```

**TDD Cycle:**
1. **RED:** Write test_new_entity_models.py validating all 7 new models
2. **GREEN:** Implement models with proper field validation
3. **REFACTOR:** Ensure consistent naming conventions and field descriptions

**Depends on:** None

**Risks:**
- Field validation rules may need adjustment after review
- Enum types for provider/platform/source may be needed (use str for now)

#### Task 1.2: Update Neo4j Constraints File

**Agent:** programmer

**Files:**
- `/home/jmagar/code/taboot/specs/001-taboot-rag-platform/contracts/neo4j-constraints.cypher` (lines 1-125)

**Changes:**
```cypher
# Add after line 33 (after Endpoint composite index):

// Container node constraints (composite unique on compose_project + compose_service)
CREATE CONSTRAINT container_composite_unique
IF NOT EXISTS
FOR (c:Container)
REQUIRE (c.compose_project, c.compose_service) IS NODE KEY;

// Network node constraints
CREATE CONSTRAINT network_cidr_unique
IF NOT EXISTS
FOR (n:Network)
REQUIRE n.cidr IS UNIQUE;

// User node constraints (composite unique on provider + username)
CREATE CONSTRAINT user_provider_username_unique
IF NOT EXISTS
FOR (u:User)
REQUIRE (u.provider, u.username) IS NODE KEY;

// Repository node constraints (composite unique on platform + org + name)
CREATE CONSTRAINT repository_composite_unique
IF NOT EXISTS
FOR (r:Repository)
REQUIRE (r.platform, r.org, r.name) IS NODE KEY;

// Package node constraints (composite unique on name + version + source)
CREATE CONSTRAINT package_composite_unique
IF NOT EXISTS
FOR (p:Package)
REQUIRE (p.name, p.version, p.source) IS NODE KEY;

// Document node constraints (keep label as "Doc" for backwards compatibility)
CREATE CONSTRAINT doc_doc_id_unique
IF NOT EXISTS
FOR (d:Doc)
REQUIRE d.doc_id IS UNIQUE;

// Credential node constraints
CREATE CONSTRAINT credential_id_unique
IF NOT EXISTS
FOR (c:Credential)
REQUIRE c.id IS UNIQUE;

# Update comment at line 120-124:
// Expected output:
// - 11 unique/key constraints (Service.name, Host.hostname, IP.addr, Proxy.name,
//   Container(compose_project,compose_service), Network.cidr, User(provider,username),
//   Repository(platform,org,name), Package(name,version,source), Doc.doc_id, Credential.id)
// - 1 composite index (Endpoint)
// - 11 property indexes (version, extraction_version, updated_at, confidence, host, chunk_id, doc_id)
// - 2 full-text indexes (Service, Host)
```

**TDD Cycle:**
1. **RED:** Test constraint application fails on duplicate entities
2. **GREEN:** Apply constraints to Neo4j (idempotent with IF NOT EXISTS)
3. **REFACTOR:** Verify SHOW CONSTRAINTS returns all 11 constraints

**Depends on:** Task 1.1 (needs Pydantic models for reference)

**Risks:**
- NODE KEY constraints enforce existence + uniqueness (may fail on null values if existing data incomplete)
- Composite constraints require all fields present in MERGE operations

#### Task 1.3: Verify Constraint Application

**Agent:** programmer

**Files:**
- `/home/jmagar/code/taboot/apps/cli/taboot_cli/commands/init.py` (verification only - no changes)

**Changes:** None (verification task)

**Verification Steps:**
```bash
# 1. Apply constraints
uv run apps/cli init

# 2. Verify constraint count
uv run apps/cli graph query "SHOW CONSTRAINTS" | grep "CONSTRAINT" | wc -l
# Expected: 11

# 3. Verify specific constraints
uv run apps/cli graph query "SHOW CONSTRAINTS WHERE name CONTAINS 'container'"
uv run apps/cli graph query "SHOW CONSTRAINTS WHERE name CONTAINS 'network'"
uv run apps/cli graph query "SHOW CONSTRAINTS WHERE name CONTAINS 'user'"
uv run apps/cli graph query "SHOW CONSTRAINTS WHERE name CONTAINS 'repository'"
uv run apps/cli graph query "SHOW CONSTRAINTS WHERE name CONTAINS 'package'"
uv run apps/cli graph query "SHOW CONSTRAINTS WHERE name CONTAINS 'doc'"
uv run apps/cli graph query "SHOW CONSTRAINTS WHERE name CONTAINS 'credential'"
```

**TDD Cycle:**
1. **RED:** Test constraint violations throw ConstraintValidationFailed
2. **GREEN:** Verify all constraints enforced correctly
3. **REFACTOR:** Document constraint behavior in GRAPH_SCHEMA.md

**Depends on:** Task 1.2

**Risks:**
- Constraint application may fail if existing test data violates new constraints (wipe DB with docker volume rm)

---

### Phase 2: Graph Writer Implementation (Parallel - 3 Agents)

**Objective:** Implement 5 missing graph writers following SwagGraphWriter pattern with 100% test coverage.

**Dependencies:** Phase 1 complete (constraints must exist before writers can test idempotency)

**Parallelization Strategy:**
- **Agent 1 (programmer):** DocumentGraphWriter + ContainerGraphWriter (2 writers)
- **Agent 2 (programmer):** DockerComposeGraphWriter + HostGraphWriter (2 writers)
- **Agent 3 (programmer):** EndpointGraphWriter (1 writer)

#### Task 2.1: Implement DocumentGraphWriter

**Agent:** Agent 1 (programmer)

**Files:**
- `/home/jmagar/code/taboot/packages/graph/writers/document_writer.py` (NEW - 200 lines)
- `/home/jmagar/code/taboot/tests/packages/graph/writers/test_document_writer.py` (NEW - 150 lines)

**Implementation Pattern (following SwagGraphWriter):**
```python
"""DocumentGraphWriter - Batched Neo4j writer for document ingestion.

Implements GraphWriterPort using batched UNWIND operations for high throughput.
Follows the pattern from packages/graph/writers/swag_writer.py.

Performance target: ≥20k edges/min with 2k-row UNWIND batches.
"""

import logging
from typing import Any
from uuid import UUID

from packages.graph.client import Neo4jClient
from packages.schemas.models import Document

logger = logging.getLogger(__name__)


class DocumentGraphWriter:
    """Batched Neo4j writer for Document node and MENTIONS relationship ingestion.

    Attributes:
        neo4j_client: Neo4j client instance with connection pooling.
        batch_size: Number of rows per UNWIND batch (default 2000).
    """

    def __init__(self, neo4j_client: Neo4jClient, batch_size: int = 2000) -> None:
        """Initialize DocumentGraphWriter with Neo4j client."""
        self.neo4j_client = neo4j_client
        self.batch_size = batch_size
        logger.info(f"Initialized DocumentGraphWriter (batch_size={batch_size})")

    def write_documents(self, documents: list[Document]) -> dict[str, int]:
        """Write Doc nodes to Neo4j using batched UNWIND.

        Creates or updates Doc nodes with all properties.
        Uses MERGE on unique key (doc_id) for idempotency.

        Args:
            documents: List of Document entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total documents written
                - batches_executed: Number of batches executed
        """
        if not documents:
            logger.info("No documents to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare document parameters
        doc_params = [
            {
                "doc_id": str(d.doc_id),  # UUID to string
                "source_url": d.source_url,
                "source_type": d.source_type.value,
                "content_hash": d.content_hash,
                "ingested_at": d.ingested_at.isoformat(),
                "extraction_state": d.extraction_state.value,
                "extraction_version": d.extraction_version,
                "updated_at": d.updated_at.isoformat(),
                "metadata": d.metadata or {},
            }
            for d in documents
        ]

        # Execute in batches
        with self.neo4j_client.session() as session:
            for i in range(0, len(doc_params), self.batch_size):
                batch = doc_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MERGE (d:Doc {doc_id: row.doc_id})
                SET d.source_url = row.source_url,
                    d.source_type = row.source_type,
                    d.content_hash = row.content_hash,
                    d.ingested_at = row.ingested_at,
                    d.extraction_state = row.extraction_state,
                    d.extraction_version = row.extraction_version,
                    d.updated_at = row.updated_at,
                    d.metadata = row.metadata
                RETURN count(d) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote document batch {batches_executed}: "
                    f"{len(batch)} rows, "
                    f"counters={summary.counters}"
                )

        logger.info(f"Wrote {total_written} Doc node(s) in {batches_executed} batch(es)")
        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_mentions(
        self,
        doc_id: UUID,
        mentions: list[dict[str, Any]]
    ) -> dict[str, int]:
        """Write MENTIONS relationships to Neo4j using batched UNWIND.

        Creates relationships from Doc node to entity nodes (Service, Host, Endpoint, etc.)
        with provenance metadata (span, section, confidence, tier).

        Args:
            doc_id: Document UUID (source node).
            mentions: List of mention dictionaries with keys:
                - target_label: str (Service|Host|Endpoint|Package|User|Network)
                - target_id: str (unique identifier for target entity)
                - span: str (text span from document)
                - section: str (document section/heading)
                - confidence: float (0.0-1.0)
                - tier: str (A|B|C - extraction tier)

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total relationships written
                - batches_executed: Number of batches executed
        """
        if not mentions:
            logger.info("No mentions to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        with self.neo4j_client.session() as session:
            for i in range(0, len(mentions), self.batch_size):
                batch = mentions[i : i + self.batch_size]

                # Group by target_label for efficient MATCH queries
                for label in set(m["target_label"] for m in batch):
                    label_batch = [m for m in batch if m["target_label"] == label]

                    # Note: Using parameterized label via apoc.merge.relationship
                    # or dynamic Cypher construction (label validated against known set)
                    query = f"""
                    UNWIND $rows AS row
                    MATCH (d:Doc {{doc_id: $doc_id}})
                    MATCH (t:{label} {{name: row.target_id}})
                    MERGE (d)-[r:MENTIONS]->(t)
                    SET r.span = row.span,
                        r.section = row.section,
                        r.confidence = row.confidence,
                        r.tier = row.tier
                    RETURN count(r) AS created_count
                    """

                    result = session.run(
                        query,
                        {
                            "doc_id": str(doc_id),
                            "rows": label_batch
                        }
                    )
                    summary = result.consume()

                    total_written += len(label_batch)
                    batches_executed += 1

                    logger.debug(
                        f"Wrote MENTIONS batch {batches_executed}: "
                        f"{len(label_batch)} relationships to {label}, "
                        f"counters={summary.counters}"
                    )

        logger.info(
            f"Wrote {total_written} MENTIONS relationship(s) in {batches_executed} batch(es)"
        )
        return {"total_written": total_written, "batches_executed": batches_executed}


# Export public API
__all__ = ["DocumentGraphWriter"]
```

**TDD Cycle:**
1. **RED:** Write test_write_documents_empty_list(), test_write_documents_single(), test_write_documents_batch_2000(), test_write_documents_idempotent()
2. **GREEN:** Implement write_documents() with UNWIND batching
3. **REFACTOR:** Extract common batching logic, improve logging

4. **RED:** Write test_write_mentions_empty_list(), test_write_mentions_single(), test_write_mentions_multiple_labels()
5. **GREEN:** Implement write_mentions() with label grouping
6. **REFACTOR:** Validate target_label against known set, improve error messages

**Depends on:** Phase 1 Task 1.3 (Doc constraint must exist)

**Risks:**
- Dynamic Cypher construction with f-strings requires label validation (prevent injection)
- MENTIONS target nodes must exist before relationship creation (may fail if entity not yet ingested)

#### Task 2.2: Implement ContainerGraphWriter

**Agent:** Agent 1 (programmer)

**Files:**
- `/home/jmagar/code/taboot/packages/graph/writers/container_writer.py` (NEW - 180 lines)
- `/home/jmagar/code/taboot/tests/packages/graph/writers/test_container_writer.py` (NEW - 120 lines)

**Implementation Pattern:**
```python
"""ContainerGraphWriter - Batched Neo4j writer for container ingestion."""

import logging
from typing import Any

from packages.graph.client import Neo4jClient
from packages.schemas.models import Container

logger = logging.getLogger(__name__)


class ContainerGraphWriter:
    """Batched Neo4j writer for Container nodes and EXPOSES relationships."""

    def __init__(self, neo4j_client: Neo4jClient, batch_size: int = 2000) -> None:
        self.neo4j_client = neo4j_client
        self.batch_size = batch_size
        logger.info(f"Initialized ContainerGraphWriter (batch_size={batch_size})")

    def write_containers(self, containers: list[Container]) -> dict[str, int]:
        """Write Container nodes to Neo4j using batched UNWIND.

        Uses MERGE on composite key (compose_project, compose_service).
        """
        # Implementation follows DocumentGraphWriter pattern
        # MERGE on (c:Container {compose_project: row.compose_project, compose_service: row.compose_service})
        pass

    def write_exposes_relationships(
        self,
        relationships: list[dict[str, Any]]
    ) -> dict[str, int]:
        """Write EXPOSES relationships from Container to Service.

        Args:
            relationships: List with keys:
                - container_project: str
                - container_service: str
                - service_name: str
        """
        # Implementation follows SwagGraphWriter.write_routes() pattern
        pass


__all__ = ["ContainerGraphWriter"]
```

**TDD Cycle:**
1. **RED:** Write test_write_containers_composite_key_uniqueness()
2. **GREEN:** Implement with composite MERGE
3. **REFACTOR:** Validate all composite key fields present

4. **RED:** Write test_write_exposes_creates_service_if_missing()
5. **GREEN:** Implement with MATCH Container, MERGE Service, MERGE relationship
6. **REFACTOR:** Ensure idempotency on re-run

**Depends on:** Phase 1 Task 1.3 (Container constraint must exist)

**Risks:**
- Composite key MERGE requires both fields non-null (validate in Pydantic model)

#### Task 2.3: Implement DockerComposeGraphWriter

**Agent:** Agent 2 (programmer)

**Files:**
- `/home/jmagar/code/taboot/packages/graph/writers/docker_compose_writer.py` (NEW - 250 lines)
- `/home/jmagar/code/taboot/tests/packages/graph/writers/test_docker_compose_writer.py` (NEW - 180 lines)

**Implementation Pattern:**
```python
"""DockerComposeGraphWriter - Batched Neo4j writer for Docker Compose ingestion."""

import logging
from typing import Any

from packages.graph.client import Neo4jClient
from packages.schemas.models import Container, Service

logger = logging.getLogger(__name__)


class DockerComposeGraphWriter:
    """Batched Neo4j writer for Docker Compose structure.

    Handles:
    - Container nodes
    - Service nodes
    - RUNS relationships (Host -> Container)
    - EXPOSES relationships (Container -> Service)
    - DEPENDS_ON relationships (Service -> Service)
    - BINDS relationships (Service -> self with port/protocol properties)
    """

    def __init__(self, neo4j_client: Neo4jClient, batch_size: int = 2000) -> None:
        self.neo4j_client = neo4j_client
        self.batch_size = batch_size
        logger.info(f"Initialized DockerComposeGraphWriter (batch_size={batch_size})")

    def write_compose_structure(
        self,
        containers: list[Container],
        services: list[Service],
        relationships: dict[str, list[dict[str, Any]]]
    ) -> dict[str, int]:
        """Write complete Docker Compose structure to Neo4j.

        Args:
            containers: List of Container entities
            services: List of Service entities
            relationships: Dict with keys:
                - depends_on: List[{source: str, target: str}]
                - binds: List[{service: str, port: int, protocol: str}]
                - runs: List[{host: str, container_project: str, container_service: str}]
                - exposes: List[{container_project: str, container_service: str, service_name: str}]

        Returns:
            dict[str, int]: Combined statistics for all operations
        """
        # Implementation orchestrates multiple batched writes
        pass


__all__ = ["DockerComposeGraphWriter"]
```

**TDD Cycle:**
1. **RED:** Write test_write_compose_structure_complete_graph()
2. **GREEN:** Implement orchestration of Container + Service + all relationships
3. **REFACTOR:** Extract relationship writers to separate methods

4. **RED:** Write test_idempotent_rerun_same_compose_file()
5. **GREEN:** Verify MERGE semantics prevent duplicates
6. **REFACTOR:** Add performance logging (nodes/sec, edges/sec)

**Depends on:** Phase 1 Task 1.3, Task 2.2 (Container constraint + ContainerGraphWriter)

**Risks:**
- Complex orchestration requires transaction ordering (nodes before relationships)
- Must handle missing Service nodes (MERGE creates if needed)

#### Task 2.4: Implement HostGraphWriter

**Agent:** Agent 2 (programmer)

**Files:**
- `/home/jmagar/code/taboot/packages/graph/writers/host_writer.py` (NEW - 180 lines)
- `/home/jmagar/code/taboot/tests/packages/graph/writers/test_host_writer.py` (NEW - 120 lines)

**Implementation Pattern:**
```python
"""HostGraphWriter - Batched Neo4j writer for host ingestion."""

import logging
from typing import Any

from packages.graph.client import Neo4jClient
from packages.schemas.models import Host, IP

logger = logging.getLogger(__name__)


class HostGraphWriter:
    """Batched Neo4j writer for Host nodes and HAS_IP relationships."""

    def __init__(self, neo4j_client: Neo4jClient, batch_size: int = 2000) -> None:
        self.neo4j_client = neo4j_client
        self.batch_size = batch_size
        logger.info(f"Initialized HostGraphWriter (batch_size={batch_size})")

    def write_hosts(self, hosts: list[Host]) -> dict[str, int]:
        """Write Host nodes to Neo4j using batched UNWIND."""
        # Implementation follows DocumentGraphWriter pattern
        pass

    def write_has_ip_relationships(
        self,
        relationships: list[dict[str, Any]]
    ) -> dict[str, int]:
        """Write HAS_IP relationships from Host to IP.

        Creates IP nodes if missing (MERGE).

        Args:
            relationships: List with keys:
                - hostname: str
                - ip_addr: str
                - ip_type: str (v4|v6)
                - allocation: str (static|dhcp|unknown)
        """
        pass


__all__ = ["HostGraphWriter"]
```

**TDD Cycle:**
1. **RED:** Write test_write_hosts_with_multiple_ips()
2. **GREEN:** Implement with nested UNWIND for ip_addresses array
3. **REFACTOR:** Extract IP node creation logic

4. **RED:** Write test_write_has_ip_creates_ip_nodes()
5. **GREEN:** Implement with MERGE IP, MERGE relationship
6. **REFACTOR:** Add IP validation (IPv4/IPv6 format)

**Depends on:** Phase 1 Task 1.3 (Host + IP constraints must exist)

**Risks:**
- Nested UNWIND for IP arrays may hit batch size limits with hosts having many IPs
- IP validation should happen in Pydantic model, not writer

#### Task 2.5: Implement EndpointGraphWriter

**Agent:** Agent 3 (programmer)

**Files:**
- `/home/jmagar/code/taboot/packages/graph/writers/endpoint_writer.py` (NEW - 200 lines)
- `/home/jmagar/code/taboot/tests/packages/graph/writers/test_endpoint_writer.py` (NEW - 150 lines)

**Implementation Pattern:**
```python
"""EndpointGraphWriter - Batched Neo4j writer for endpoint ingestion."""

import logging
from typing import Any

from packages.graph.client import Neo4jClient
from packages.schemas.models import Endpoint

logger = logging.getLogger(__name__)


class EndpointGraphWriter:
    """Batched Neo4j writer for Endpoint nodes and relationships."""

    def __init__(self, neo4j_client: Neo4jClient, batch_size: int = 2000) -> None:
        self.neo4j_client = neo4j_client
        self.batch_size = batch_size
        logger.info(f"Initialized EndpointGraphWriter (batch_size={batch_size})")

    def write_endpoints(self, endpoints: list[Endpoint]) -> dict[str, int]:
        """Write Endpoint nodes to Neo4j using batched UNWIND.

        Uses composite index on (service, method, path).
        """
        # Implementation follows DocumentGraphWriter pattern
        # MERGE on (e:Endpoint {service: row.service, method: row.method, path: row.path})
        pass

    def write_binds_to_relationships(
        self,
        relationships: list[dict[str, Any]]
    ) -> dict[str, int]:
        """Write BINDS_TO relationships from Service to Endpoint."""
        pass

    def write_resolves_to_relationships(
        self,
        relationships: list[dict[str, Any]]
    ) -> dict[str, int]:
        """Write RESOLVES_TO relationships from Endpoint to IP."""
        pass


__all__ = ["EndpointGraphWriter"]
```

**TDD Cycle:**
1. **RED:** Write test_write_endpoints_composite_index()
2. **GREEN:** Implement with composite MERGE (service, method, path)
3. **REFACTOR:** Validate all index fields present

4. **RED:** Write test_write_binds_to_creates_service_if_missing()
5. **GREEN:** Implement with MERGE Service + Endpoint
6. **REFACTOR:** Ensure idempotency

7. **RED:** Write test_write_resolves_to_validates_ip_exists()
8. **GREEN:** Implement with MATCH Endpoint, MERGE IP, MERGE relationship
9. **REFACTOR:** Add error handling for missing Endpoint nodes

**Depends on:** Phase 1 Task 1.3 (Endpoint constraint must exist)

**Risks:**
- Composite index requires all 3 fields in MERGE (service, method, path)
- RESOLVES_TO assumes IP nodes exist (may fail if IP not yet created)

---

### Phase 3: Integration and Refactoring (Parallel - 3 Agents)

**Objective:** Integrate new writers into existing commands and use-cases, refactor ingest_docker_compose.py.

**Dependencies:** Phase 2 complete (all writers implemented)

#### Task 3.1: Update Graph Writers __init__.py

**Agent:** Agent 1 (programmer)

**Files:**
- `/home/jmagar/code/taboot/packages/graph/writers/__init__.py` (lines 1-10)

**Changes:**
```python
"""Graph writers for batched Neo4j operations."""

from packages.graph.writers.container_writer import ContainerGraphWriter
from packages.graph.writers.docker_compose_writer import DockerComposeGraphWriter
from packages.graph.writers.document_writer import DocumentGraphWriter
from packages.graph.writers.endpoint_writer import EndpointGraphWriter
from packages.graph.writers.host_writer import HostGraphWriter
from packages.graph.writers.swag_writer import SwagGraphWriter

__all__ = [
    "SwagGraphWriter",
    "DocumentGraphWriter",
    "ContainerGraphWriter",
    "DockerComposeGraphWriter",
    "HostGraphWriter",
    "EndpointGraphWriter",
]
```

**TDD Cycle:**
1. **RED:** Test import failures before adding to __init__.py
2. **GREEN:** Add imports and exports
3. **REFACTOR:** Verify no circular dependencies

**Depends on:** Phase 2 all tasks

**Risks:** None (pure import aggregation)

#### Task 3.2: Refactor ingest_docker_compose.py to Use DockerComposeGraphWriter

**Agent:** Agent 2 (programmer)

**Files:**
- `/home/jmagar/code/taboot/apps/cli/taboot_cli/commands/ingest_docker_compose.py` (lines 1-196)

**Changes:**
```python
# Replace _write_to_neo4j() function (lines 134-192) with:

def _write_to_neo4j(
    services: list[dict[str, str]],
    relationships: list[dict[str, str | int]],
) -> None:
    """Write services and relationships to Neo4j using DockerComposeGraphWriter.

    Args:
        services: List of service dictionaries with name, image, version.
        relationships: List of relationship dictionaries with type, source, target/port.
    """
    from packages.graph.client import Neo4jClient
    from packages.graph.writers import DockerComposeGraphWriter
    from packages.schemas.models import Container, Service

    # Convert dict data to Pydantic models
    # (simplified - full implementation needs container extraction from services)
    service_models = [
        Service(
            name=s["name"],
            image=s.get("image"),
            version=s.get("version"),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        for s in services
    ]

    # Group relationships by type
    depends_on = [r for r in relationships if r["type"] == "DEPENDS_ON"]
    binds = [r for r in relationships if r["type"] == "BINDS"]

    # Write using DockerComposeGraphWriter
    with Neo4jClient() as client:
        writer = DockerComposeGraphWriter(client)
        result = writer.write_compose_structure(
            containers=[],  # TODO: Extract from services
            services=service_models,
            relationships={
                "depends_on": depends_on,
                "binds": binds,
                "runs": [],
                "exposes": [],
            }
        )

        logger.info(
            "Wrote Docker Compose structure: %s",
            result
        )
```

**TDD Cycle:**
1. **RED:** Test old implementation still works (baseline)
2. **GREEN:** Refactor to use DockerComposeGraphWriter
3. **REFACTOR:** Remove old direct Cypher queries

**Depends on:** Phase 2 Task 2.3 (DockerComposeGraphWriter must exist)

**Risks:**
- DockerComposeReader output format may not match writer input (need adapter logic)
- Container extraction from services requires understanding Docker Compose structure

#### Task 3.3: Update Core Use-Cases to Use New Writers

**Agent:** Agent 3 (programmer)

**Files:**
- `/home/jmagar/code/taboot/packages/core/use_cases/ingest_web.py` (add DocumentGraphWriter usage)
- `/home/jmagar/code/taboot/packages/core/use_cases/ingest_github.py` (add DocumentGraphWriter usage)
- `/home/jmagar/code/taboot/packages/core/use_cases/ingest_docker_compose.py` (NEW - orchestrate DockerComposeGraphWriter)

**Changes (ingest_web.py example):**
```python
# Add after document ingestion (line ~80):

from packages.graph.client import Neo4jClient
from packages.graph.writers import DocumentGraphWriter

# Write document to graph
with Neo4jClient() as client:
    writer = DocumentGraphWriter(client)
    writer.write_documents([document])
```

**TDD Cycle:**
1. **RED:** Test use-case fails without graph write
2. **GREEN:** Add DocumentGraphWriter calls
3. **REFACTOR:** Extract graph write logic to shared helper

**Depends on:** Phase 2 Task 2.1 (DocumentGraphWriter must exist)

**Risks:**
- Core layer should not directly import adapters (consider creating port interface)
- Transaction boundaries need careful design (ingest + graph write should be atomic or separate?)

---

### Phase 4: Testing and Performance Validation (Parallel)

**Objective:** Comprehensive test coverage and performance validation for all writers.

**Dependencies:** Phase 3 complete (all writers integrated)

#### Task 4.1: Unit Tests for All Writers

**Agent:** Agent 1 (programmer)

**Files:**
- `/home/jmagar/code/taboot/tests/packages/graph/writers/test_document_writer.py`
- `/home/jmagar/code/taboot/tests/packages/graph/writers/test_container_writer.py`
- `/home/jmagar/code/taboot/tests/packages/graph/writers/test_docker_compose_writer.py`
- `/home/jmagar/code/taboot/tests/packages/graph/writers/test_host_writer.py`
- `/home/jmagar/code/taboot/tests/packages/graph/writers/test_endpoint_writer.py`

**Test Coverage Requirements:**
- Empty list handling (return early with zero counts)
- Single entity write (verify Neo4j node created)
- Batch size boundary (2000, 2001, 4000 rows)
- Idempotency (run twice, verify no duplicates)
- Constraint violations (test error handling)
- Relationship write with missing target nodes

**TDD Cycle:**
Already completed during Phase 2 implementation (red-green-refactor per task)

**Verification:**
```bash
# Run unit tests
uv run pytest tests/packages/graph/writers -m "unit" -v

# Check coverage
uv run pytest --cov=packages/graph/writers tests/packages/graph/writers
# Target: ≥95% line coverage
```

**Depends on:** Phase 2 all tasks (tests written during implementation)

**Risks:** None (tests already exist from TDD cycles)

#### Task 4.2: Integration Tests

**Agent:** Agent 2 (programmer)

**Files:**
- `/home/jmagar/code/taboot/tests/packages/graph/writers/integration/test_writer_integration.py` (NEW - 200 lines)

**Test Scenarios:**
1. **End-to-End Docker Compose Ingestion:**
   - Parse sample docker-compose.yaml
   - Write with DockerComposeGraphWriter
   - Query Neo4j to verify all nodes and relationships created
   - Verify constraint enforcement

2. **Multi-Writer Coordination:**
   - Write Host with HostGraphWriter
   - Write Containers with ContainerGraphWriter
   - Write RUNS relationships
   - Verify graph connectivity

3. **Document + Mentions Flow:**
   - Write Document with DocumentGraphWriter
   - Write Service/Host nodes
   - Write MENTIONS relationships
   - Traverse graph: MATCH (d:Doc)-[:MENTIONS]->(s:Service)

**Integration Test Requirements:**
```python
@pytest.mark.integration
@pytest.mark.neo4j
def test_docker_compose_end_to_end():
    """Test complete Docker Compose ingestion workflow."""
    # Requires Neo4j test container or live instance
    pass
```

**Verification:**
```bash
# Run integration tests (requires Neo4j running)
docker compose up -d taboot-graph
uv run pytest tests/packages/graph/writers/integration -m "integration" -v
```

**Depends on:** Phase 3 all tasks (writers must be integrated)

**Risks:**
- Integration tests require Neo4j running (document in test setup)
- Test data cleanup required between tests (use fixtures with teardown)

#### Task 4.3: Performance Benchmarks

**Agent:** Agent 3 (programmer)

**Files:**
- `/home/jmagar/code/taboot/tests/packages/graph/writers/performance/test_writer_performance.py` (NEW - 150 lines)

**Benchmark Scenarios:**
1. **Throughput Test (20k edges/min target):**
   - Write 10,000 Service nodes in batches of 2000
   - Measure nodes/sec
   - Write 20,000 DEPENDS_ON relationships
   - Measure edges/sec
   - Assert ≥20k edges/min (333 edges/sec)

2. **Batch Size Comparison:**
   - Test batch sizes: 500, 1000, 2000, 5000
   - Measure throughput for each
   - Verify 2000 is optimal (per research doc)

3. **Idempotency Performance:**
   - Write 5000 nodes
   - Re-run same write (MERGE should be fast on duplicates)
   - Compare first-run vs re-run latency

**Performance Test Requirements:**
```python
@pytest.mark.performance
@pytest.mark.slow
def test_writer_throughput_20k_edges_per_min():
    """Verify writer achieves ≥20k edges/min target."""
    # Generate 20,000 test relationships
    # Time the write operation
    # Assert edges/sec ≥ 333
    pass
```

**Verification:**
```bash
# Run performance tests (tagged as slow)
uv run pytest tests/packages/graph/writers/performance -m "performance" -v

# Expected output:
# test_writer_throughput_20k_edges_per_min PASSED (2.5s)
# Achieved: 450 edges/sec (27,000 edges/min) ✓
```

**Depends on:** Phase 3 all tasks (writers must be integrated)

**Risks:**
- Performance tests may fail on slow hardware (CI may need dedicated Neo4j instance)
- Baseline varies by hardware (document test environment requirements)

---

## File Changes Matrix

### New Files (10 files)

| File Path | Lines | Agent | Phase | Description |
|-----------|-------|-------|-------|-------------|
| `/home/jmagar/code/taboot/packages/graph/writers/document_writer.py` | 200 | Agent 1 | 2 | DocumentGraphWriter implementation |
| `/home/jmagar/code/taboot/packages/graph/writers/container_writer.py` | 180 | Agent 1 | 2 | ContainerGraphWriter implementation |
| `/home/jmagar/code/taboot/packages/graph/writers/docker_compose_writer.py` | 250 | Agent 2 | 2 | DockerComposeGraphWriter implementation |
| `/home/jmagar/code/taboot/packages/graph/writers/host_writer.py` | 180 | Agent 2 | 2 | HostGraphWriter implementation |
| `/home/jmagar/code/taboot/packages/graph/writers/endpoint_writer.py` | 200 | Agent 3 | 2 | EndpointGraphWriter implementation |
| `/home/jmagar/code/taboot/tests/packages/graph/writers/test_document_writer.py` | 150 | Agent 1 | 2 | Unit tests for DocumentGraphWriter |
| `/home/jmagar/code/taboot/tests/packages/graph/writers/test_container_writer.py` | 120 | Agent 1 | 2 | Unit tests for ContainerGraphWriter |
| `/home/jmagar/code/taboot/tests/packages/graph/writers/test_docker_compose_writer.py` | 180 | Agent 2 | 2 | Unit tests for DockerComposeGraphWriter |
| `/home/jmagar/code/taboot/tests/packages/graph/writers/test_host_writer.py` | 120 | Agent 2 | 2 | Unit tests for HostGraphWriter |
| `/home/jmagar/code/taboot/tests/packages/graph/writers/test_endpoint_writer.py` | 150 | Agent 3 | 2 | Unit tests for EndpointGraphWriter |

### Modified Files (4 files)

| File Path | Lines Changed | Agent | Phase | Description |
|-----------|---------------|-------|-------|-------------|
| `/home/jmagar/code/taboot/packages/schemas/models/__init__.py` | +120 (lines 374-494) | programmer | 1 | Add 7 new Pydantic models + __all__ update |
| `/home/jmagar/code/taboot/specs/001-taboot-rag-platform/contracts/neo4j-constraints.cypher` | +50 (lines 34-84, 120-128) | programmer | 1 | Add 7 new constraints + update comments |
| `/home/jmagar/code/taboot/packages/graph/writers/__init__.py` | +8 (lines 3-10) | Agent 1 | 3 | Add new writer imports and exports |
| `/home/jmagar/code/taboot/apps/cli/taboot_cli/commands/ingest_docker_compose.py` | ~60 (lines 134-192) | Agent 2 | 3 | Refactor to use DockerComposeGraphWriter |

### Documentation Files (1 file)

| File Path | Lines Changed | Agent | Phase | Description |
|-----------|---------------|-------|-------|-------------|
| `/home/jmagar/code/taboot/packages/graph/docs/GRAPH_SCHEMA.md` | +30 (lines 68-98) | programmer | 1 | Update constraint documentation |

**Total New Files:** 10 (1,730 lines)
**Total Modified Files:** 4 (~200 lines changed)
**Total Documentation:** 1 (+30 lines)

---

## Testing Strategy

### TDD Discipline

**Red-Green-Refactor Cycle (Mandatory for All Tasks):**

1. **RED Phase:**
   - Write failing test FIRST (before any implementation)
   - Test must fail for the right reason (not syntax error)
   - Verify test failure message matches expected behavior

2. **GREEN Phase:**
   - Write minimal code to pass the test
   - No premature optimization
   - Code can be ugly/duplicated in this phase

3. **REFACTOR Phase:**
   - Extract common patterns
   - Improve naming and structure
   - All tests must still pass after refactor

**Enforcement:**
- Each task specifies explicit TDD cycle steps
- Agents must report test failures before implementation
- No code merged without corresponding test

### Test Coverage Targets

**Unit Tests:**
- **Target:** ≥95% line coverage for all writers
- **Scope:** Individual writer methods in isolation
- **Mocking:** Neo4j client responses (no live DB needed)
- **Speed:** <1s per test, <10s total suite

**Integration Tests:**
- **Target:** End-to-end workflow coverage
- **Scope:** Multi-writer coordination, constraint validation
- **Dependencies:** Live Neo4j instance (docker-compose)
- **Speed:** <30s per test, <2min total suite

**Performance Tests:**
- **Target:** ≥20k edges/min throughput validation
- **Scope:** Batch size optimization, idempotency overhead
- **Dependencies:** Isolated Neo4j instance
- **Speed:** Marked as "slow", optional in CI

### Test Organization

```
tests/packages/graph/writers/
├── test_document_writer.py          # Unit tests
├── test_container_writer.py         # Unit tests
├── test_docker_compose_writer.py    # Unit tests
├── test_host_writer.py              # Unit tests
├── test_endpoint_writer.py          # Unit tests
├── integration/
│   └── test_writer_integration.py   # Integration tests
└── performance/
    └── test_writer_performance.py   # Performance benchmarks
```

**Test Markers:**
```python
@pytest.mark.unit           # Fast, no external dependencies
@pytest.mark.integration    # Requires Neo4j running
@pytest.mark.performance    # Throughput benchmarks
@pytest.mark.slow           # Tests >5s execution time
@pytest.mark.neo4j          # Requires Neo4j (integration + performance)
```

**Test Commands:**
```bash
# Unit tests only (fast feedback)
uv run pytest tests/packages/graph/writers -m "unit" -v

# Integration tests (requires Neo4j)
docker compose up -d taboot-graph
uv run pytest tests/packages/graph/writers -m "integration" -v

# Performance tests (optional, slow)
uv run pytest tests/packages/graph/writers -m "performance" -v

# All tests (full validation)
uv run pytest tests/packages/graph/writers -v

# Coverage report
uv run pytest --cov=packages/graph/writers --cov-report=html tests/packages/graph/writers
```

---

## Data/Schema Impacts

### Neo4j Constraints

**New Constraints (7 added):**

1. **Container:** NODE KEY on (compose_project, compose_service)
   - Enforces existence + uniqueness on composite identifier
   - Breaking change: Existing Container nodes without both fields will fail constraint
   - Mitigation: Wipe existing data or backfill missing fields

2. **Network:** UNIQUE on cidr
   - Enforces uniqueness on CIDR notation
   - No breaking changes expected (CIDR inherently unique)

3. **User:** NODE KEY on (provider, username)
   - Composite identifier for multi-provider auth
   - Breaking change: Existing User nodes without provider field will fail
   - Mitigation: Wipe existing data or default provider to 'local'

4. **Repository:** NODE KEY on (platform, org, name)
   - Composite identifier for code repos
   - No existing Repository nodes expected (new entity type)

5. **Package:** NODE KEY on (name, version, source)
   - Composite identifier for software packages
   - No existing Package nodes expected (new entity type)

6. **Document (Doc label):** UNIQUE on doc_id
   - Enforces uniqueness on document UUID
   - No breaking changes (doc_id already used as identifier)

7. **Credential:** UNIQUE on id
   - Enforces uniqueness on credential identifier
   - No existing Credential nodes expected (new entity type)

**Constraint Validation Query:**
```cypher
// Verify all 11 constraints exist
SHOW CONSTRAINTS
YIELD name, type, entityType, labelsOrTypes, properties
WHERE type IN ['UNIQUENESS', 'NODE_KEY']
RETURN name, type, entityType, labelsOrTypes, properties
ORDER BY name;

// Expected: 11 rows
// - service_name_unique (UNIQUENESS, Node, Service, [name])
// - host_hostname_unique (UNIQUENESS, Node, Host, [hostname])
// - ip_addr_unique (UNIQUENESS, Node, IP, [addr])
// - proxy_name_unique (UNIQUENESS, Node, Proxy, [name])
// - container_composite_unique (NODE_KEY, Node, Container, [compose_project, compose_service])
// - network_cidr_unique (UNIQUENESS, Node, Network, [cidr])
// - user_provider_username_unique (NODE_KEY, Node, User, [provider, username])
// - repository_composite_unique (NODE_KEY, Node, Repository, [platform, org, name])
// - package_composite_unique (NODE_KEY, Node, Package, [name, version, source])
// - doc_doc_id_unique (UNIQUENESS, Node, Doc, [doc_id])
// - credential_id_unique (UNIQUENESS, Node, Credential, [id])
```

### Pydantic Model Schema

**New Models (7 added to packages/schemas/models/__init__.py):**

- `Container` (lines ~375-390)
- `Network` (lines ~392-402)
- `User` (lines ~404-413)
- `Repository` (lines ~415-426)
- `Package` (lines ~428-438)
- `Credential` (lines ~440-450)

**Breaking Changes:**
- None (additive only - no existing model modifications)

**Validation Rules:**
- All models extend `GraphNodeBase` (inherit created_at, updated_at, extraction_version, metadata)
- Composite key fields marked as required (non-nullable)
- Field length constraints align with Neo4j string limits (max 256-512 chars)

### API Contracts

**No OpenAPI changes** - graph writers are internal adapter layer, not exposed via API.

**Internal Port Changes:**
- None (writers implement internal pattern, no formal port interface yet)

### Database Migrations

**PostgreSQL:** No changes (graph work is Neo4j only)

**Neo4j:**
- No data migrations needed (constraints are additive)
- Existing data may violate new constraints (wipe DB recommended)
- Constraint application is idempotent (IF NOT EXISTS)

**Qdrant:** No changes

---

## Success Metrics

### Functional Completeness

- [ ] All 11 Neo4j constraints exist (verify with SHOW CONSTRAINTS)
- [ ] All 7 new Pydantic models pass validation tests
- [ ] All 5 new graph writers implement write_* methods
- [ ] ingest_docker_compose.py refactored to use DockerComposeGraphWriter
- [ ] SwagGraphWriter unchanged and still passing tests

### Test Coverage

- [ ] ≥95% line coverage for packages/graph/writers/
- [ ] All unit tests passing (<10s total)
- [ ] All integration tests passing (<2min total)
- [ ] Performance tests achieve ≥20k edges/min target

### Performance Validation

**Throughput Targets (per neo4j-graph-patterns-research.md):**
- [ ] Service nodes: ≥2000 nodes/sec (UNWIND batch write)
- [ ] Relationships: ≥333 edges/sec (20k edges/min target)
- [ ] Idempotent re-run: <20% overhead vs first run

**Benchmark Commands:**
```bash
# Performance test suite
uv run pytest tests/packages/graph/writers/performance -m "performance" -v

# Manual throughput validation
uv run apps/cli graph query "
  UNWIND range(1, 10000) AS i
  CREATE (s:Service {name: 'test-service-' + i})
  RETURN count(s)
"
# Expected: <5s execution (2000+ nodes/sec)
```

### Documentation Quality

- [ ] neo4j-constraints.cypher updated with all 7 new constraints
- [ ] GRAPH_SCHEMA.md constraint section updated (lines 68-98)
- [ ] All new writer modules have docstrings with usage examples
- [ ] Test files include docstrings explaining test scenarios

### Deployment Readiness

- [ ] All tests passing in CI/CD
- [ ] No regressions in existing SwagGraphWriter tests
- [ ] Performance benchmarks documented in test output
- [ ] Breaking changes documented (constraint violations)

---

## Risk Mitigation

### Risk 1: Constraint Violations on Existing Data

**Severity:** HIGH
**Probability:** MEDIUM

**Risk:** Applying new NODE KEY constraints may fail if existing Neo4j data has null values in composite key fields.

**Mitigation:**
1. **Pre-deployment validation query:**
   ```cypher
   // Check for Container nodes missing composite key fields
   MATCH (c:Container)
   WHERE c.compose_project IS NULL OR c.compose_service IS NULL
   RETURN count(c) AS invalid_containers;

   // Expected: 0 (no invalid nodes)
   ```

2. **Fallback strategy:** If validation fails, wipe Neo4j data:
   ```bash
   docker compose down taboot-graph
   docker volume rm taboot_neo4j_data
   docker compose up -d taboot-graph
   uv run apps/cli init
   ```

3. **No migration scripts needed** - single-user system allows breaking changes

### Risk 2: Performance Degradation from Additional Constraints

**Severity:** LOW
**Probability:** LOW

**Risk:** Each constraint adds write overhead (~10-15% per research doc). Adding 7 constraints may slow writes.

**Mitigation:**
1. **Benchmark before/after:**
   ```bash
   # Before: Current 4 constraints
   uv run pytest tests/packages/graph/writers/performance -m "performance" -v

   # After: All 11 constraints
   uv run pytest tests/packages/graph/writers/performance -m "performance" -v

   # Acceptable: <20% throughput decrease
   ```

2. **Constraint necessity review:** All 7 new constraints enforce critical data integrity (no removal candidates)

3. **Batch size tuning:** May need to increase batch size from 2000 to 4211 if overhead exceeds 20%

### Risk 3: Dynamic Cypher Construction (SQL Injection Analog)

**Severity:** MEDIUM
**Probability:** LOW

**Risk:** DocumentGraphWriter.write_mentions() uses f-string for target_label (line ~180 in implementation pattern).

**Mitigation:**
1. **Whitelist validation:**
   ```python
   VALID_MENTION_LABELS = {"Service", "Host", "Endpoint", "Package", "User", "Network"}

   def write_mentions(self, doc_id: UUID, mentions: list[dict[str, Any]]) -> dict[str, int]:
       for mention in mentions:
           if mention["target_label"] not in VALID_MENTION_LABELS:
               raise ValueError(f"Invalid target_label: {mention['target_label']}")
   ```

2. **Unit test for injection:**
   ```python
   def test_write_mentions_rejects_invalid_label():
       mentions = [{"target_label": "Service); DROP DATABASE neo4j; //", ...}]
       with pytest.raises(ValueError, match="Invalid target_label"):
           writer.write_mentions(doc_id, mentions)
   ```

3. **Alternative: APOC procedures** - Use apoc.merge.relationship() for fully parameterized label (future enhancement)

### Risk 4: Test Data Cleanup Between Integration Tests

**Severity:** LOW
**Probability:** MEDIUM

**Risk:** Integration tests may leave data in Neo4j, causing subsequent test failures or false positives.

**Mitigation:**
1. **Pytest fixtures with teardown:**
   ```python
   @pytest.fixture
   def clean_neo4j():
       """Ensure Neo4j is clean before and after test."""
       client = Neo4jClient()
       client.connect()

       # Pre-test cleanup
       with client.session() as session:
           session.run("MATCH (n) DETACH DELETE n")

       yield client

       # Post-test cleanup
       with client.session() as session:
           session.run("MATCH (n) DETACH DELETE n")

       client.close()
   ```

2. **Test isolation:** Each integration test uses unique node names (e.g., f"test-service-{uuid4()}")

3. **CI/CD strategy:** Use ephemeral Neo4j containers per test suite run

### Risk 5: Parallel Agent Context Loss

**Severity:** MEDIUM
**Probability:** MEDIUM

**Risk:** Agents working in parallel may duplicate effort or create incompatible implementations.

**Mitigation:**
1. **Shared pattern enforcement:** All agents reference SwagGraphWriter as template (line 1-217 in swag_writer.py)

2. **Interface contract:**
   ```python
   # All writers must implement:
   class GraphWriter(Protocol):
       def __init__(self, neo4j_client: Neo4jClient, batch_size: int = 2000) -> None: ...
       def write_<entities>(self, entities: list[Model]) -> dict[str, int]: ...
   ```

3. **Code review checkpoint:** After Phase 2 Task 2.1-2.5 complete, review all writer interfaces for consistency before Phase 3

4. **Shared test utilities:** Create common test fixtures in conftest.py for all writer tests

---

## Parallel Execution Strategy

### Phase Dependency Graph

```
Phase 1 (Sequential - Foundation)
├── Task 1.1: Add Pydantic Models
├── Task 1.2: Update Neo4j Constraints (depends on 1.1)
└── Task 1.3: Verify Constraints (depends on 1.2)
    ↓
Phase 2 (Parallel - 3 Agents)
├── Agent 1: Task 2.1 (DocumentGraphWriter) + Task 2.2 (ContainerGraphWriter)
├── Agent 2: Task 2.3 (DockerComposeGraphWriter) + Task 2.4 (HostGraphWriter)
└── Agent 3: Task 2.5 (EndpointGraphWriter)
    ↓
Phase 3 (Parallel - 3 Agents)
├── Agent 1: Task 3.1 (Update __init__.py)
├── Agent 2: Task 3.2 (Refactor ingest_docker_compose.py)
└── Agent 3: Task 3.3 (Update core use-cases)
    ↓
Phase 4 (Parallel - 3 Agents)
├── Agent 1: Task 4.1 (Unit tests - already done in Phase 2 TDD)
├── Agent 2: Task 4.2 (Integration tests)
└── Agent 3: Task 4.3 (Performance benchmarks)
```

### Agent Assignment

**Programmer Agent (Sequential - Phase 1):**
- Handles foundation work (constraints, models)
- Single-threaded to ensure schema consistency
- Estimated time: 2 hours

**Agent 1 (programmer - Parallel):**
- Phase 2: DocumentGraphWriter + ContainerGraphWriter (2 writers)
- Phase 3: Update __init__.py (coordination)
- Phase 4: Verify unit tests (already done in TDD)
- Estimated time: 6-8 hours

**Agent 2 (programmer - Parallel):**
- Phase 2: DockerComposeGraphWriter + HostGraphWriter (2 writers)
- Phase 3: Refactor ingest_docker_compose.py (integration)
- Phase 4: Integration tests (multi-writer coordination)
- Estimated time: 8-10 hours

**Agent 3 (programmer - Parallel):**
- Phase 2: EndpointGraphWriter (1 writer)
- Phase 3: Update core use-cases (3 files)
- Phase 4: Performance benchmarks (throughput validation)
- Estimated time: 6-8 hours

### Blocking Dependencies

**Phase 1 blocks Phase 2:**
- All constraints must exist before writers can test MERGE operations
- Pydantic models must exist before writer type hints

**Phase 2 blocks Phase 3:**
- All writers must be implemented before integration
- Unit tests must pass before integration tests can run

**Phase 3 blocks Phase 4:**
- Integration work must be complete before end-to-end validation
- Core use-cases must be updated before full workflow tests

**No blocking within phases:**
- Phase 2 tasks are fully independent (no shared files)
- Phase 3 tasks touch different files (no merge conflicts)
- Phase 4 tasks are read-only (no code changes)

### Coordination Checkpoints

**Checkpoint 1: After Phase 1 Task 1.3**
- Verify: SHOW CONSTRAINTS returns 11 rows
- Verify: All Pydantic models importable
- Blocking: Do not start Phase 2 until verified

**Checkpoint 2: After Phase 2 Task 2.5**
- Verify: All 5 writers importable
- Verify: All unit tests passing (uv run pytest tests/packages/graph/writers -m "unit")
- Blocking: Do not start Phase 3 until verified

**Checkpoint 3: After Phase 3 Task 3.3**
- Verify: ingest_docker_compose.py passes smoke test
- Verify: No import errors in core use-cases
- Blocking: Do not start Phase 4 integration tests until verified

### Agent Communication Protocol

**Agents must report:**
- [START] Task X.Y started (timestamp)
- [UPDATE] Progress update every 30 minutes
- [BLOCKED] Dependency blocker encountered (await resolution)
- [COMPLETE] Task X.Y complete with test results
- [FAILED] Task X.Y failed with error details

**Example:**
```
[Agent 1] [START] Task 2.1 (DocumentGraphWriter) - 2025-10-28 14:00:00
[Agent 1] [UPDATE] DocumentGraphWriter implementation 60% (write_documents complete)
[Agent 1] [UPDATE] DocumentGraphWriter implementation 100% (write_mentions complete)
[Agent 1] [COMPLETE] Task 2.1 - 10 unit tests passing, 96% coverage
[Agent 1] [START] Task 2.2 (ContainerGraphWriter) - 2025-10-28 15:30:00
```

---

## Open Questions and Assumptions

### Assumptions (Documented)

1. **Single-user system:** Breaking changes acceptable (wipe and rebuild DB)
2. **No existing data:** All constraints can be applied without migration scripts
3. **TDD discipline enforced:** All agents follow red-green-refactor strictly
4. **Neo4j 5.23+:** Relationship property indexes available (used in research doc)
5. **Performance baseline:** SwagGraphWriter achieves ≥20k edges/min (verified)

### Resolved Questions

**Q1: Should we rename "Doc" label to "Document" for consistency?**
**A1:** NO - Keep "Doc" label as-is. Breaking change with no functional benefit. Pydantic model named "Document" maps to Neo4j label "Doc".

**Q2: Endpoint schema inconsistency - which is correct?**
**A2:** Use constraint file schema (service, method, path). GRAPH_SCHEMA.md alternate schema (scheme, fqdn, port, path) is documentation bug. File issue for future alignment (out of scope).

**Q3: Should we implement all 7 missing constraints or prioritize subset?**
**A3:** Implement all 7. Partial constraints lead to data quality issues. Infrastructure graphs require complete referential integrity.

**Q4: Should we create 5 new writers or consolidate into generic writer?**
**A4:** Create 5 specialized writers. Follows established SwagGraphWriter pattern. Generic writer adds complexity without benefit.

**Q5: What's optimal agent allocation for parallel work?**
**A5:** 3 parallel programmer agents (distribution: 2+2+1 writers). Balanced workload, no agent idle time.

### Open Questions (Need User Input)

**Q6: Should DocumentGraphWriter.write_mentions() support wildcard target_labels?**
- Current design requires exact label match (Service, Host, etc.)
- Alternative: Support "Any" label with dynamic MATCH?
- **Decision needed:** Whitelist validation or wildcard support?

**Q7: Should core use-cases directly import graph writers (adapter layer)?**
- Current architecture: apps → adapters → core (strict dependency flow)
- Alternative: Create GraphWriterPort interface in core, inject writer as dependency
- **Decision needed:** Violate layering for simplicity or add port abstraction?

**Q8: Should we add relationship property validation in writers?**
- Current design: Writers trust input dictionaries (no validation)
- Alternative: Create Pydantic models for relationships (e.g., DependsOnRelationship)
- **Decision needed:** Trust callers or add validation layer?

**Q9: Should performance tests run in CI/CD or manual only?**
- Current design: Mark as "slow", optional in CI
- Alternative: Run in CI with relaxed thresholds (e.g., ≥15k edges/min instead of 20k)
- **Decision needed:** CI enforcement or manual validation?

**Q10: Should we add bulk delete operations to writers?**
- Current design: Writers only handle CREATE/MERGE (no DELETE)
- Alternative: Add delete_documents(), delete_containers(), etc. methods
- **Decision needed:** Scope creep or future enhancement?

---

## Next Steps After Plan Approval

1. **Create feature branch:**
   ```bash
   git checkout -b feat/neo4j-constraints-and-writers
   ```

2. **Execute Phase 1 (Sequential):**
   ```bash
   # Programmer agent handles foundation work
   # Estimated time: 2 hours
   ```

3. **Spawn Phase 2 agents (Parallel):**
   ```bash
   # Launch 3 parallel programmer agents
   # Agent 1: DocumentGraphWriter + ContainerGraphWriter
   # Agent 2: DockerComposeGraphWriter + HostGraphWriter
   # Agent 3: EndpointGraphWriter
   # Estimated time: 8-10 hours
   ```

4. **Verify Checkpoint 2:**
   ```bash
   uv run pytest tests/packages/graph/writers -m "unit" -v
   # Target: All tests passing, ≥95% coverage
   ```

5. **Execute Phase 3 (Parallel):**
   ```bash
   # Launch 3 parallel programmer agents for integration
   # Estimated time: 4-6 hours
   ```

6. **Execute Phase 4 (Parallel):**
   ```bash
   # Launch 3 parallel programmer agents for testing
   # Estimated time: 2-4 hours
   ```

7. **Final validation:**
   ```bash
   # Run full test suite
   uv run pytest tests/packages/graph/writers -v

   # Verify constraints
   uv run apps/cli init
   uv run apps/cli graph query "SHOW CONSTRAINTS"

   # Performance validation
   uv run pytest tests/packages/graph/writers/performance -m "performance" -v
   ```

8. **Create PR:**
   ```bash
   git add .
   git commit -m "feat(graph): add missing constraints and implement 5 graph writers"
   git push origin feat/neo4j-constraints-and-writers
   # Create PR with test results and performance benchmarks
   ```

---

## Summary

This plan provides a complete roadmap for updating Neo4j constraints and implementing missing graph writers in the Taboot RAG platform. Key highlights:

- **Complete schema coverage:** All 11 entity constraints implemented
- **Proven pattern:** Follow SwagGraphWriter template (battle-tested, ≥20k edges/min)
- **Strict TDD:** Red-green-refactor enforced for all tasks
- **Parallel execution:** 3 agents, 16-20 hours estimated effort
- **Zero breaking changes:** Additive only (except DB wipe acceptable)
- **Comprehensive testing:** Unit (95% coverage) + Integration + Performance
- **Clear success metrics:** Functional + Performance + Documentation quality

**Ready for approval and execution.**
