# LlamaCrawl v2 — Technical Implementation Plan Context

**Created**: 2025-10-20
**Based on**: 5 parallel code-finder agent investigations + specification clarifications

---

## Executive Summary

LlamaCrawl v2 is a **production-ready architectural design** waiting for implementation. Core layers are defined but mostly skeleton code. This document serves as input for `/speckit.plan` command.

### Key Stats
- **11 Docker services** (4 GPU-accelerated)
- **7 adapter packages** (ingest, extraction, graph, vector, retrieval, schemas, common)
- **3 app shells** (FastAPI, Typer CLI, MCP server)
- **Strict layering**: apps → adapters → core (framework-agnostic business logic)
- **GPU targets**: RTX 4070 baseline; ≥50 pages/sec (Tier A), ≥200 sentences/sec (Tier B), ≤250ms/window (Tier C)

---

## 1. Architecture Overview

### Layer Model (Strict Dependency Flow)

```
apps/api (FastAPI)
apps/cli (Typer)
apps/mcp (MCP server)
    ↓
packages/ingest         (Firecrawl, normalizer, chunker)
packages/extraction     (Tier A/B/C extractors: regex, spaCy, Qwen3-4B)
packages/graph          (Neo4j driver, Cypher, UNWIND batches)
packages/vector         (Qdrant client, HNSW, hybrid search)
packages/retrieval      (LlamaIndex indices, retrievers, query engines)
    ↓
packages/core           (Domain models, use-cases, ports/interfaces)
packages/schemas        (Pydantic DTOs, OpenAPI)
packages/common         (Logging, config, observability)
```

**Rule**: Core depends ONLY on schemas + common. Adapters implement ports from core. Apps are thin I/O shells calling core use-cases.

---

## 2. Core Domain Model (Not Yet Implemented)

### Node Labels (Neo4j)
- `Host` — Physical/virtual machine (unique hostname)
- `Container` — Containerized runtime (compose_project, compose_service)
- `Service` — Logical networked service (name, protocol, port)
- `Endpoint` — Externally reachable URL/socket (scheme, fqdn, port, path)
- `Network` — L2/L3 segment (unique CIDR)
- `User` — Human or service principal (provider, username)
- `Credential` — API key or secret reference
- `Repository` — Code repo (platform, org, name)
- `Package` — Software component (pypi, npm, dockerhub, ghcr)
- `Document` — Ingested page/file (doc_id, url, title)
- `IP` — Routable IP address (unique addr)

### Relationship Types
- `RUNS` (Host → Container), `EXPOSES` (Container → Service), `BINDS_TO` (Service → Endpoint)
- `RESOLVES_TO` (Endpoint → IP), `CONTAINS` (Network → Host)
- `DEPENDS_ON` (Service → Service), `ROUTES_TO` (ReverseProxy → Service)
- `USES_CREDENTIAL` (User → Credential), `BUILDS` (Repository → Package)
- `MENTIONS` (Document → Entity, with provenance), `RUNS_IN` (Package → Container)

### Vector Payload Schema (Qdrant)
Single collection `taboot.documents` (1024-dim, Cosine):
- **Keyword fields**: doc_id, chunk_id, namespace, url, title, source, job_id, sha256, mime, lang
- **Numeric**: chunk_index, text_len
- **Datetime**: created_at, updated_at
- **Array**: tags

---

## 3. Ingestion Plane (packages/ingest/)

### Pipeline
```
Firecrawl/source readers
  → Normalizer (HTML→MD, boilerplate removal)
  → Chunker (semantic, ≤512 tokens, with overlap)
  → TEI embeddings (GPU, 1024-dim, Qwen3-Embedding-0.6B)
  → Qdrant upserts
  + Document metadata to Neo4j
  + Extraction queue to Redis
```

### Sources (11+)
- Web URLs (Firecrawl)
- GitHub (git clone, README + code comments)
- Reddit (threads, comments)
- YouTube (transcripts)
- Gmail (email attachments)
- Elasticsearch (indexed documents)
- Docker Compose (deterministic parsing)
- SWAG (nginx/reverse proxy configs)
- Tailscale (network state)
- Unifi (network topology)
- AI sessions (LLM conversation history)

### Expected Structure
```
packages/ingest/
├── sources/          # Source-specific clients
├── normalizers/      # HTML/markdown normalization
├── chunkers/         # Chunking strategies
├── services/         # Orchestration (queues, retries)
└── utils/
```

**Performance target**: ≥50 pages/sec (Tier A deterministic parsing)

---

## 4. Extraction Plane (packages/extraction/)

### Tiered Architecture
1. **Tier A (Deterministic)** — Regex, JSON/YAML parsers, Aho-Corasick dictionaries → **≥50 pages/sec**
2. **Tier B (spaCy NLP)** — Entity rulers, dependency matchers, sentence classifier → **≥200 sentences/sec (md)** or **≥40 (trf)**
3. **Tier C (LLM Windows)** — Qwen3-4B-Instruct via Ollama, ≤512 tokens, JSON schema, batched 8–16 → **≤250ms/window median**, p95 ≤750ms

### Output Model
- Extracted triples (subject, predicate, object)
- Buffered in **Redis with TTL** during batch processing
- Atomic commit to Neo4j (UNWIND batches)
- DLQ pattern for failed windows (Redis sorted sets)

### Expected Structure
```
packages/extraction/
├── tier_a/           # Deterministic extractors
├── tier_b/           # spaCy NLP pipeline
├── tier_c/           # LLM window extraction
├── pipelines/        # Tier orchestration
├── services/         # Queueing, caching
└── utils/
```

**Clarifications from spec**:
- Precision-first (target ≥0.85 precision, ≥0.75 recall)
- Fail-fast on service failures (no fallback modes)
- Redis cache by SHA-256(window + extractor_version)

---

## 5. Graph Storage (packages/graph/)

### Schema
- **11 node labels** (Host, Container, Service, Endpoint, Network, User, Credential, Repository, Package, Document, IP)
- **11 relationship types** with properties (confidence, doc_id, source, span, etc.)
- **14 constraints/indexes** (UNIQUE on natural keys, composite indexes on lookup patterns)

### Write Patterns
1. **Docker Compose** → Batch create containers, services, endpoints (UNWIND 2–5k rows)
2. **SWAG routes** → Create reverse proxy → service mappings
3. **Document provenance** → Link Doc → Entity via MENTIONS (with source, confidence, span)

### Read Patterns
1. **Services on host** — `MATCH (h:Host)-[:RUNS]->(:Container)-[:EXPOSES]->(s:Service)`
2. **External endpoints** — `MATCH (e:Endpoint)-[:BINDS_TO]-(s:Service)`
3. **Dependency subgraph** — ≤2-hop traversal with provenance links

### Expected Structure
```
packages/graph/
├── client/           # Neo4j driver setup
├── writers/          # Batched UNWIND logic
├── queries/          # Cypher builders
├── migrations/       # Schema setup (idempotent)
└── utils/
```

**Performance target**: ≥20k edges/min with 2k-row UNWIND batches

---

## 6. Vector Storage (packages/vector/)

### Collection Config
- **Name**: `taboot.documents`
- **Dimension**: 1024 (TEI embeddings)
- **Distance**: Cosine similarity
- **HNSW**: m=32, ef_construct=128, full_scan_threshold=10000
- **Sharding**: 4 shards (scale by data volume)
- **Replication**: 1 (single-node; increase for HA)

### Payload Schema (15 fields)
- Keywords: doc_id, chunk_id, namespace, url, title, source, job_id, sha256, mime, lang
- Numeric: chunk_index, text_len
- Datetime: created_at, updated_at
- Array: tags

### Deduplication
- By `(sha256, namespace)` — if content identical, update metadata + `updated_at`
- Idempotent upserts via `point_id = chunk_id`

### Expected Structure
```
packages/vector/
├── client/           # Qdrant client/session
├── writers/          # Upsert/delete pipelines
├── queries/          # Vector search helpers
├── migrations/       # Collection/index management
└── utils/
```

**Performance target**: ≥5k vectors/sec upsert

---

## 7. Retrieval & Synthesis (packages/retrieval/)

### 6-Stage Pipeline
1. **Query embedding** — TEI to 1024-dim
2. **Metadata filtering** — source, date, namespace, tags
3. **Vector search** — Qdrant top-k (default 100)
4. **Reranking** — BAAI/bge-reranker-v2-m3 via SentenceTransformers (16-batch)
5. **Graph traversal** — Neo4j ≤2-hop neighbor discovery
6. **Synthesis** — Qwen3-4B-Instruct with inline citations + bibliography

### Expected Structure
```
packages/retrieval/
├── context/          # LlamaIndex settings, prompts
├── indices/          # VectorStoreIndex, PropertyGraphIndex
├── retrievers/       # Hybrid retriever + post-processors
├── query_engines/    # QA engine with citation builder
├── services/         # Routing, caching
└── utils/
```

**SLA**: <3s p95 end-to-end (embed + search + rerank + graph + synthesis)

**Key design**: Core layer is framework-agnostic (NO LlamaIndex imports). Adapters implement core ports using LlamaIndex.

---

## 8. API & CLI (apps/api/ & apps/cli/)

### FastAPI (`apps/api/`)
- **Endpoints** (15+ planned):
  - `/health` — liveness probe
  - `/jobs/firecrawl` — POST to create crawl job (202 Accepted)
  - `/jobs/{job_id}` — GET detail, POST cancel, DELETE purge
  - `/ingestions` — create, list, detail, cancel
  - `/crawl:sync` — blocking crawl (200 response)
  - `/sessions` — GET active, DELETE force-close

- **Auth**: Bearer Token (JWT) with expiry + refresh mechanics
- **Response envelope**: `{"data": {...}, "error": {...}}`
- **Error codes**: E_URL_BAD, E_ROBOTS, E_403_WAF, E_429_RATE, E_5XX_ORIGIN, E_PARSE, E_TIMEOUT, E_BROWSER, E_QDRANT, E_NEO4J, E_GPU_OOM

### Typer CLI (`apps/cli/`)
- **Commands** (planned):
  - `taboot ingest web <url>` — ingest from URL
  - `taboot extract pending` — run extraction pipeline
  - `taboot extract reprocess --since 7d` — reprocess docs
  - `taboot graph query "<cypher>"` — execute Neo4j query
  - `taboot query "<question>"` — test retrieval
  - `taboot status` — view extraction metadata
  - `taboot init` — initialize schema + collections

---

## 9. Docker Compose Stack (11 Services)

### GPU Services (4)
| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `taboot-vectors` | qdrant/qdrant:gpu-nvidia | 7000 (HTTP), 7001 (gRPC) | Vector DB (HNSW GPU) |
| `taboot-embed` | ghcr.io/huggingface/text-embeddings-inference | 8080 | TEI embeddings (Qwen3-Embedding-0.6B) |
| `taboot-rerank` | ./docker/reranker/Dockerfile | 8081 | Reranker (Qwen3-Reranker-0.6B) |
| `taboot-ollama` | ollama/ollama:latest | 11434 | LLM (Qwen3-4B-Instruct) |

### Non-GPU Services (7)
| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `taboot-graph` | ./docker/neo4j/Dockerfile (5.23) | 7474, 7687 | Neo4j property graph |
| `taboot-cache` | redis:7.2-alpine | 6379 | Redis (state, DLQ, cache) |
| `taboot-db` | ./docker/postgres/Dockerfile (16) | 5432 | PostgreSQL (Firecrawl metadata) |
| `taboot-playwright` | ghcr.io/firecrawl/playwright-service | 3000 | Browser microservice |
| `taboot-crawler` | ghcr.io/firecrawl/firecrawl | 3002 | Firecrawl orchestrator |
| `taboot-app` | ./docker/app/Dockerfile (Python 3.13) | 8000 | FastAPI app |
| `taboot-worker` | ./docker/worker/Dockerfile (Python 3.13) | — | Extraction worker (optional) |

### Health Checks
- All services have structured health checks
- Dependencies: `taboot-app` waits for healthy cache, vectors, graph, embed, db
- Startup delays: 10–60s

---

## 10. Configuration (.env.example)

**112 environment variables** covering:
- Firecrawl (workers, concurrency, retries)
- PostgreSQL, Redis, Neo4j (URIs, credentials)
- TEI, Reranker, Ollama (model names, device)
- External credentials (GitHub, Reddit, Gmail, Elasticsearch, Tailscale, HF)
- Observability (log level, API URL)

**Example key vars**:
```
FIRECRAWL_API_URL=http://taboot-crawler:3002
REDIS_URL=redis://taboot-cache:6379
QDRANT_URL=http://taboot-vectors:6333
NEO4J_URI=bolt://taboot-graph:7687
TEI_EMBEDDING_URL=http://taboot-embed:80
RERANKER_URL=http://taboot-rerank:8000
OLLAMA_PORT=11434
```

---

## 11. Code Quality & Testing

### Tools
- **Linter**: Ruff 0.14.0+ (100-char line length)
- **Type checker**: mypy 1.18.2+ (strict mode, no `any`)
- **Test framework**: pytest (markers: unit, integration, slow, source-specific)
- **Coverage**: ≥85% in packages/core + extraction logic

### Test Structure
```
tests/<package>/<module>/test_*.py
```

### Markers
```
unit              # Fast, no dependencies
integration       # Requires Docker services
slow              # >5s
gmail, github, reddit, elasticsearch, firecrawl  # Source-specific
```

---

## 12. Performance Targets (RTX 4070)

| Component | Target |
|-----------|--------|
| Tier A extraction | ≥50 pages/sec |
| Tier B extraction | ≥200 sentences/sec (md) or ≥40 (trf) |
| Tier C LLM | ≤250ms median/window, p95 ≤750ms (batched 8–16) |
| Neo4j writes | ≥20k edges/min (2k-row UNWIND) |
| Qdrant upserts | ≥5k vectors/sec (768-dim) |
| Full retrieval | <3s p95 answer generation |
| Extraction F1 | ≥0.80 (precision-first: ≥0.85 precision, ≥0.75 recall) |

---

## 13. Key Clarifications (From Spec Session)

1. **API Auth**: Bearer Token (JWT) with expiry + refresh mechanics
2. **Neo4j MENTIONS**: Doc → Chunk (direct); no intermediate Section nodes in MVP
3. **Extraction Output**: Buffered in Redis with TTL; atomic Neo4j commits
4. **Service Failures**: Fail-fast with clear error; no fallback modes
5. **Quality Trade-off**: Precision-first (minimize false positives over missed facts)

---

## 14. Next Steps for `/speckit.plan`

When running `/speckit.plan`, provide:

1. **Tech Stack Choices** (confirm these are correct):
   - Python 3.11+ (uv package manager)
   - FastAPI + Uvicorn (API)
   - Typer (CLI)
   - LlamaIndex (retrieval framework)
   - Neo4j 5.23+ (graph DB)
   - Qdrant (vector DB)
   - Redis 7.2 (state + DLQ)
   - PostgreSQL 16 (metadata)
   - spaCy (Tier B NLP)
   - Ollama + Qwen3-4B (Tier C LLM)
   - TEI (embeddings)
   - SentenceTransformers (reranking)

2. **Architecture Patterns** (confirm these are correct):
   - Hexagonal/ports-and-adapters (core + adapters + apps)
   - Strict layering (apps → adapters → core)
   - Framework-agnostic core (no FastAPI/LlamaIndex in core layer)
   - Async task queues (Redis DLQ for extraction failures)
   - Batch writes (2–5k row UNWIND in Neo4j)

3. **Key Decision Points** to confirm:
   - Single Qdrant collection with namespace filtering vs. per-namespace collections?
   - Doc → Chunk direct MENTIONS vs. hierarchical Doc → Section → Chunk?
   - Bearer JWT vs. API key for FastAPI auth?
   - Precision-first vs. balanced F1 for extraction quality?
   - Fail-fast vs. best-effort on service failures?

---

## File Paths (Absolute)

| Component | Path |
|-----------|------|
| Core layer | `/home/jmagar/code/taboot/packages/core/` |
| Ingestion adapter | `/home/jmagar/code/taboot/packages/ingest/` |
| Extraction adapter | `/home/jmagar/code/taboot/packages/extraction/` |
| Graph adapter | `/home/jmagar/code/taboot/packages/graph/` |
| Vector adapter | `/home/jmagar/code/taboot/packages/vector/` |
| Retrieval adapter | `/home/jmagar/code/taboot/packages/retrieval/` |
| Schemas layer | `/home/jmagar/code/taboot/packages/schemas/` |
| Common utilities | `/home/jmagar/code/taboot/packages/common/` |
| FastAPI app | `/home/jmagar/code/taboot/apps/api/` |
| Typer CLI | `/home/jmagar/code/taboot/apps/cli/` |
| MCP server | `/home/jmagar/code/taboot/apps/mcp/` |
| Compose stack | `/home/jmagar/code/taboot/docker-compose.yaml` |
| Configuration | `/home/jmagar/code/taboot/.env.example` |
| Architecture docs | `/home/jmagar/code/taboot/docs/` |

---

**Ready for `/speckit.plan`.**
