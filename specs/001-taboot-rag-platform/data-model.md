# Data Model: Taboot Doc-to-Graph RAG Platform

**Date**: 2025-10-21
**Purpose**: Define entities, relationships, validation rules, and state transitions

## Overview

This data model defines the structure for both relational (PostgreSQL, Redis state) and graph (Neo4j) storage, plus vector metadata (Qdrant). The model supports multi-source ingestion, multi-tier extraction, and hybrid retrieval.

---

## Core Entities

### Document (Relational: PostgreSQL)

Represents an ingested document from any source.

**Fields**:
- `doc_id`: UUID (primary key, generated on ingestion)
- `source_url`: str (original source URL or identifier, max 2048 chars)
- `source_type`: enum (web, GitHub, Reddit, YouTube, Gmail, Elasticsearch, Docker Compose, SWAG, Tailscale, UniFi, AI Session)
  - *Note: Enum values stored lowercase (`web`, `github`, `reddit`, `youtube`, etc.); docs use proper casing for readability*
- `content_hash`: str (SHA-256 hex digest of normalized content, 64 chars)
- `ingested_at`: datetime (UTC timestamp of ingestion)
- `extraction_state`: enum (`pending`, `tier_a_done`, `tier_b_done`, `tier_c_done`, `completed`, `failed`)
- `extraction_version`: str (extractor version tag, e.g., `v1.2.0`, nullable)
- `updated_at`: datetime (UTC timestamp of last update)
- `metadata`: JSONB (arbitrary key-value pairs: `{"page_count": 42, "author": "..."}, nullable`)

**Validation Rules**:
- `doc_id`: Required, unique
- `source_url`: Required, non-empty, valid URL or file path
- `source_type`: Required, must be one of enum values
- `content_hash`: Required, 64-char hex string (SHA-256)
- `ingested_at`: Required, must be <= current time
- `extraction_state`: Required, must be one of enum values
- `extraction_version`: Optional, semver format if provided
- `updated_at`: Required, auto-updated on modification

**Indexes**:
- Primary: `doc_id`
- Composite: `(source_type, ingested_at)` for filtering by source and date
- Unique: `content_hash` for deduplication

---

### Chunk (Qdrant Vector Database)

Represents a semantic chunk of a document with embedding vector.

**Fields** (stored in Qdrant point payload):
- `chunk_id`: UUID (Qdrant point ID)
- `doc_id`: UUID (foreign key to Document)
- `content`: str (chunk text, up to 4096 chars)
- `section`: str (heading/path context, e.g., `"Installation > Prerequisites"`, max 512 chars)
- `position`: int (offset in document, 0-indexed)
- `token_count`: int (number of tokens in chunk, for context window management)
- `embedding`: float array (1024-dim vector from Qwen3-Embedding-0.6B, stored separately in Qdrant)

**Qdrant Metadata** (for filtering):
- `source_url`: str (copied from Document)
- `source_type`: str (copied from Document)
- `ingested_at`: int (Unix timestamp, copied from Document)
- `tags`: list[str] (optional tags for filtering, e.g., `["kubernetes", "networking"]`)

**Validation Rules**:
- `chunk_id`: Required, unique
- `doc_id`: Required, must reference existing Document
- `content`: Required, non-empty, 1-4096 chars
- `section`: Optional, max 512 chars
- `position`: Required, ≥0
- `token_count`: Required, ≥1, ≤512 (enforced by chunker)
- `embedding`: Required, exactly 1024 dimensions, normalized (cosine similarity)

**Qdrant Collection Config**:
- Dimension: 1024
- Distance: Cosine
- HNSW: `M=16`, `ef_construct=200`
- Quantization: Scalar (optional for memory savings)

---

### Service (Graph: Neo4j Node)

Represents a software service/application.

**Properties**:
- `name`: str (unique, max 256 chars, e.g., `"api-service"`, `"postgres"`)
- `description`: str (optional, max 2048 chars)
- `image`: str (optional, Docker image or binary path, max 512 chars)
- `version`: str (optional, semver or tag, max 64 chars)
- `metadata`: map (arbitrary key-value pairs, e.g., `{env: "production", replicas: 3}`)
- `created_at`: datetime (UTC timestamp of node creation)
- `updated_at`: datetime (UTC timestamp of last update)
- `extraction_version`: str (extractor version tag, nullable)

**Validation Rules**:
- `name`: Required, unique, non-empty, alphanumeric + hyphen/underscore
- `description`: Optional, max 2048 chars
- `image`: Optional, max 512 chars
- `version`: Optional, max 64 chars
- `metadata`: Optional, valid map
- `created_at`, `updated_at`: Required, auto-managed
- `extraction_version`: Optional, semver format if provided

**Constraints**:
- Unique constraint on `name`

---

### Host (Graph: Neo4j Node)

Represents a physical or virtual machine.

**Properties**:
- `hostname`: str (unique, max 256 chars, e.g., `"server01.example.com"`)
- `ip_addresses`: list[str] (array of IP addresses, dotted notation or CIDR)
- `os`: str (optional, max 128 chars, e.g., `"Ubuntu 22.04"`)
- `location`: str (optional, max 256 chars, e.g., `"us-east-1a"`)
- `metadata`: map (arbitrary key-value pairs)
- `created_at`: datetime
- `updated_at`: datetime
- `extraction_version`: str (nullable)

**Validation Rules**:
- `hostname`: Required, unique, non-empty, valid hostname format
- `ip_addresses`: Optional, each IP must be valid IPv4/IPv6 dotted notation or CIDR
- `os`: Optional, max 128 chars
- `location`: Optional, max 256 chars
- `metadata`: Optional, valid map

**Constraints**:
- Unique constraint on `hostname`

---

### IP (Graph: Neo4j Node)

Represents an IP address.

**Properties**:
- `addr`: str (unique, dotted notation or CIDR, max 64 chars, e.g., `"192.168.1.10"`, `"10.0.0.0/24"`)
- `ip_type`: enum (`v4`, `v6`)
- `allocation`: enum (`static`, `dhcp`, `unknown`)
- `metadata`: map
- `created_at`: datetime
- `updated_at`: datetime
- `extraction_version`: str (nullable)

**Validation Rules**:
- `addr`: Required, unique, valid IPv4/IPv6 dotted notation or CIDR
- `ip_type`: Required, must be `v4` or `v6`
- `allocation`: Required, must be one of enum values
- `metadata`: Optional, valid map

**Constraints**:
- Unique constraint on `addr`

---

### Proxy (Graph: Neo4j Node)

Represents a reverse proxy or gateway.

**Properties**:
- `name`: str (unique, max 256 chars, e.g., `"nginx-proxy"`, `"swag"`)
- `proxy_type`: enum (`nginx`, `traefik`, `haproxy`, `swag`, `other`)
- `config_path`: str (optional, file path to config, max 512 chars)
- `metadata`: map
- `created_at`: datetime
- `updated_at`: datetime
- `extraction_version`: str (nullable)

**Validation Rules**:
- `name`: Required, unique, non-empty
- `proxy_type`: Required, must be one of enum values
- `config_path`: Optional, valid file path format
- `metadata`: Optional, valid map

**Constraints**:
- Unique constraint on `name`

---

### Endpoint (Graph: Neo4j Node)

Represents an HTTP/API endpoint.

**Properties**:
- `service`: str (foreign key to Service.name, max 256 chars)
- `method`: enum (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `*`)
- `path`: str (URL path pattern, max 512 chars, e.g., `"/api/v1/users/{id}"`)
- `auth`: str (optional, authentication method, max 128 chars, e.g., `"JWT"`, `"OAuth2"`, `"none"`)
- `rate_limit`: int (optional, requests per minute, ≥0)
- `metadata`: map
- `created_at`: datetime
- `updated_at`: datetime
- `extraction_version`: str (nullable)

**Validation Rules**:
- `service`: Required, must reference existing Service.name
- `method`: Required, must be one of enum values
- `path`: Required, non-empty, valid URL path pattern
- `auth`: Optional, max 128 chars
- `rate_limit`: Optional, ≥0 if provided
- `metadata`: Optional, valid map

**Constraints**:
- Composite unique index on `(service, method, path)`

---

### ExtractionWindow (Relational: PostgreSQL)

Represents a micro-window processed by Tier C LLM extraction.

**Fields**:
- `window_id`: UUID (primary key)
- `doc_id`: UUID (foreign key to Document)
- `content`: str (text content, max 2048 chars, ≤512 tokens)
- `tier`: enum (`A`, `B`, `C`)
- `triples_generated`: int (count of triples extracted from this window, ≥0)
- `llm_latency_ms`: int (nullable, LLM inference time in milliseconds, only for tier=C)
- `cache_hit`: bool (nullable, whether LLM response was cached, only for tier=C)
- `processed_at`: datetime (UTC timestamp)
- `extraction_version`: str (nullable)

**Validation Rules**:
- `window_id`: Required, unique
- `doc_id`: Required, must reference existing Document
- `content`: Required, non-empty, max 2048 chars
- `tier`: Required, must be `A`, `B`, or `C`
- `triples_generated`: Required, ≥0
- `llm_latency_ms`: Optional (tier C only), ≥0 if provided
- `cache_hit`: Optional (tier C only)
- `processed_at`: Required, must be <= current time

**Indexes**:
- Primary: `window_id`
- Foreign key: `doc_id`
- Composite: `(doc_id, tier)` for filtering windows by document and tier

---

### Triple (Graph: Neo4j Relationship Property)

Represents an extracted knowledge triple. Stored as properties on Neo4j relationships.

**Properties** (attached to relationships):
- `source_window_id`: UUID (foreign key to ExtractionWindow, identifies extraction source)
- `confidence`: float (0.0-1.0, extraction confidence score)
- `extraction_version`: str (nullable, extractor version tag)
- `created_at`: datetime
- `updated_at`: datetime

**Validation Rules**:
- `source_window_id`: Required, must reference existing ExtractionWindow
- `confidence`: Required, 0.0 ≤ confidence ≤ 1.0
- `extraction_version`: Optional, semver format if provided

---

### IngestionJob (Relational: PostgreSQL)

Represents an ingestion task.

**Fields**:
- `job_id`: UUID (primary key)
- `source_type`: enum (same as Document.source_type)
- `source_target`: str (URL, repo name, file path, max 2048 chars)
- `state`: enum (`pending`, `running`, `completed`, `failed`)
- `created_at`: datetime
- `started_at`: datetime (nullable, when job started)
- `completed_at`: datetime (nullable, when job completed)
- `pages_processed`: int (count of pages/documents ingested, ≥0)
- `chunks_created`: int (count of chunks created, ≥0)
- `errors`: JSONB (nullable, array of error objects: `[{error: "...", url: "...", timestamp: "..."}]`)

**Validation Rules**:
- `job_id`: Required, unique
- `source_type`: Required, must be one of enum values
- `source_target`: Required, non-empty, max 2048 chars
- `state`: Required, must be one of enum values
- `created_at`: Required, must be <= current time
- `started_at`: Optional, must be >= created_at if provided
- `completed_at`: Optional, must be >= started_at if provided
- `pages_processed`: Required, ≥0
- `chunks_created`: Required, ≥0
- `errors`: Optional, valid JSON array

**State Transitions**:
- `pending` → `running` (job starts)
- `running` → `completed` (job succeeds)
- `running` → `failed` (job encounters unrecoverable error)

**Indexes**:
- Primary: `job_id`
- Composite: `(source_type, state, created_at)` for filtering active jobs

---

### ExtractionJob (Relational: PostgreSQL)

Represents an extraction task for a document.

**Fields**:
- `job_id`: UUID (primary key)
- `doc_id`: UUID (foreign key to Document)
- `state`: enum (`pending`, `tier_a_done`, `tier_b_done`, `tier_c_done`, `completed`, `failed`)
- `tier_a_triples`: int (count of triples from Tier A, ≥0)
- `tier_b_windows`: int (count of windows selected by Tier B, ≥0)
- `tier_c_triples`: int (count of triples from Tier C, ≥0)
- `started_at`: datetime (nullable)
- `completed_at`: datetime (nullable)
- `retry_count`: int (number of retry attempts, ≥0, max 3)
- `errors`: JSONB (nullable, error log)

**Validation Rules**:
- `job_id`: Required, unique
- `doc_id`: Required, must reference existing Document
- `state`: Required, must be one of enum values
- `tier_a_triples`: Required, ≥0
- `tier_b_windows`: Required, ≥0
- `tier_c_triples`: Required, ≥0
- `started_at`: Optional, must be <= current time if provided
- `completed_at`: Optional, must be >= started_at if provided
- `retry_count`: Required, 0 ≤ retry_count ≤ 3
- `errors`: Optional, valid JSON

**State Transitions**:
- `pending` → `tier_a_done` (Tier A completes)
- `tier_a_done` → `tier_b_done` (Tier B completes)
- `tier_b_done` → `tier_c_done` (Tier C completes)
- `tier_c_done` → `completed` (all tiers done, graph writes complete)
- Any → `failed` (unrecoverable error, retry_count = 3)

**Indexes**:
- Primary: `job_id`
- Foreign key: `doc_id`
- Composite: `(state, started_at)` for worker job selection

---

## Relationships (Neo4j Graph Model)

### DEPENDS_ON

**Source**: Service
**Target**: Service
**Direction**: Service A → Service B (A depends on B)

**Properties**:
- `dependency_type`: str (optional, e.g., `"runtime"`, `"buildtime"`, max 64 chars)
- `source_window_id`: UUID (extraction source)
- `confidence`: float (0.0-1.0)
- `extraction_version`: str (nullable)
- `created_at`: datetime
- `updated_at`: datetime

**Validation Rules**:
- Source and target must be different services
- `dependency_type`: Optional, max 64 chars
- `confidence`: 0.0 ≤ confidence ≤ 1.0

**Example**: `(api-service)-[:DEPENDS_ON {dependency_type: "runtime"}]->(postgres)`

---

### ROUTES_TO

**Source**: Proxy
**Target**: Service
**Direction**: Proxy → Service (proxy routes traffic to service)

**Properties**:
- `host`: str (optional, virtual host, max 256 chars, e.g., `"api.example.com"`)
- `path`: str (optional, URL path pattern, max 512 chars, e.g., `"/api/*"`)
- `tls`: bool (whether TLS/HTTPS is enabled)
- `source_window_id`: UUID
- `confidence`: float (0.0-1.0)
- `extraction_version`: str (nullable)
- `created_at`: datetime
- `updated_at`: datetime

**Validation Rules**:
- `host`: Optional, valid hostname format
- `path`: Optional, valid URL path pattern
- `tls`: Required, boolean
- `confidence`: 0.0 ≤ confidence ≤ 1.0

**Example**: `(nginx-proxy)-[:ROUTES_TO {host: "api.example.com", path: "/v1/*", tls: true}]->(api-service)`

---

### BINDS

**Source**: Service
**Target**: (Implicit port, stored as property)
**Direction**: Service → Port (service binds to port)

**Properties**:
- `port`: int (port number, 1-65535)
- `protocol`: enum (`tcp`, `udp`)
- `source_window_id`: UUID
- `confidence`: float (0.0-1.0)
- `extraction_version`: str (nullable)
- `created_at`: datetime
- `updated_at`: datetime

**Validation Rules**:
- `port`: Required, 1 ≤ port ≤ 65535
- `protocol`: Required, must be `tcp` or `udp`
- `confidence`: 0.0 ≤ confidence ≤ 1.0

**Example**: `(api-service)-[:BINDS {port: 8080, protocol: "tcp"}]->()`

**Note**: Target is implicit (no Port node), port stored as relationship property.

---

### RUNS

**Source**: Host
**Target**: Service
**Direction**: Host → Service (host runs service)

**Properties**:
- `container_id`: str (optional, Docker container ID, max 128 chars)
- `pid`: int (optional, process ID, ≥0)
- `source_window_id`: UUID
- `confidence`: float (0.0-1.0)
- `extraction_version`: str (nullable)
- `created_at`: datetime
- `updated_at`: datetime

**Validation Rules**:
- `container_id`: Optional, max 128 chars
- `pid`: Optional, ≥0 if provided
- `confidence`: 0.0 ≤ confidence ≤ 1.0

**Example**: `(server01)-[:RUNS {container_id: "abc123", pid: 42}]->(api-service)`

---

### EXPOSES_ENDPOINT

**Source**: Service
**Target**: Endpoint
**Direction**: Service → Endpoint (service exposes endpoint)

**Properties**:
- `auth`: str (optional, overrides Endpoint.auth, max 128 chars)
- `source_window_id`: UUID
- `confidence`: float (0.0-1.0)
- `extraction_version`: str (nullable)
- `created_at`: datetime
- `updated_at`: datetime

**Validation Rules**:
- `auth`: Optional, max 128 chars
- `confidence`: 0.0 ≤ confidence ≤ 1.0

**Example**: `(api-service)-[:EXPOSES_ENDPOINT {auth: "JWT"}]->(GET /api/v1/users)`

---

### MENTIONS

**Source**: (Implicit Chunk, referenced via Qdrant)
**Target**: Entity (Service, Host, IP, Proxy, Endpoint)
**Direction**: Chunk → Entity (chunk mentions entity)

**Properties**:
- `span`: str (text snippet from chunk, max 512 chars)
- `section`: str (heading/path context, max 512 chars)
- `hash`: str (content hash of chunk, 64-char SHA-256)
- `chunk_id`: UUID (Qdrant point ID)
- `doc_id`: UUID (source document)
- `source_window_id`: UUID
- `confidence`: float (0.0-1.0)
- `extraction_version`: str (nullable)
- `created_at`: datetime
- `updated_at`: datetime

**Validation Rules**:
- `span`: Required, non-empty, max 512 chars
- `section`: Optional, max 512 chars
- `hash`: Required, 64-char hex string
- `chunk_id`: Required, must reference existing Qdrant point
- `doc_id`: Required, must reference existing Document
- `confidence`: 0.0 ≤ confidence ≤ 1.0

**Example**: `(chunk:abc123)-[:MENTIONS {span: "api-service depends on postgres", section: "Architecture", hash: "..."}]->(Service:postgres)`

**Note**: Source is implicit (Chunk in Qdrant), referenced via `chunk_id`.

---

### LOCATED_AT

**Source**: Host
**Target**: IP
**Direction**: Host → IP (host is located at IP)

**Properties**:
- `interface`: str (optional, network interface name, max 64 chars, e.g., `"eth0"`)
- `source_window_id`: UUID
- `confidence`: float (0.0-1.0)
- `extraction_version`: str (nullable)
- `created_at`: datetime
- `updated_at`: datetime

**Validation Rules**:
- `interface`: Optional, max 64 chars
- `confidence`: 0.0 ≤ confidence ≤ 1.0

**Example**: `(server01)-[:LOCATED_AT {interface: "eth0"}]->(IP:192.168.1.10)`

---

### CONNECTS_TO

**Source**: Service
**Target**: Host
**Direction**: Service → Host (service connects to host)

**Properties**:
- `port`: int (optional, destination port, 1-65535)
- `protocol`: enum (optional, `tcp`, `udp`)
- `source_window_id`: UUID
- `confidence`: float (0.0-1.0)
- `extraction_version`: str (nullable)
- `created_at`: datetime
- `updated_at`: datetime

**Validation Rules**:
- `port`: Optional, 1 ≤ port ≤ 65535 if provided
- `protocol`: Optional, must be `tcp` or `udp` if provided
- `confidence`: 0.0 ≤ confidence ≤ 1.0

**Example**: `(api-service)-[:CONNECTS_TO {port: 5432, protocol: "tcp"}]->(db-host)`

---

## State Machine: Extraction Pipeline

### Document Extraction State

```text
pending
  ↓
tier_a_done (Deterministic extraction complete)
  ↓
tier_b_done (spaCy NLP extraction complete)
  ↓
tier_c_done (LLM window extraction complete)
  ↓
completed (Graph writes complete)

Any state → failed (on error, retry_count = 3)
```

**Transitions**:
1. `pending → tier_a_done`: Tier A extractor processes document, generates triples, writes to Neo4j
2. `tier_a_done → tier_b_done`: Tier B extractor selects micro-windows, identifies candidate spans
3. `tier_b_done → tier_c_done`: Tier C LLM processes windows, generates triples, writes to Neo4j
4. `tier_c_done → completed`: Final graph consistency check, mark document complete
5. Any → `failed`: Unrecoverable error after 3 retries, send to DLQ

---

## Summary

This data model defines:
- **9 entity types**: Document, Chunk, Service, Host, IP, Proxy, Endpoint, ExtractionWindow, Triple
- **8 relationship types**: DEPENDS_ON, ROUTES_TO, BINDS, RUNS, EXPOSES_ENDPOINT, MENTIONS, LOCATED_AT, CONNECTS_TO
- **2 job types**: IngestionJob, ExtractionJob
- **State machines**: Document extraction pipeline (5 states + failed)
- **Validation rules**: Field constraints, uniqueness, foreign keys, state transitions
- **Indexes**: Primary keys, composite indexes for query performance

Fields enforce explicit validation rules; relationships include confidence scores and extraction provenance; nodes and relationships are versioned to support reprocessing.
