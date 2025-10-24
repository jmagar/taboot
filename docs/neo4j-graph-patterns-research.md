# Neo4j Graph Modeling Patterns & Cypher Best Practices
## Infrastructure Knowledge Graph Research Report

**Context:** Taboot v2 Doc-to-Graph RAG Platform
**Target Performance:** ≥20k edges/min with 2k UNWIND batches
**Hardware:** 16GB RAM + SSD
**Date:** 2025-10-20

---

## 1. Schema Design: Constraints, Indexes & Composite Keys

### Decision: Use Key Constraints + Composite Indexes

**Recommended Pattern:**
- **Unique constraints** on single-property identifiers (Service.name, Host.hostname, IP.addr)
- **Key constraints** on composite identifiers (Endpoint: service+method+path)
- **Range indexes** on frequently queried properties (timestamps, source metadata)
- **Relationship property indexes** on ROUTES_TO, BINDS properties (port, protocol)

### Rationale
- Key constraints enforce **both existence and uniqueness**, preventing null identifiers
- Constraints automatically create backing indexes (no need for separate CREATE INDEX)
- Composite indexes enable efficient lookups on multi-property patterns common in infrastructure graphs
- Relationship indexes (Neo4j 4.3+) significantly improve edge property filtering

### Cypher Examples

```cypher
-- Single-property unique constraints (nodes)
CREATE CONSTRAINT service_name_unique IF NOT EXISTS
FOR (s:Service) REQUIRE s.name IS UNIQUE;

CREATE CONSTRAINT host_hostname_unique IF NOT EXISTS
FOR (h:Host) REQUIRE h.hostname IS UNIQUE;

CREATE CONSTRAINT ip_addr_unique IF NOT EXISTS
FOR (i:IP) REQUIRE i.addr IS UNIQUE;

-- Key constraint (existence + uniqueness) for composite identifier
CREATE CONSTRAINT endpoint_key IF NOT EXISTS
FOR (e:Endpoint) REQUIRE (e.service, e.method, e.path) IS NODE KEY;

-- Composite index for fast lookups (when uniqueness not required)
CREATE INDEX endpoint_composite IF NOT EXISTS
FOR (e:Endpoint) ON (e.service, e.method, e.path);

-- Range index for timestamp filtering
CREATE INDEX doc_timestamp IF NOT EXISTS
FOR (d:Doc) ON (d.ingested_at);

-- Relationship property indexes (Neo4j 4.3+)
CREATE INDEX routes_to_host IF NOT EXISTS
FOR ()-[r:ROUTES_TO]-() ON (r.host);

CREATE INDEX binds_port IF NOT EXISTS
FOR ()-[r:BINDS]-() ON (r.port, r.protocol);
```

### Performance Notes
- **Index-backed constraints** enable O(log n) lookups vs O(n) full scans
- Composite indexes only help when **all properties** are filtered (service AND method AND path)
- Property order matters: put equality checks first, then range checks
- Relationship indexes showed **4x throughput improvement** (2571ms → 744ms in benchmarks)

### Pitfalls
- **Don't over-index**: Each index adds write overhead (~10-15% per index)
- Composite index with 3+ properties: query must filter on **all** to use index
- Key constraints prevent null values: ensure extractors populate all key fields
- Constraint violations throw `Neo.ClientError.Schema.ConstraintValidationFailed` (not retriable)

---

## 2. UNWIND Patterns: Bulk Insert/Merge with Batching

### Decision: UNWIND with MERGE-on-ID, ON CREATE for properties

**Recommended Pattern:**
```cypher
UNWIND $batch as row
MERGE (n:Label {id: row.id})
ON CREATE SET n += row.properties, n.created_at = timestamp()
ON MATCH SET n += row.properties, n.updated_at = timestamp()
```

### Rationale
- **MERGE only on unique identifier** (not all properties) prevents false negatives
- `ON CREATE` vs `ON MATCH` enables differential property updates
- UNWIND processes entire batch in single transaction (reduces overhead)
- Idempotent: re-running same batch is safe (critical for multi-source enrichment)

### Cypher Examples

**Nodes (Services, Hosts, IPs):**
```cypher
-- Services from Docker Compose + docs
UNWIND $batch as row
MERGE (s:Service {name: row.name})
ON CREATE SET
  s += row.properties,
  s.first_seen_at = timestamp(),
  s.sources = [row.source]
ON MATCH SET
  s += row.properties,
  s.updated_at = timestamp(),
  s.sources = CASE
    WHEN row.source IN s.sources THEN s.sources
    ELSE s.sources + row.source
  END
RETURN count(s) as services_merged;

-- Hosts with IPs
UNWIND $batch as row
MERGE (h:Host {hostname: row.hostname})
ON CREATE SET h += row.properties
WITH h, row
UNWIND row.ip_addresses as ip_addr
MERGE (i:IP {addr: ip_addr})
MERGE (h)-[:HAS_IP]->(i);
```

**Relationships (DEPENDS_ON, ROUTES_TO):**
```cypher
-- IMPORTANT: MATCH nodes first, then MERGE relationship
UNWIND $batch as row
MATCH (from:Service {name: row.from_service})
MATCH (to:Service {name: row.to_service})
MERGE (from)-[r:DEPENDS_ON]->(to)
ON CREATE SET r += row.properties
RETURN count(r) as dependencies_created;

-- ROUTES_TO with properties
UNWIND $batch as row
MATCH (proxy:Proxy {name: row.proxy_name})
MATCH (svc:Service {name: row.service_name})
MERGE (proxy)-[r:ROUTES_TO]->(svc)
ON CREATE SET
  r.host = row.host,
  r.path = row.path,
  r.tls = row.tls
ON MATCH SET
  r.host = row.host,
  r.path = row.path,
  r.tls = row.tls;
```

**Multi-source enrichment (Docker Compose → Docs → SWAG):**
```cypher
-- First pass: Docker Compose (structure)
UNWIND $docker_batch as row
MERGE (s:Service {name: row.name})
ON CREATE SET
  s.image = row.image,
  s.source = "docker-compose"
ON MATCH SET
  s.image = coalesce(row.image, s.image);

-- Second pass: Docs (descriptions)
UNWIND $docs_batch as row
MERGE (s:Service {name: row.name})
ON MATCH SET
  s.description = row.description,
  s.source = s.source + ",docs";

-- Third pass: SWAG (routing)
UNWIND $swag_batch as row
MERGE (s:Service {name: row.service})
MERGE (p:Proxy {name: "swag"})
MERGE (p)-[r:ROUTES_TO]->(s)
ON CREATE SET r += row.routing_config;
```

### Performance Notes
- **Batch size: 2,000-10,000 rows** for 16GB RAM systems
- Larger batches (50k) work if properties are small (<1KB per row)
- Each UNWIND+MERGE transaction is atomic (all-or-nothing)
- For 20k edges/min target: 10 batches/min × 2k rows = achievable

### Pitfalls
- **Never MERGE long patterns** (creates duplicates if partial match exists)
- Always `MATCH` nodes first, then `MERGE` relationships separately
- `MERGE (a)-[r:REL]->(b)` without MATCH on `a`, `b` → duplicate nodes
- Property maps with null values: use `coalesce()` or filter before UNWIND
- Constraint violations abort entire batch → use smaller batches or handle duplicates client-side

---

## 3. Idempotent Operations: MERGE vs CREATE, Property Updates

### Decision: MERGE for idempotence, CREATE for known-new data

**Recommended Pattern:**
- **MERGE** for infrastructure nodes (Services, Hosts discovered from multiple sources)
- **CREATE** for time-series data (Docs, chunks, extraction events)
- **Last-write-wins** with `ON MATCH SET n += properties` for metadata updates

### Rationale
- MERGE checks existence before write (idempotent but slower)
- CREATE is 2-3x faster but throws errors on constraint violations
- Infrastructure graphs need idempotence: same Service discovered in Docker + docs + SWAG
- Docs/chunks are immutable: use CREATE with unique doc_id

### Cypher Examples

**Idempotent node creation (MERGE):**
```cypher
-- Service may exist from prior source
MERGE (s:Service {name: $service_name})
ON CREATE SET s += $properties
ON MATCH SET s += $properties  -- last-write-wins
RETURN s;
```

**Fast creation for known-new nodes (CREATE):**
```cypher
-- Doc ingestion: doc_id is unique (enforced by constraint)
UNWIND $batch as row
CREATE (d:Doc {doc_id: row.doc_id})
SET d += row.properties
RETURN count(d) as docs_created;
```

**Idempotent relationships (MATCH → MERGE pattern):**
```cypher
-- Prevent duplicate DEPENDS_ON edges
MATCH (from:Service {name: $from})
MATCH (to:Service {name: $to})
MERGE (from)-[r:DEPENDS_ON]->(to)
ON CREATE SET r.discovered_at = timestamp()
RETURN r;
```

**Last-write-wins property updates:**
```cypher
-- Update Service metadata from latest source
MERGE (s:Service {name: $name})
ON MATCH SET
  s += $new_properties,          -- overwrites existing
  s.updated_at = timestamp(),
  s.update_count = coalesce(s.update_count, 0) + 1;
```

**Conditional updates (first-write-wins for certain fields):**
```cypher
MERGE (s:Service {name: $name})
ON CREATE SET
  s += $properties,
  s.first_seen_at = timestamp()
ON MATCH SET
  s.description = coalesce(s.description, $properties.description),  -- keep first
  s.version = $properties.version,  -- always update
  s.updated_at = timestamp();
```

### Performance Notes
- **MERGE**: ~500-1000 ops/sec (with index lookup)
- **CREATE**: ~2000-3000 ops/sec (no existence check)
- MERGE on relationships: ensure relationship type is indexed if filtering on properties
- Use MERGE for ≤10k ops, consider CREATE + client-side deduplication for >100k ops

### Pitfalls
- **MERGE without constraints** → full graph scan (catastrophically slow)
- `MERGE (n:Service)` (no properties) → matches ANY Service node
- **Concurrent MERGE** can create duplicates (use constraints to prevent)
- `ON MATCH SET n = $props` (assignment) replaces ALL properties; use `+=` (merge)
- `MERGE (a)-[r]->(b)` creates both nodes if missing; MATCH first if nodes should exist

---

## 4. Performance: Index Selection, Query Optimization, Traversal

### Decision: Index hints + relationship direction + traversal limits

**Recommended Pattern:**
- Rely on query planner (mature since Neo4j 4.x)
- Use `USING INDEX` hints only when planner picks wrong index
- Specify relationship direction explicitly (`-[:REL]->` vs `-[:REL]-`)
- Limit traversals with `[:REL*1..2]` (max 2 hops for infrastructure graphs)

### Rationale
- Modern planner chooses optimal index 95%+ of queries
- Index hints override planner (useful for skewed data distributions)
- Relationship direction reduces search space (50% fewer candidates)
- Infrastructure graphs rarely need >2-hop traversals (immediate dependencies)

### Cypher Examples

**Leveraging indexes (automatic):**
```cypher
-- Planner automatically uses service_name_unique constraint index
MATCH (s:Service {name: "taboot-api"})
RETURN s;

-- Composite index on Endpoint(service, method, path)
MATCH (e:Endpoint {service: "api", method: "GET", path: "/health"})
RETURN e;
```

**Index hints (when planner needs guidance):**
```cypher
-- Force use of hostname index (if planner picks wrong index)
MATCH (h:Host)
USING INDEX h:Host(hostname)
WHERE h.hostname STARTS WITH "prod-"
RETURN h;

-- Multiple index hints (requires join later)
MATCH (s:Service), (h:Host)
USING INDEX s:Service(name)
USING INDEX h:Host(hostname)
WHERE s.name = "api" AND h.hostname = "prod-01"
MATCH (s)-[:RUNS]->(h)
RETURN s, h;
```

**Relationship direction optimization:**
```cypher
-- Bad: bidirectional search (checks both directions)
MATCH (s:Service {name: "api"})-[:DEPENDS_ON]-(dep)
RETURN dep;

-- Good: directed search (50% fewer checks)
MATCH (s:Service {name: "api"})-[:DEPENDS_ON]->(dep)
RETURN dep;

-- Reverse direction if needed
MATCH (s:Service {name: "api"})<-[:DEPENDS_ON]-(dependent)
RETURN dependent;
```

**Limited traversal (infrastructure dependencies):**
```cypher
-- Direct dependencies (1 hop)
MATCH (s:Service {name: "api"})-[:DEPENDS_ON]->(dep)
RETURN dep;

-- Transitive dependencies (up to 2 hops)
MATCH (s:Service {name: "api"})-[:DEPENDS_ON*1..2]->(dep)
RETURN DISTINCT dep;

-- With path details
MATCH path = (s:Service {name: "api"})-[:DEPENDS_ON*1..2]->(dep)
RETURN dep.name, length(path) as hops
ORDER BY hops, dep.name;
```

**Query optimization checklist:**
```cypher
-- 1. Start with indexed property (Service.name has unique constraint)
MATCH (s:Service {name: $name})

-- 2. Use directed relationships
MATCH (s)-[:ROUTES_TO]->(target)

-- 3. Filter early (before traversal)
WHERE s.enabled = true

-- 4. Limit traversal depth
MATCH (s)-[:DEPENDS_ON*1..2]->(dep)

-- 5. Use DISTINCT to avoid duplicates
RETURN DISTINCT dep.name

-- 6. Limit result size
LIMIT 100;
```

**Relationship property filtering with indexes:**
```cypher
-- Create index first (see Section 1)
-- CREATE INDEX binds_port FOR ()-[r:BINDS]-() ON (r.port);

-- Query uses relationship index automatically
MATCH (s:Service)-[b:BINDS]->(h:Host)
WHERE b.port = 443 AND b.protocol = "tcp"
RETURN s, h;
```

### Performance Notes
- **Index lookups:** O(log n) for B-tree indexes
- **Relationship traversal:** O(d) where d = average degree (10-100 for infrastructure nodes)
- **Variable-length paths:** O(b^d) where b = branching factor, d = max depth
- **DISTINCT:** Adds hash-join overhead; avoid if possible
- Composite indexes: 2x faster than multiple single-property lookups

### Pitfalls
- **Missing indexes**: Query scans all nodes → O(n) instead of O(log n)
- **Bidirectional relationships** without direction: doubles search space
- **Long variable-length paths** (`[:REL*]` without limit): exponential blowup
- **Cartesian products**: Multiple MATCH without connecting them → n×m results
- **Index hints on non-existent indexes**: Query fails with "could not solve hints"

---

## 5. APOC Usage: Batch Operations, Meta-data, Algorithms

### Decision: Use `apoc.periodic.iterate` for bulk updates, avoid for writes

**Recommended Pattern:**
- **Native UNWIND** for bulk inserts/merges (faster, no APOC dependency)
- **apoc.periodic.iterate** for bulk updates/refactoring (when UNWIND insufficient)
- **apoc.meta.*** for schema inspection and documentation generation
- Avoid APOC for production write paths (not tracked by memory manager)

### Rationale
- Native UNWIND is faster and safer than APOC for 90% of batch operations
- apoc.periodic.iterate enables parallel updates (good for CPU-bound ops)
- APOC procedures bypass memory tracking → can OOM server
- Infrastructure graphs need deterministic writes → native Cypher preferred

### Cypher Examples

**Bulk updates with apoc.periodic.iterate:**
```cypher
-- Update all Service nodes in batches (CPU-bound operation)
CALL apoc.periodic.iterate(
  "MATCH (s:Service) RETURN s",
  "SET s.updated_at = timestamp(), s.checked = true",
  {batchSize: 10000, parallel: true}
) YIELD batches, total
RETURN batches, total;

-- Refactor: add labels based on properties
CALL apoc.periodic.iterate(
  "MATCH (s:Service) WHERE s.type = 'database' RETURN s",
  "SET s:Database",
  {batchSize: 5000, parallel: true}
);
```

**When to use UNWIND instead (most cases):**
```cypher
-- Prefer this over apoc.periodic.iterate for bulk inserts
UNWIND $batch as row
MERGE (s:Service {name: row.name})
ON CREATE SET s += row.properties
RETURN count(s);
```

**Schema inspection (apoc.meta):**
```cypher
-- View all node labels and counts
CALL apoc.meta.stats() YIELD labels
RETURN labels;

-- View all relationship types
CALL apoc.meta.relTypeProperties() YIELD relType, propertyName, propertyTypes
RETURN relType, collect(propertyName) as properties;

-- Generate graph schema visualization
CALL apoc.meta.graph() YIELD nodes, relationships
RETURN nodes, relationships;
```

**Batch operations configuration:**
```cypher
-- Sequential batches (safer, predictable memory)
CALL apoc.periodic.iterate(
  "MATCH (d:Doc) RETURN d",
  "MATCH (d)-[:MENTIONS]->(s:Service) SET d.service_count = count(s)",
  {batchSize: 2000, parallel: false, iterateList: true}
);

-- Parallel batches (faster, higher memory usage)
CALL apoc.periodic.iterate(
  "MATCH (s:Service) WHERE NOT s.checked RETURN s",
  "SET s:Actor, s.checked = true",
  {batchSize: 10000, parallel: true, concurrency: 4}
);
```

### Performance Notes
- **apoc.periodic.iterate**: Processes 10k-50k nodes/sec (depends on operation)
- **parallel:true**: Can use all CPU cores (good for label/property updates)
- **parallel:false**: Sequential processing (safer for relationship creation)
- APOC not detected by memory tracker → monitor heap manually
- Native UNWIND typically 20-30% faster than APOC for bulk inserts

### Pitfalls
- **APOC + parallel + relationships** → deadlocks (use parallel:false)
- **No memory limits**: APOC procedures can OOM server
- **Not included in Neo4j core**: Requires separate installation (included in Docker image)
- **Versioning**: APOC version must match Neo4j version exactly
- **Error handling**: APOC errors don't auto-retry like native transactions

---

## 6. Python Driver: Connection Pooling, Transactions, Error Handling

### Decision: Managed transactions + connection pool tuning + retry strategies

**Recommended Pattern:**
```python
from neo4j import GraphDatabase, exceptions
import time

class Neo4jWriter:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
            max_connection_pool_size=50,  # 2-3x worker threads
            connection_acquisition_timeout=60.0,
            max_transaction_retry_time=30.0,
            connection_timeout=30.0,
        )

    def close(self):
        self.driver.close()

    def write_batch(self, batch: list[dict]) -> int:
        """Execute write with automatic retries."""
        with self.driver.session(database="neo4j") as session:
            result = session.execute_write(
                self._write_tx, batch
            )
            return result

    @staticmethod
    def _write_tx(tx, batch: list[dict]) -> int:
        """Transaction function (auto-retried on transient failures)."""
        query = """
        UNWIND $batch as row
        MERGE (s:Service {name: row.name})
        ON CREATE SET s += row.properties
        RETURN count(s) as count
        """
        result = tx.run(query, batch=batch)
        return result.single()["count"]

    def write_with_retry(self, batch: list[dict], max_retries: int = 3) -> int:
        """Handle constraint violations with custom retry logic."""
        for attempt in range(max_retries):
            try:
                return self.write_batch(batch)
            except exceptions.ConstraintError as e:
                if "ConstraintValidationFailed" in str(e):
                    # Constraint violation: filter duplicates and retry
                    batch = self._filter_duplicates(batch, e)
                    if not batch:
                        return 0
                else:
                    raise
            except exceptions.TransientError as e:
                # Transient failure: exponential backoff
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise
        return 0
```

### Rationale
- **Managed transactions** (`execute_write`) provide automatic retries on transient failures
- Connection pooling reduces overhead (connections are expensive to create)
- Pool size = 2-3x concurrent workers (balance between throughput and memory)
- Explicit database name avoids extra round-trip to determine default database

### Python Driver Examples

**Connection pool configuration:**
```python
# High-throughput configuration (20k edges/min)
driver = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "password"),
    max_connection_pool_size=50,       # 2-3x worker count
    connection_acquisition_timeout=60.0,  # Wait up to 60s for connection
    max_transaction_retry_time=30.0,   # Retry transient failures for 30s
    connection_timeout=30.0,            # TCP connection timeout
    fetch_size=1000,                    # Stream results in batches
)
```

**Managed transactions (recommended):**
```python
def create_service_dependencies(driver, dependencies: list[dict]):
    with driver.session(database="neo4j") as session:
        # execute_write automatically retries on transient failures
        result = session.execute_write(
            _create_dependencies_tx, dependencies
        )
        return result

def _create_dependencies_tx(tx, dependencies: list[dict]):
    query = """
    UNWIND $batch as row
    MATCH (from:Service {name: row.from})
    MATCH (to:Service {name: row.to})
    MERGE (from)-[r:DEPENDS_ON]->(to)
    RETURN count(r) as count
    """
    result = tx.run(query, batch=dependencies)
    return result.single()["count"]
```

**Auto-commit transactions (highest throughput, no retries):**
```python
# Use for fire-and-forget writes where occasional failures acceptable
with driver.session(database="neo4j") as session:
    for batch in batches:
        # No automatic retries, no transaction overhead
        session.run("""
            UNWIND $batch as row
            CREATE (d:Doc {doc_id: row.doc_id})
            SET d += row.properties
        """, batch=batch)
```

**Error handling:**
```python
from neo4j.exceptions import (
    ConstraintError,
    TransientError,
    ServiceUnavailable,
    Neo4jError,
)

def safe_write(driver, query: str, params: dict):
    try:
        with driver.session(database="neo4j") as session:
            result = session.execute_write(
                lambda tx: tx.run(query, **params).consume()
            )
            return result
    except ConstraintError as e:
        # Constraint violation (not retriable)
        if "ConstraintValidationFailed" in e.message:
            logger.error(f"Duplicate key: {params}")
            raise
    except TransientError as e:
        # Transient failure (retriable by driver)
        logger.warning(f"Transient error, retrying: {e}")
        raise  # Driver will retry automatically
    except ServiceUnavailable as e:
        # Server down (not retriable)
        logger.error(f"Neo4j unavailable: {e}")
        raise
    except Neo4jError as e:
        # Other Neo4j errors
        logger.error(f"Neo4j error {e.code}: {e.message}")
        raise
```

**Concurrent writes with connection pooling:**
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def parallel_writes(driver, batches: list[list[dict]], workers: int = 10):
    """Write batches in parallel using connection pool."""
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(write_batch, driver, batch): i
            for i, batch in enumerate(batches)
        }

        results = []
        for future in as_completed(futures):
            batch_idx = futures[future]
            try:
                count = future.result()
                results.append((batch_idx, count))
            except Exception as e:
                logger.error(f"Batch {batch_idx} failed: {e}")
                results.append((batch_idx, 0))

        return results

def write_batch(driver, batch: list[dict]) -> int:
    with driver.session(database="neo4j") as session:
        result = session.execute_write(
            lambda tx: tx.run("""
                UNWIND $batch as row
                MERGE (s:Service {name: row.name})
                ON CREATE SET s += row.properties
                RETURN count(s) as count
            """, batch=batch).single()["count"]
        )
        return result
```

### Performance Notes
- **execute_write**: Manages transactions + automatic retries (~500-1000 ops/sec per connection)
- **Auto-commit** (session.run): No retries, higher throughput (~1500-2000 ops/sec)
- Connection pool overhead: ~50ms to acquire connection (amortized over batch)
- For 20k edges/min: 10 workers × 2k batch × 10 batches/min = achievable

### Pitfalls
- **Pool exhaustion**: Too few connections → timeouts; too many → memory waste
- **Constraint violations** are not retriable: handle client-side
- **Explicit transactions** (`session.begin_transaction()`) require manual commit/rollback
- **Not specifying database**: Extra round-trip to determine default database
- **Closed sessions**: Session is closed at end of `with` block; don't reuse sessions across threads

---

## 7. Specific Recommendations for Taboot v2

### Infrastructure Graph Schema

**Constraints (create at startup):**
```cypher
-- Node constraints
CREATE CONSTRAINT service_name IF NOT EXISTS
FOR (s:Service) REQUIRE s.name IS UNIQUE;

CREATE CONSTRAINT host_hostname IF NOT EXISTS
FOR (h:Host) REQUIRE h.hostname IS UNIQUE;

CREATE CONSTRAINT ip_addr IF NOT EXISTS
FOR (i:IP) REQUIRE i.addr IS UNIQUE;

CREATE CONSTRAINT proxy_name IF NOT EXISTS
FOR (p:Proxy) REQUIRE p.name IS UNIQUE;

CREATE CONSTRAINT doc_id IF NOT EXISTS
FOR (d:Doc) REQUIRE d.doc_id IS UNIQUE;

CREATE CONSTRAINT endpoint_key IF NOT EXISTS
FOR (e:Endpoint) REQUIRE (e.service, e.method, e.path) IS NODE KEY;
```

**Indexes (after constraints):**
```cypher
-- Composite indexes
CREATE INDEX endpoint_lookup IF NOT EXISTS
FOR (e:Endpoint) ON (e.service, e.method, e.path);

-- Range indexes (timestamps, metadata)
CREATE INDEX doc_ingested IF NOT EXISTS
FOR (d:Doc) ON (d.ingested_at);

CREATE INDEX doc_source IF NOT EXISTS
FOR (d:Doc) ON (d.source);

-- Relationship property indexes
CREATE INDEX routes_to_props IF NOT EXISTS
FOR ()-[r:ROUTES_TO]-() ON (r.host, r.path);

CREATE INDEX binds_props IF NOT EXISTS
FOR ()-[r:BINDS]-() ON (r.port, r.protocol);

CREATE INDEX mentions_props IF NOT EXISTS
FOR ()-[r:MENTIONS]-() ON (r.span, r.section);
```

### Bulk Write Strategy (Python Driver)

**neo4j_writer.py:**
```python
from typing import Any
from neo4j import GraphDatabase, Session, Transaction, exceptions
import logging

logger = logging.getLogger(__name__)

class Neo4jBulkWriter:
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        batch_size: int = 2000,
        max_pool_size: int = 50,
    ):
        self.driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
            max_connection_pool_size=max_pool_size,
            connection_acquisition_timeout=60.0,
            max_transaction_retry_time=30.0,
        )
        self.batch_size = batch_size

    def close(self):
        self.driver.close()

    def write_services(self, services: list[dict[str, Any]]) -> int:
        """Idempotent service writes with source tracking."""
        batches = self._chunk_list(services, self.batch_size)
        total = 0

        for batch in batches:
            with self.driver.session(database="neo4j") as session:
                count = session.execute_write(self._write_services_tx, batch)
                total += count

        return total

    @staticmethod
    def _write_services_tx(tx: Transaction, batch: list[dict]) -> int:
        query = """
        UNWIND $batch as row
        MERGE (s:Service {name: row.name})
        ON CREATE SET
          s += row.properties,
          s.first_seen_at = timestamp(),
          s.sources = [row.source]
        ON MATCH SET
          s += row.properties,
          s.updated_at = timestamp(),
          s.sources = CASE
            WHEN row.source IN s.sources THEN s.sources
            ELSE s.sources + row.source
          END
        RETURN count(s) as count
        """
        result = tx.run(query, batch=batch)
        return result.single()["count"]

    def write_dependencies(self, edges: list[dict[str, Any]]) -> int:
        """Idempotent dependency edges (MATCH → MERGE pattern)."""
        batches = self._chunk_list(edges, self.batch_size)
        total = 0

        for batch in batches:
            with self.driver.session(database="neo4j") as session:
                count = session.execute_write(self._write_dependencies_tx, batch)
                total += count

        return total

    @staticmethod
    def _write_dependencies_tx(tx: Transaction, batch: list[dict]) -> int:
        query = """
        UNWIND $batch as row
        MATCH (from:Service {name: row.from_service})
        MATCH (to:Service {name: row.to_service})
        MERGE (from)-[r:DEPENDS_ON]->(to)
        ON CREATE SET r += row.properties
        ON MATCH SET r += row.properties
        RETURN count(r) as count
        """
        result = tx.run(query, batch=batch)
        return result.single()["count"]

    @staticmethod
    def _chunk_list(items: list, size: int) -> list[list]:
        """Split list into chunks of specified size."""
        return [items[i:i + size] for i in range(0, len(items), size)]
```

### Multi-Source Enrichment Pattern

**Deterministic extraction workflow:**
```python
# Stage 1: Docker Compose (structure)
docker_services = extract_docker_compose("docker-compose.yaml")
writer.write_services([
    {"name": svc.name, "source": "docker-compose", "properties": svc.to_dict()}
    for svc in docker_services
])

# Stage 2: Docs (descriptions + endpoints)
doc_services = extract_from_docs(qdrant_client, "service documentation")
writer.write_services([
    {"name": svc.name, "source": "docs", "properties": svc.to_dict()}
    for svc in doc_services
])

# Stage 3: SWAG (routing)
swag_routes = extract_swag_config("/config/nginx/proxy-confs/*.conf")
for route in swag_routes:
    writer.write_dependencies([{
        "from_service": "swag",
        "to_service": route.target_service,
        "properties": {"host": route.host, "path": route.path, "tls": True}
    }])
```

### Performance Validation Query

```cypher
// Measure write throughput
PROFILE
UNWIND range(1, 2000) as i
MERGE (s:Service {name: "test-" + i})
ON CREATE SET s.created_at = timestamp()
RETURN count(s);

// Check index usage
EXPLAIN
MATCH (s:Service {name: "taboot-api"})-[:DEPENDS_ON]->(dep)
RETURN dep;

// Measure traversal performance
PROFILE
MATCH (s:Service {name: "taboot-api"})-[:DEPENDS_ON*1..2]->(dep)
RETURN DISTINCT dep.name;
```

---

## 8. Common Pitfalls Summary

| Issue | Symptom | Solution |
|-------|---------|----------|
| **MERGE without constraints** | Slow queries, full graph scans | Create unique/key constraints on merge properties |
| **Long pattern MERGE** | Duplicate nodes/relationships | Split into separate MERGE statements, MATCH nodes first |
| **Concurrent MERGE** | Duplicate nodes despite constraints | Ensure constraints exist, use larger batch sizes |
| **Missing relationship direction** | 2x slower queries | Use `-[:REL]->` instead of `-[:REL]-` |
| **Variable-length paths without limit** | Exponential query time | Add `[:REL*1..2]` with reasonable max depth |
| **Constraint violations in batch** | Entire batch fails | Filter duplicates client-side or use smaller batches |
| **Pool exhaustion** | Connection timeouts | Increase `max_connection_pool_size` or reduce workers |
| **APOC parallel + relationships** | Deadlocks, failed writes | Use `parallel: false` for relationship creation |
| **Composite index partial match** | Index not used | Query must filter on ALL indexed properties |
| **Null property values** | Constraint violations, unexpected behavior | Use `coalesce()` or filter nulls before write |

---

## 9. References & Further Reading

### Official Neo4j Documentation
- [Cypher Manual (Constraints)](https://neo4j.com/docs/cypher-manual/current/constraints/)
- [Cypher Manual (Indexes)](https://neo4j.com/docs/cypher-manual/current/indexes/)
- [Python Driver Manual](https://neo4j.com/docs/python-manual/current/)
- [APOC Documentation](https://neo4j.com/docs/apoc/current/)

### Key Blog Posts & Articles
- [5 Tips for Fast Batched Updates](https://medium.com/neo4j/5-tips-tricks-for-fast-batched-updates-of-graph-structures-with-neo4j-and-cypher-73c7f693c8cc)
- [Understanding MERGE](https://neo4j.com/developer/kb/understanding-how-merge-works/)
- [Neo4j 4.3 Relationship Indexes](https://neo4j.com/blog/developer/neo4j-4-3-blog-series-relationship-indexes/)
- [Microservices with Neo4j](https://neo4j.com/blog/nodes/fixing-microservices-architecture-graphconnect/)

### Performance Benchmarks
- [Best Practices for Large Updates](https://neo4j.com/blog/nodes/nodes-2019-best-practices-to-make-large-updates-in-neo4j/)
- [Neo4j Performance Guide](https://neo4j-guide.com/neo4j-slow-write-performance/)

### Status Codes (Error Handling)
- [Neo4j Status Codes](https://neo4j.com/docs/status-codes/current/)

---

## 10. Quick Reference Card

### Essential Cypher Patterns

```cypher
-- Idempotent node creation (multi-source)
UNWIND $batch as row
MERGE (s:Service {name: row.name})
ON CREATE SET s += row.properties, s.sources = [row.source]
ON MATCH SET s += row.properties, s.sources = s.sources + row.source
RETURN count(s);

-- Idempotent relationship creation (MATCH first)
UNWIND $batch as row
MATCH (from:Service {name: row.from})
MATCH (to:Service {name: row.to})
MERGE (from)-[r:DEPENDS_ON]->(to)
ON CREATE SET r += row.properties
RETURN count(r);

-- Fast creation (known-new nodes)
UNWIND $batch as row
CREATE (d:Doc {doc_id: row.doc_id})
SET d += row.properties;

-- Limited traversal (infrastructure deps)
MATCH (s:Service {name: $name})-[:DEPENDS_ON*1..2]->(dep)
RETURN DISTINCT dep.name;
```

### Python Driver Template

```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "password"),
    max_connection_pool_size=50,
)

def write_batch(batch: list[dict]) -> int:
    with driver.session(database="neo4j") as session:
        return session.execute_write(
            lambda tx: tx.run("""
                UNWIND $batch as row
                MERGE (n:Node {id: row.id})
                ON CREATE SET n += row.properties
                RETURN count(n)
            """, batch=batch).single()[0]
        )
```

### Performance Checklist

- [ ] Unique/key constraints on merge properties
- [ ] Composite indexes on multi-property lookups
- [ ] Relationship property indexes for filtering
- [ ] Batch size 2k-10k rows (16GB RAM)
- [ ] MATCH nodes first, then MERGE relationships
- [ ] Specify relationship direction (`-[:REL]->`)
- [ ] Limit traversal depth (`[:REL*1..2]`)
- [ ] Connection pool = 2-3x worker count
- [ ] Use managed transactions (`execute_write`)
- [ ] Handle constraint violations separately

---

**End of Research Report**
