# Data Model: LlamaCrawl v2 — Doc-to-Graph RAG Platform

**Feature**: `001-llamacrawl-v2-rag-platform`
**Date**: 2025-10-20
**Status**: Phase 1 Design Complete

## Overview

This document defines all entities, relationships, state transitions, and validation rules for LlamaCrawl v2. The system uses a hybrid storage architecture:

- **Neo4j** — Property graph for entities and relationships (11 node types, 11 relationship types)
- **Qdrant** — Vector embeddings with rich metadata (1024-dim, 15 payload fields)
- **Redis** — State, cache, and DLQ (3 key patterns)
- **PostgreSQL** — Firecrawl job metadata (managed by Firecrawl service)

---

## Neo4j Graph Model

### Node Types (11 Total)

#### 1. Document
Represents an ingested source document (web page, config file, GitHub repo, etc.)

**Fields**:
- `docId: string` (PK, unique) — UUID v4 identifier
- `url: string` — Source URL or file path
- `title: string` — Document title or filename
- `sourceType: string` — Enum: `web|github|reddit|youtube|gmail|elasticsearch|compose|swag|tailscale|unifi|ai_session`
- `ingestedAt: datetime` — Timestamp of initial ingestion
- `updatedAt: datetime` — Last update timestamp
- `retentionPolicy: integer?` — Days before auto-deletion (null = permanent)
- `contentHash: string` — SHA-256 of normalized content
- `metadata: map` — Source-specific metadata (JSON blob)

**Constraints**:
```cypher
CREATE CONSTRAINT doc_docid FOR (d:Document) REQUIRE d.docId IS UNIQUE;
CREATE INDEX doc_url FOR (d:Document) ON (d.url);
CREATE INDEX doc_source FOR (d:Document) ON (d.sourceType);
```

**Validation Rules**:
- `docId` must be valid UUID v4
- `url` must be valid URL or absolute file path
- `sourceType` must be one of 11 supported types
- `ingestedAt` must be in the past
- `retentionPolicy` must be ≥1 if set

---

#### 2. Service
Infrastructure service (microservice, daemon, database, etc.)

**Fields**:
- `name: string` (PK, unique) — Service identifier (e.g., "nginx", "postgres")
- `version: string?` — Version string
- `protocol: string?` — Primary protocol (http, tcp, udp, etc.)
- `port: integer?` — Primary port number
- `description: string?` — Human-readable description
- `createdAt: datetime` — First extracted timestamp
- `updatedAt: datetime` — Last updated timestamp
- `schemaVersion: string` — Data model version (semver)

**Constraints**:
```cypher
CREATE CONSTRAINT service_name FOR (s:Service) REQUIRE s.name IS UNIQUE;
CREATE INDEX service_proto_port FOR (s:Service) ON (s.protocol, s.port);
```

**Validation Rules**:
- `name` must match `^[a-z0-9][a-z0-9_-]*$` (lowercase, alphanumeric with hyphens/underscores)
- `version` must match semver pattern if provided
- `port` must be 1-65535 if provided
- `protocol` must be lowercase alphanumeric

---

#### 3. Host
Physical or virtual machine

**Fields**:
- `hostname: string` (PK, unique) — Fully qualified domain name or bare hostname
- `ip: string?` — Primary IP address (may be updated)
- `osType: string?` — Operating system (linux, windows, darwin, etc.)
- `description: string?` — Human-readable description
- `createdAt: datetime` — First extracted timestamp
- `updatedAt: datetime` — Last updated timestamp

**Constraints**:
```cypher
CREATE CONSTRAINT host_hostname FOR (h:Host) REQUIRE h.hostname IS UNIQUE;
CREATE INDEX host_ip FOR (h:Host) ON (h.ip);
```

**Validation Rules**:
- `hostname` must be valid DNS hostname (RFC 1123)
- `ip` must be valid IPv4 or IPv6 address if provided
- `osType` must match `^[a-z0-9_]+$` if provided

---

#### 4. IP
Network IP address (distinct from Host to support multi-homed systems)

**Fields**:
- `addr: string` (PK, unique) — IP address (v4 or v6)
- `cidr: string?` — CIDR block if part of subnet
- `isPublic: boolean` — True if public IP, false if private/internal
- `createdAt: datetime` — First extracted timestamp
- `updatedAt: datetime` — Last updated timestamp

**Constraints**:
```cypher
CREATE CONSTRAINT ip_addr FOR (i:IP) REQUIRE i.addr IS UNIQUE;
```

**Validation Rules**:
- `addr` must be valid IPv4 or IPv6 address
- `cidr` must be valid CIDR notation if provided
- `isPublic` derived from IP ranges (RFC 1918 for private)

---

#### 5. ReverseProxy
HTTP/TCP reverse proxy or load balancer (Traefik, nginx, HAProxy, etc.)

**Fields**:
- `name: string` (PK, unique) — Proxy identifier
- `type: string` — Proxy type (traefik, nginx, haproxy, cloudflare, etc.)
- `version: string?` — Version string
- `configPath: string?` — Path to config file
- `createdAt: datetime` — First extracted timestamp
- `updatedAt: datetime` — Last updated timestamp

**Constraints**:
```cypher
CREATE CONSTRAINT proxy_name FOR (p:ReverseProxy) REQUIRE p.name IS UNIQUE;
```

**Validation Rules**:
- `name` must match `^[a-z0-9][a-z0-9_-]*$`
- `type` must be lowercase alphanumeric

---

#### 6. Endpoint
HTTP/RPC endpoint exposed by a service

**Fields**:
- `scheme: string` — Protocol scheme (http, https, grpc, ws, wss)
- `fqdn: string` — Fully qualified domain name
- `port: integer` — Port number
- `path: string` — URL path (e.g., "/api/v1/users")
- `method: string?` — HTTP method (GET, POST, etc.) or RPC method name
- `authRequired: boolean` — True if authentication required
- `createdAt: datetime` — First extracted timestamp
- `updatedAt: datetime` — Last updated timestamp

**Composite PK**: `(scheme, fqdn, port, path)`

**Constraints**:
```cypher
CREATE CONSTRAINT endpoint_uniq FOR (e:Endpoint)
  REQUIRE (e.scheme, e.fqdn, e.port, e.path) IS UNIQUE;
CREATE INDEX endpoint_fqdn FOR (e:Endpoint) ON (e.fqdn);
```

**Validation Rules**:
- `scheme` must be one of: http, https, grpc, grpc+tls, ws, wss
- `fqdn` must be valid hostname or IP
- `port` must be 1-65535
- `path` must start with `/`
- `method` must be uppercase if HTTP method

---

#### 7. Network
Network segment or VLAN

**Fields**:
- `cidr: string` (PK, unique) — CIDR notation (e.g., "10.0.0.0/24")
- `name: string?` — Human-readable name (e.g., "prod-vpc")
- `isPublic: boolean` — True if public subnet
- `description: string?` — Description
- `createdAt: datetime` — First extracted timestamp
- `updatedAt: datetime` — Last updated timestamp

**Constraints**:
```cypher
CREATE CONSTRAINT network_cidr FOR (n:Network) REQUIRE n.cidr IS UNIQUE;
```

**Validation Rules**:
- `cidr` must be valid CIDR notation
- `isPublic` derived from IP range (RFC 1918 for private)

---

#### 8. Container
Docker or Kubernetes container instance

**Fields**:
- `containerId: string` (PK, unique) — Container ID (short or long)
- `name: string` — Container name
- `image: string` — Image reference (e.g., "nginx:1.25")
- `composeProject: string?` — Docker Compose project name
- `composeService: string?` — Service name in compose file
- `createdAt: datetime` — First extracted timestamp
- `updatedAt: datetime` — Last updated timestamp

**Constraints**:
```cypher
CREATE CONSTRAINT container_id FOR (c:Container) REQUIRE c.containerId IS UNIQUE;
CREATE INDEX container_compose FOR (c:Container) ON (c.composeProject, c.composeService);
```

**Validation Rules**:
- `containerId` must be valid Docker container ID (12 or 64 hex chars)
- `image` must match `^[a-z0-9._/-]+:[a-z0-9._-]+$`

---

#### 9. Image
Container image (Docker, OCI)

**Fields**:
- `imageId: string` (PK, unique) — Image digest (sha256:...)
- `name: string` — Image name with tag (e.g., "nginx:1.25")
- `registry: string?` — Registry URL (e.g., "docker.io")
- `createdAt: datetime` — First extracted timestamp
- `updatedAt: datetime` — Last updated timestamp

**Constraints**:
```cypher
CREATE CONSTRAINT image_id FOR (i:Image) REQUIRE i.imageId IS UNIQUE;
```

**Validation Rules**:
- `imageId` must be valid image digest (sha256:...)
- `name` must match image reference pattern

---

#### 10. VPNTunnel
VPN or WireGuard tunnel

**Fields**:
- `tunnelId: string` (PK, unique) — Tunnel identifier
- `name: string` — Human-readable name
- `type: string` — Tunnel type (wireguard, openvpn, tailscale, etc.)
- `localEndpoint: string` — Local IP or CIDR
- `remoteEndpoint: string` — Remote IP or CIDR
- `createdAt: datetime` — First extracted timestamp
- `updatedAt: datetime` — Last updated timestamp

**Constraints**:
```cypher
CREATE CONSTRAINT vpn_id FOR (v:VPNTunnel) REQUIRE v.tunnelId IS UNIQUE;
```

**Validation Rules**:
- `tunnelId` must be non-empty string
- `localEndpoint` and `remoteEndpoint` must be valid IP/CIDR

---

#### 11. TailscaleNode
Tailscale mesh VPN node

**Fields**:
- `nodeId: string` (PK, unique) — Tailscale node ID
- `name: string` — Node name (hostname)
- `tailscaleIp: string` — Tailscale-assigned IP (100.x.y.z)
- `machineKey: string?` — Machine key (sensitive)
- `lastSeen: datetime?` — Last seen timestamp
- `createdAt: datetime` — First extracted timestamp
- `updatedAt: datetime` — Last updated timestamp

**Constraints**:
```cypher
CREATE CONSTRAINT tailscale_nodeid FOR (t:TailscaleNode) REQUIRE t.nodeId IS UNIQUE;
CREATE INDEX tailscale_ip FOR (t:TailscaleNode) ON (t.tailscaleIp);
```

**Validation Rules**:
- `nodeId` must be non-empty string
- `tailscaleIp` must be valid IPv4 in 100.64.0.0/10 range
- `machineKey` should be encrypted at rest (if stored)

---

### Relationship Types (11 Total)

#### 1. DEPENDS_ON
Service A depends on Service B (application-level dependency)

**Properties**:
- `docId: string` — Source document ID
- `confidence: float` — Extraction confidence (0.0-1.0)
- `source: string` — Extraction tier (tier_a, tier_b, tier_c)
- `extractionMethod: string` — Method identifier (regex, spacy_dep, llm_window)
- `since: datetime` — When dependency was first observed

**Pattern**:
```cypher
(s:Service)-[:DEPENDS_ON {docId, confidence, source, extractionMethod, since}]->(d:Service)
```

**Validation Rules**:
- `confidence` must be 0.0-1.0
- `source` must be one of: tier_a, tier_b, tier_c
- `since` must be in the past

---

#### 2. ROUTES_TO
ReverseProxy routes traffic to Service or Endpoint

**Properties**:
- `host: string?` — Host header match rule
- `path: string?` — Path prefix match rule
- `tls: boolean` — True if HTTPS/TLS enabled
- `docId: string` — Source document ID
- `confidence: float` — Extraction confidence
- `source: string` — Extraction tier
- `extractionMethod: string` — Method identifier
- `since: datetime` — First observed timestamp

**Pattern**:
```cypher
(p:ReverseProxy)-[:ROUTES_TO {host, path, tls, docId, confidence, source, extractionMethod, since}]->(s:Service|Endpoint)
```

**Validation Rules**:
- `host` must be valid hostname pattern (may include wildcards)
- `path` must start with `/` if provided
- `confidence` must be 0.0-1.0

---

#### 3. BINDS
Service binds to a port/protocol on a Host or IP

**Properties**:
- `port: integer` — Port number
- `protocol: string` — Protocol (tcp, udp, http, https, etc.)
- `docId: string` — Source document ID
- `confidence: float` — Extraction confidence
- `source: string` — Extraction tier
- `extractionMethod: string` — Method identifier
- `since: datetime` — First observed timestamp

**Pattern**:
```cypher
(s:Service)-[:BINDS {port, protocol, docId, confidence, source, extractionMethod, since}]->(h:Host|IP)
```

**Validation Rules**:
- `port` must be 1-65535
- `protocol` must be lowercase alphanumeric
- `confidence` must be 0.0-1.0

---

#### 4. RUNS
Container RUNS on Host

**Properties**:
- `restartPolicy: string?` — Docker restart policy (always, unless-stopped, etc.)
- `docId: string` — Source document ID
- `confidence: float` — Extraction confidence
- `source: string` — Extraction tier
- `since: datetime` — First observed timestamp

**Pattern**:
```cypher
(c:Container)-[:RUNS {restartPolicy, docId, confidence, source, since}]->(h:Host)
```

**Validation Rules**:
- `restartPolicy` must be one of: no, always, unless-stopped, on-failure
- `confidence` must be 0.0-1.0

---

#### 5. EXPOSES_ENDPOINT
Service exposes an Endpoint

**Properties**:
- `auth: string?` — Auth mechanism (bearer, basic, oauth2, apikey, none)
- `rateLimit: integer?` — Requests per minute
- `docId: string` — Source document ID
- `confidence: float` — Extraction confidence
- `source: string` — Extraction tier
- `extractionMethod: string` — Method identifier
- `since: datetime` — First observed timestamp

**Pattern**:
```cypher
(s:Service)-[:EXPOSES_ENDPOINT {auth, rateLimit, docId, confidence, source, extractionMethod, since}]->(e:Endpoint)
```

**Validation Rules**:
- `auth` must be one of: bearer, basic, oauth2, apikey, mtls, none
- `rateLimit` must be ≥1 if provided
- `confidence` must be 0.0-1.0

---

#### 6. CONNECTS_TO
Network connectivity relationship (Service to Service, Host to Network, etc.)

**Properties**:
- `protocol: string?` — Connection protocol
- `encrypted: boolean` — True if connection is encrypted
- `docId: string` — Source document ID
- `confidence: float` — Extraction confidence
- `source: string` — Extraction tier
- `since: datetime` — First observed timestamp

**Pattern**:
```cypher
(s:Service|Host)-[:CONNECTS_TO {protocol, encrypted, docId, confidence, source, since}]->(d:Service|Host|Network)
```

**Validation Rules**:
- `protocol` must be lowercase alphanumeric if provided
- `confidence` must be 0.0-1.0

---

#### 7. RESOLVES_TO
DNS resolution relationship (Host resolves to IP)

**Properties**:
- `recordType: string` — DNS record type (A, AAAA, CNAME, etc.)
- `ttl: integer?` — TTL in seconds
- `docId: string` — Source document ID
- `confidence: float` — Extraction confidence
- `source: string` — Extraction tier
- `since: datetime` — First observed timestamp

**Pattern**:
```cypher
(h:Host)-[:RESOLVES_TO {recordType, ttl, docId, confidence, source, since}]->(i:IP)
```

**Validation Rules**:
- `recordType` must be one of: A, AAAA, CNAME, MX, TXT, NS, PTR
- `ttl` must be ≥0 if provided
- `confidence` must be 0.0-1.0

---

#### 8. RUNS_IN
Container runs in a Network

**Properties**:
- `networkMode: string?` — Docker network mode (bridge, host, none, custom)
- `docId: string` — Source document ID
- `confidence: float` — Extraction confidence
- `source: string` — Extraction tier
- `since: datetime` — First observed timestamp

**Pattern**:
```cypher
(c:Container)-[:RUNS_IN {networkMode, docId, confidence, source, since}]->(n:Network)
```

**Validation Rules**:
- `networkMode` must be one of: bridge, host, none, overlay, macvlan, custom
- `confidence` must be 0.0-1.0

---

#### 9. BUILDS
Service builds from an Image

**Properties**:
- `buildArgs: map?` — Build arguments (JSON)
- `dockerfile: string?` — Path to Dockerfile
- `docId: string` — Source document ID
- `confidence: float` — Extraction confidence
- `source: string` — Extraction tier
- `since: datetime` — First observed timestamp

**Pattern**:
```cypher
(s:Service)-[:BUILDS {buildArgs, dockerfile, docId, confidence, source, since}]->(i:Image)
```

**Validation Rules**:
- `dockerfile` must be valid file path if provided
- `confidence` must be 0.0-1.0

---

#### 10. MENTIONS
Document MENTIONS a chunk (traceability relationship)

**Properties**:
- `section: string?` — Document section (e.g., "Services", "Configuration")
- `span: [integer, integer]?` — Character offsets [start, end] in document
- `chunkHash: string` — SHA-256 of chunk text
- `chunkIndex: integer` — Sequential chunk number within document

**Pattern**:
```cypher
(d:Document)-[:MENTIONS {section, span, chunkHash, chunkIndex}]->(embedding in Qdrant)
```

**Note**: This is a hybrid relationship. The Neo4j side stores metadata; the actual chunk text and embedding live in Qdrant. Use `chunkHash` or `chunkId` (derived as `${docId}:${chunkIndex}`) to look up in Qdrant.

**Validation Rules**:
- `span[0]` must be ≤ `span[1]` if provided
- `chunkHash` must be valid SHA-256 hex string (64 chars)
- `chunkIndex` must be ≥0

---

#### 11. USES_VPN
Service or Host uses a VPN tunnel

**Properties**:
- `docId: string` — Source document ID
- `confidence: float` — Extraction confidence
- `source: string` — Extraction tier
- `since: datetime` — First observed timestamp

**Pattern**:
```cypher
(s:Service|Host)-[:USES_VPN {docId, confidence, source, since}]->(v:VPNTunnel|TailscaleNode)
```

**Validation Rules**:
- `confidence` must be 0.0-1.0

---

## Qdrant Vector Model

### Collection: `taboot.documents`

**Vector Configuration**:
- **Dimensions**: 1024
- **Distance**: Cosine
- **HNSW Config**:
  - `m`: 32 (number of bi-directional links per element)
  - `ef_construct`: 128 (construction time trade-off)
  - `full_scan_threshold`: 10000 (below this count, use brute-force)
- **Shards**: 4
- **Replication**: 1 (single-node; increase for HA)

### Payload Schema (15 Fields)

#### Keyword Fields (10)

1. **doc_id** (`string`, indexed)
   - UUID v4 of source document
   - Maps to Neo4j `Document.docId`

2. **chunk_id** (`string`, indexed, unique within collection)
   - Format: `${doc_id}:${chunk_index}`
   - Used as Qdrant point ID

3. **namespace** (`string`, indexed)
   - Logical grouping (e.g., "prod-configs", "staging-docs")
   - Enables multi-tenant filtering

4. **url** (`string`, indexed)
   - Source URL or file path

5. **title** (`string`, indexed)
   - Document title

6. **source** (`string`, indexed)
   - Source type: `web|github|reddit|youtube|gmail|elasticsearch|compose|swag|tailscale|unifi|ai_session`

7. **job_id** (`string`, indexed)
   - Firecrawl job ID or ingestion batch ID

8. **sha256** (`string`, indexed)
   - SHA-256 of chunk text (enables deduplication)

9. **mime** (`string`, indexed)
   - MIME type (e.g., "text/markdown", "application/yaml")

10. **lang** (`string`, indexed)
    - Language code (ISO 639-1, e.g., "en", "es")

#### Numeric Fields (2)

11. **chunk_index** (`integer`, indexed)
    - Sequential chunk number within document (0-based)

12. **text_len** (`integer`)
    - Character count of chunk text

#### Datetime Fields (2)

13. **created_at** (`integer`, indexed)
    - Unix timestamp (seconds since epoch)

14. **updated_at** (`integer`, indexed)
    - Unix timestamp of last update

#### Array Fields (1)

15. **tags** (`string[]`, indexed)
    - Free-form tags for filtering (e.g., ["production", "database"])

### Deduplication Strategy

**Key**: `(sha256, namespace)` tuple

**Logic**:
```python
def upsert_chunk(
    chunk_id: str,
    embedding: List[float],
    payload: Dict[str, Any]
) -> None:
    """Idempotent upsert with deduplication."""
    existing = qdrant.scroll(
        collection_name="taboot.documents",
        scroll_filter=models.Filter(
            must=[
                models.FieldCondition(key="sha256", match=payload["sha256"]),
                models.FieldCondition(key="namespace", match=payload["namespace"])
            ]
        ),
        limit=1
    )

    if existing.points:
        # Update metadata only, preserve embedding
        qdrant.set_payload(
            collection_name="taboot.documents",
            payload={"updated_at": int(datetime.now().timestamp())},
            points=[existing.points[0].id]
        )
    else:
        # Insert new point
        qdrant.upsert(
            collection_name="taboot.documents",
            points=[models.PointStruct(
                id=chunk_id,
                vector=embedding,
                payload=payload
            )]
        )
```

---

## Redis State Model

### Key Patterns (3 Categories)

#### 1. Extraction Cache

**Pattern**: `extraction:{content_hash}`
- **Value**: JSON-serialized extraction result (triples list)
- **TTL**: 7 days
- **Purpose**: Cache Tier C LLM outputs by SHA-256 window hash

**Example**:
```python
cache_key = f"extraction:{sha256(window_text.encode()).hexdigest()}"
redis.setex(cache_key, timedelta(days=7), orjson.dumps(result))
```

**Metadata Key**: `extraction:meta:{content_hash}`
- **Value**: JSON with extractor version, timestamp
- **TTL**: 7 days

---

#### 2. Dead Letter Queue (DLQ)

**Pattern**: `dlq:extraction:{content_hash}`
- **Value**: JSON with error details, retry count, timestamps
- **TTL**: 30 days
- **Purpose**: Track failed extraction attempts

**Retry Count Key**: `dlq:retry:{content_hash}`
- **Value**: Integer (0-3)
- **TTL**: 30 days

**Permanently Failed Key**: `dlq:failed:{content_hash}`
- **Value**: JSON with error, final timestamp, extractor version
- **TTL**: 90 days (long retention for forensics)

**Sorted Set for Priority Queue**: `dlq:pending`
- **Score**: Unix timestamp of next retry
- **Value**: `content_hash`
- **Purpose**: Time-ordered retry queue

---

#### 3. Job State

**Pattern**: `job:{job_id}`
- **Value**: JSON with status, progress, timestamps
- **TTL**: 7 days after completion
- **Purpose**: Track long-running ingestion jobs

**Job States**:
```python
class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
```

**Example**:
```json
{
  "job_id": "fwl_xyz123",
  "status": "running",
  "source": "web",
  "url": "https://example.com/docs",
  "started_at": "2025-10-20T14:30:00Z",
  "updated_at": "2025-10-20T14:30:45Z",
  "progress": {
    "pages_crawled": 12,
    "pages_total": 50,
    "chunks_created": 340,
    "triples_extracted": 1205
  }
}
```

---

## State Transitions

### Job Lifecycle

```
QUEUED → RUNNING → SUCCEEDED
              ↓
           FAILED
              ↓
          (manual retry) → RUNNING
```

**Transition Rules**:
- `QUEUED`: Initial state when job created
- `QUEUED → RUNNING`: When worker picks up job
- `RUNNING → SUCCEEDED`: All pages/files ingested successfully
- `RUNNING → FAILED`: Unrecoverable error (service down, invalid credentials, etc.)
- `RUNNING → CANCELED`: User-initiated cancellation
- `FAILED → RUNNING`: Manual retry via API (`POST /jobs/{job_id}/retry`)

**State Constraints**:
- Cannot transition from `SUCCEEDED` to any other state
- Cannot transition from `CANCELED` to `RUNNING` (must create new job)
- `RUNNING` jobs older than 24 hours auto-transition to `FAILED` with timeout error

---

### Extraction DLQ Lifecycle

```
NEW → PENDING → RETRY_1 → RETRY_2 → RETRY_3 → PERMANENTLY_FAILED
           ↓         ↓          ↓          ↓
        SUCCESS   SUCCESS    SUCCESS    SUCCESS
```

**Transition Rules**:
- `NEW`: Window added to extraction queue
- `NEW → PENDING`: First extraction attempt
- `PENDING → SUCCESS`: Extraction succeeded
- `PENDING → RETRY_1`: Transient error (timeout, network, etc.)
- `RETRY_1 → RETRY_2`: Second failure
- `RETRY_2 → RETRY_3`: Third failure
- `RETRY_3 → PERMANENTLY_FAILED`: Max retries exceeded
- Any `RETRY_N → SUCCESS`: Extraction succeeded after retry

**Retry Backoff**:
- Retry 1: 1 second delay
- Retry 2: 5 seconds delay
- Retry 3: 25 seconds delay

**Permanent Failure Causes**:
- Malformed JSON output from LLM (after 3 attempts)
- Schema validation failure (after 3 attempts)
- Window exceeds 512 token limit (non-retryable)
- LLM service permanently unavailable (manual intervention required)

---

### Document Retention Lifecycle

```
INGESTED → ACTIVE → EXPIRING → DELETED
                ↓
            MANUAL_DELETE → DELETED
```

**Transition Rules**:
- `INGESTED`: Document added to system
- `INGESTED → ACTIVE`: Extraction complete, document queryable
- `ACTIVE → EXPIRING`: Retention policy deadline approaching (7 days before)
- `EXPIRING → DELETED`: Retention deadline reached, auto-delete triggered
- `ACTIVE → MANUAL_DELETE`: User-initiated deletion (`DELETE /documents/{doc_id}`)
- `MANUAL_DELETE → DELETED`: Deletion complete (Neo4j + Qdrant + Redis cleanup)

**Deletion Operations**:
1. Delete all Neo4j nodes/relationships with `docId`
2. Delete all Qdrant points with `doc_id` payload
3. Delete all Redis cache entries with `docId` prefix
4. Log deletion event for audit trail

**Constraints**:
- `DELETED` documents cannot be restored (create new ingestion job)
- `retentionPolicy=null` means permanent retention (never transitions to EXPIRING)
- `MANUAL_DELETE` overrides retention policy

---

## Validation Rules Summary

### Global Constraints

1. **Idempotency**: All writes must be idempotent (MERGE in Neo4j, upsert in Qdrant, SETEX in Redis)
2. **Provenance**: Every extracted relationship must include `docId`, `source` (tier), `confidence`, `extractionMethod`
3. **Timestamps**: All `createdAt` must be ≤ `now()`; all `updatedAt` must be ≥ `createdAt`
4. **Confidence Scores**: Must be in range [0.0, 1.0]; precision-first extraction targets ≥0.85 precision
5. **Determinism**: Tier A extractions must produce byte-identical output for same input + extractor version

---

### Neo4j Validation

**Constraint Count**: 14 (11 unique, 3 composite index)

**Invariants**:
- No orphan nodes (every node must connect to at least one other node or Document)
- No duplicate relationships (unique on relationship type + properties)
- All relationship properties must include provenance fields (`docId`, `confidence`, `source`)

**Enforcement**:
```cypher
-- Pre-write validation query (example for DEPENDS_ON)
MATCH (s:Service {name: $service}), (d:Service {name: $dependency})
MERGE (s)-[r:DEPENDS_ON]->(d)
SET r.docId = $docId,
    r.confidence = $confidence,
    r.source = $source,
    r.extractionMethod = $method,
    r.since = coalesce(r.since, datetime())
RETURN r
```

---

### Qdrant Validation

**Point Count**: No hard limit (tested up to 10M points)

**Invariants**:
- Every point must have all 15 payload fields
- `chunk_id` must be unique across collection
- `(sha256, namespace)` tuple must be unique (enforced via deduplication logic)
- Vector dimensions must match collection config (1024-dim)

**Enforcement**:
```python
from pydantic import BaseModel, Field, validator

class QdrantPayload(BaseModel):
    doc_id: str = Field(..., min_length=36, max_length=36)  # UUID v4
    chunk_id: str = Field(..., pattern=r"^[a-f0-9-]{36}:\d+$")
    namespace: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    source: str = Field(..., regex=r"^(web|github|reddit|youtube|gmail|elasticsearch|compose|swag|tailscale|unifi|ai_session)$")
    job_id: str = Field(...)
    sha256: str = Field(..., regex=r"^[a-f0-9]{64}$")
    mime: str = Field(...)
    lang: str = Field(..., min_length=2, max_length=5)
    chunk_index: int = Field(..., ge=0)
    text_len: int = Field(..., ge=1)
    created_at: int = Field(..., ge=0)
    updated_at: int = Field(..., ge=0)
    tags: List[str] = Field(default_factory=list)

    @validator("updated_at")
    def updated_at_must_be_gte_created_at(cls, v, values):
        if "created_at" in values and v < values["created_at"]:
            raise ValueError("updated_at must be >= created_at")
        return v
```

---

### Redis Validation

**Key Expiry**: All keys must have TTL (no permanent keys except job state during active ingestion)

**Invariants**:
- Extraction cache entries must have 7-day TTL
- DLQ entries must have 30-day TTL
- Job state entries must have 7-day TTL after completion
- Retry count must be ≤3

**Enforcement**:
```python
def add_to_dlq(content_hash: str, error: Dict[str, Any]) -> None:
    """Add failed extraction to DLQ with validation."""
    retry_count = redis.get(f"dlq:retry:{content_hash}") or 0

    if retry_count >= 3:
        # Permanently failed
        redis.setex(
            f"dlq:failed:{content_hash}",
            timedelta(days=90),
            orjson.dumps({"error": error, "final_timestamp": datetime.now().isoformat()})
        )
        redis.delete(f"dlq:retry:{content_hash}")
    else:
        # Add to retry queue
        redis.setex(
            f"dlq:extraction:{content_hash}",
            timedelta(days=30),
            orjson.dumps({"error": error, "retry_count": retry_count + 1})
        )
        redis.incr(f"dlq:retry:{content_hash}")
        redis.zadd("dlq:pending", {content_hash: time.time() + backoff(retry_count)})
```

---

## Error Codes

All errors follow the pattern `E_{CATEGORY}_{SPECIFIC}` and map to HTTP status codes:

### Ingestion Errors (4xx Client Errors)

- **E_URL_BAD** (400): Malformed URL or invalid file path
- **E_ROBOTS** (403): Blocked by robots.txt
- **E_403_WAF** (403): WAF rejection (Cloudflare, etc.)
- **E_429_RATE** (429): Rate limit exceeded (Firecrawl, external API)

### Service Errors (5xx Server Errors)

- **E_5XX_ORIGIN** (502): Origin server error (external service down)
- **E_PARSE** (500): Content parsing failure (invalid YAML, malformed HTML, etc.)
- **E_TIMEOUT** (504): Request timeout (Firecrawl, external API)
- **E_BROWSER** (500): Playwright/browser error

### Storage Errors (5xx Server Errors)

- **E_QDRANT** (503): Vector DB error (connection, write, search failure)
- **E_NEO4J** (503): Graph DB error (connection, Cypher syntax, deadlock after retries)
- **E_REDIS** (503): Cache/DLQ error (connection, memory full)
- **E_GPU_OOM** (507): GPU out of memory (TEI, reranker, Ollama)

### Extraction Errors (4xx/5xx)

- **E_TOKEN_LIMIT** (400): Window exceeds 512 tokens (non-retryable)
- **E_SCHEMA_INVALID** (422): LLM output doesn't match JSON schema (after validation)
- **E_LLM_TIMEOUT** (504): Ollama request timeout
- **E_LLM_MALFORMED** (500): Unparseable JSON from LLM

### Error Response Format

```json
{
  "error": {
    "code": "E_NEO4J",
    "message": "Failed to write triples to Neo4j after 5 retries",
    "details": {
      "doc_id": "abc123",
      "chunk_id": "abc123:45",
      "retry_count": 5,
      "last_error": "DeadlockDetectedException: Transaction was rolled back"
    },
    "timestamp": "2025-10-20T14:30:00Z",
    "request_id": "req_xyz789"
  }
}
```

---

## Performance Constraints

### Throughput Targets (RTX 4070)

| Component | Target | Rationale |
|-----------|--------|-----------|
| Tier A extraction | ≥50 pages/sec | CPU-bound, deterministic parsing (regex, JSON/YAML, Aho-Corasick) |
| Tier B extraction | ≥200 sentences/sec | spaCy `en_core_web_md` with entity_ruler + dependency matchers |
| Tier C LLM | ≤250ms/window median | Qwen3-4B-Instruct batched 8-16, with Redis caching |
| Neo4j writes | ≥20k edges/min | 2k-row UNWIND batches with idempotent MERGE |
| Qdrant upserts | ≥5k vectors/sec | 1024-dim HNSW GPU indexing with batching |
| E2E retrieval | <3s p95 | Embed + search + rerank + graph + synthesis |

### Latency Targets

| Operation | P50 | P95 | P99 |
|-----------|-----|-----|-----|
| Query embedding (TEI) | 30ms | 80ms | 150ms |
| Vector search (Qdrant) | 50ms | 120ms | 250ms |
| Reranking (top-100 → top-5) | 80ms | 200ms | 400ms |
| Graph traversal (≤2 hops) | 40ms | 100ms | 200ms |
| Synthesis (Qwen3-4B) | 800ms | 1500ms | 2500ms |
| **Total E2E** | **1.0s** | **2.0s** | **3.5s** |

### Accuracy Constraints

| Metric | Target | Enforcement |
|--------|--------|-------------|
| Extraction F1 | ≥0.80 | CI fails if drop ≥2 points |
| Extraction Precision | ≥0.85 | Precision-first (false positives dangerous for infra graphs) |
| Extraction Recall | ≥0.75 | Secondary to precision |
| Citation Accuracy | 100% | All citations must link to valid sources |
| Cache Hit Rate (Tier C) | ≥60% | After warmup on repeated content |

---

## Document Version

- **Version**: 1.0.0
- **Date**: 2025-10-20
- **Status**: Phase 1 Complete
- **Next**: Generate contracts (neo4j-schema.cypher, qdrant-collection.json, extraction-tier-schemas.json, api-openapi.yaml)
