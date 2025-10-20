# Implementation Plan: LlamaCrawl v2 — Doc-to-Graph RAG Platform

**Branch**: `001-llamacrawl-v2-rag-platform` | **Date**: 2025-10-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification + TECH_STACK_SUMMARY.md + 5 parallel code-finder investigations + PIPELINE_INVESTIGATION_REPORT.md

**Note**: Greenfield platform build. Architectural design complete; implementation is skeleton (mostly empty `__init__.py` files per PIPELINE_INVESTIGATION_REPORT.md).

## Summary

**LlamaCrawl v2** is a multi-source Doc-to-Graph RAG platform ingesting from 11+ sources (web, GitHub, Reddit, YouTube, Gmail, Elasticsearch, configs), extracting facts via 3-tier pipeline (deterministic → NLP → LLM), storing in Neo4j graph + Qdrant vectors, and retrieving via 6-stage hybrid search with inline citations.

**Primary approach**: Strict hexagonal/ports-and-adapters architecture (apps → adapters → core) ensuring framework-agnostic business logic. GPU-accelerated extraction (≥50 pages/sec Tier A, ≥200 sentences/sec Tier B, ≤250ms/window Tier C). End-to-end retrieval <3s p95.

## Technical Context

**Language/Version**: Python 3.11+ (uv package manager)
**Primary Dependencies**: FastAPI 0.119.0+, Typer 0.15.1+, LlamaIndex (11 packages for retrieval), Neo4j 5.26, Qdrant 1.15.1+, Redis 5.0.1+, spaCy 3.8.1+, Ollama + Qwen3-4B-Instruct
**Storage**: Neo4j 5.23+ (property graph), Qdrant (1024-dim vectors, HNSW GPU), Redis 7.2 (state/DLQ/cache), PostgreSQL 16 (Firecrawl metadata), Docker volumes (persistent)
**Testing**: pytest (markers: unit, integration, slow, source-specific), mypy strict mode, Ruff (linter/formatter), ≥85% coverage in packages/core + extraction logic
**Target Platform**: Linux server (RTX 4070+ GPU for training/inference), deployed via docker-compose or Kubernetes
**Project Type**: Multi-package monorepo (7 adapter packages + 3 app shells + core layer)
**Performance Goals**: Tier A ≥50 pages/sec, Tier B ≥200 sentences/sec, Tier C ≤250ms/window, Neo4j ≥20k edges/min, Qdrant ≥5k vectors/sec, E2E retrieval <3s p95
**Constraints**: Fail-fast on external service failures (no fallback modes), precision-first extraction (≥0.85 precision, ≥0.75 recall), deterministic Tier A parsing, idempotent Neo4j writes (2–5k row UNWIND batches)
**Scale/Scope**: 11+ ingestion sources, 3-tier extraction pipeline, 11 Neo4j node types + 11 relationships, 1024-dim embeddings, 6-stage retrieval, 15+ API endpoints, full CLI command suite

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

✅ **PASS**: No pre-production violations. All constraints documented:
- **Type Safety**: Strict mypy, no `any` types (constitution principle I) ✓
- **Error Handling**: Fail-fast, no fallbacks (constitution principle II) ✓
- **TDD**: ≥85% coverage in core + extraction (constitution principle III) ✓
- **Layered Architecture**: Strict apps → adapters → core (constitution principle IV) ✓
- **Performance Targets**: Quantified for all tiers (constitution principle V) ✓
- **Framework Isolation**: Core has zero framework deps (constitution principle VI) ✓
- **Observability**: Metrics, tracing, F1 validation (constitution principle VII) ✓
- **Extraction Contracts**: Tier A/B/C invariants (constitution principle VIII) ✓

## Project Structure

### Documentation (this feature)

```
.specify/specs/001-llamacrawl-v2-rag-platform/
├── spec.md                         # Feature specification (completed)
├── TECH_STACK_SUMMARY.md           # Technical context investigation (completed)
├── PIPELINE_INVESTIGATION_REPORT.md # Maturity assessment (completed)
├── PIPELINE_MATURITY_SUMMARY.md    # Implementation status (completed)
├── INVESTIGATION_INDEX.md           # Investigation metadata (completed)
├── checklists/
│   └── requirements.md              # Quality checklist (completed)
├── plan.md                          # This file (implementation plan)
├── research.md                      # Phase 0 output (to be generated)
├── data-model.md                    # Phase 1 output (to be generated)
├── quickstart.md                    # Phase 1 output (to be generated)
├── contracts/                       # Phase 1 output (to be generated)
│   ├── neo4j-schema.cypher
│   ├── qdrant-collection.json
│   ├── extraction-tier-schemas.json
│   └── api-openapi.yaml
└── tasks.md                         # Phase 2 output (generated via /speckit.tasks, already complete)
```

### Source Code (repository root - Multi-package Monorepo)

```
/home/jmagar/code/taboot/

packages/
├── core/                # Business logic, use-cases, ports (framework-agnostic)
│   ├── entities/        # Domain models (Document, Entity, Relation, Graph)
│   ├── value_objects/   # Immutable value objects (ChunkId, ServiceName, IPAddress)
│   ├── use_cases/       # Application services (IngestWeb, ExtractFromDoc, QueryGraph)
│   ├── ports/           # Adapter interfaces (IngestPort, ExtractorPort, GraphWriterPort)
│   └── services/        # Domain services (entity resolution, caching strategies)
├── schemas/             # Pydantic DTOs, OpenAPI
│   ├── models/          # Entity models (Document, Chunk, Triple, Service, Host, IP, Endpoint)
│   ├── validators/      # Shared validators
│   ├── jsonschema/      # Generated schemas
│   └── openapi/         # OpenAPI fragments
├── common/              # Logging, config, observability
│   ├── logging/         # JSON structured logging (python-json-logger)
│   ├── config/          # Environment/config loaders (112 env vars)
│   ├── observability/   # Metrics, tracing (windows/sec, tier hits, LLM p95, cache hit-rate)
│   └── utils/           # Utilities
├── ingest/              # Firecrawl, normalization, chunking (STATUS: 0% per investigation)
│   ├── sources/         # Source-specific clients (web, github, reddit, youtube, gmail, elasticsearch, compose, swag, tailscale, unifi, ai-sessions)
│   ├── normalizers/     # HTML/markdown normalization (HTML→MD, boilerplate removal)
│   ├── chunkers/        # Token-based, markdown-aware, code-aware chunking (≤512 tokens, with overlap)
│   ├── services/        # Orchestration (queues, retries, rate limiting, backpressure)
│   └── utils/           # Helpers (provenance metadata, deduplication)
├── extraction/          # Tier A/B/C extractors (STATUS: 0% per investigation)
│   ├── tier_a/          # Deterministic (regex, YAML/JSON parsing, Aho-Corasick for known services/IPs/hosts, ≥50 pages/sec CPU)
│   ├── tier_b/          # spaCy NLP (entity ruler + dependency matchers + sentence classifier on en_core_web_md or trf, ≥200 sentences/sec md)
│   ├── tier_c/          # LLM windows (Qwen3-4B-Instruct via Ollama, ≤512-token windows, temperature=0, JSON schema, batched 8–16, median ≤250ms, p95 ≤750ms)
│   ├── pipelines/       # Tier orchestration (A→B→C flow)
│   ├── services/        # Queueing (Redis DLQ), caching (SHA-256 window hash), entity resolution
│   └── utils/           # Helpers
├── graph/               # Neo4j adapter (STATUS: 0% per investigation)
│   ├── client/          # Driver setup, session management
│   ├── writers/         # Batched UNWIND logic (2–5k rows, ≥20k edges/min, idempotent MERGE)
│   ├── queries/         # Cypher query builders
│   ├── migrations/      # Schema setup (idempotent, 14 constraints/indexes)
│   ├── docs/
│   │   └── GRAPH_SCHEMA.md  # 11 node labels + 11 relationships with properties
│   └── utils/           # Serialization, retry logic
├── vector/              # Qdrant adapter (STATUS: 0% per investigation)
│   ├── client/          # Qdrant client, session management
│   ├── writers/         # Upsert/delete pipelines (≥5k vectors/sec, 1024-dim HNSW GPU, deduplication by sha256+namespace)
│   ├── queries/         # Vector search helpers (top-k, metadata filters)
│   ├── migrations/      # Collection/index management (taboot.documents collection, Cosine similarity)
│   ├── docs/
│   │   └── VECTOR_SCHEMA.md # 15 payload fields (doc_id, chunk_id, namespace, url, title, source, job_id, sha256, mime, lang, chunk_index, text_len, created_at, updated_at, tags)
│   └── utils/           # Payload shaping, filters
└── retrieval/           # LlamaIndex adapter (STATUS: 0% per investigation)
    ├── context/         # Settings (TEI embeddings, Ollama LLM), prompts
    ├── indices/         # VectorStoreIndex (Qdrant) + PropertyGraphIndex (Neo4jPGStore)
    ├── retrievers/      # Hybrid retriever (6-stage: embed → filter → search → rerank → traverse → synthesize), post-processors, reranking (BAAI/bge-reranker-v2-m3)
    ├── query_engines/   # QA engine with inline citations + bibliography, graph-augmented synthesis
    ├── services/        # Routing, caching, citation builders (inline numeric [1][2] + source list)
    └── utils/           # Shared utilities

apps/
├── api/                 # FastAPI HTTP service (STATUS: 0% per investigation, only health stub)
│   ├── routes/          # Route modules (jobs, ingestions, crawl, sessions, graph, query) - 15+ endpoints
│   ├── deps/            # Dependency injection (Bearer JWT auth with expiry/refresh, sessions, error handling)
│   ├── schemas/         # Request/response DTOs (via packages/schemas)
│   ├── services/        # Adapter instantiation
│   ├── docs/            # API documentation
│   │   ├── API.md
│   │   ├── JOB_LIFECYCLE.md
│   │   ├── OBSERVABILITY.md
│   │   ├── SECURITY_MODEL.md
│   │   └── BACKPRESSURE_RATELIMITING.md
│   └── app.py           # Main FastAPI app (currently minimal stub per investigation)
├── cli/                 # Typer CLI (STATUS: 0% per investigation)
│   ├── commands/        # Command families (ingest web/compose/github/reddit/youtube/gmail, extract pending/reprocess, query, graph query, status, init)
│   ├── services/        # Shared utilities (prompting, formatters)
│   ├── deps/            # Shared dependencies
│   └── main.py          # Typer app entry point
└── mcp/                 # MCP server adapter (STATUS: 0% per investigation)
    ├── handlers/        # MCP request handlers
    ├── schemas/         # MCP-specific schemas
    └── server.py        # MCP server entry point

docker/
├── app/                 # FastAPI container (Python 3.13-slim multi-stage)
├── worker/              # Extraction worker (Python 3.13-slim)
├── reranker/            # SentenceTransformers reranker (PyTorch CUDA)
├── neo4j/               # Neo4j 5.23 with APOC
└── postgres/            # PostgreSQL 16

tests/
├── unit/                # Fast unit tests (no dependencies, target ≥85% in core + extraction)
│   ├── packages/        # mirrors packages/
│   └── apps/            # mirrors apps/
├── integration/         # Integration tests (requires Docker services healthy)
├── contract/            # Contract/schema tests (Neo4j constraints, Qdrant collection, API OpenAPI)
└── conftest.py          # pytest fixtures

docs/
├── ARCHITECTURE.md      # Platform architecture overview (complete per investigation)
├── EVALUATION_PLAN.md   # Retrieval metrics, F1 gates, CI pipeline
├── CONFIGURATION.md     # All 112 env vars documented
├── SECURITY_MODEL.md    # Auth, SSRF, secrets management
├── DATA_GOVERNANCE.md   # Retention, erasure, audit trails
└── MAKEFILE_REFERENCES.md # Automation targets

.github/workflows/
├── test.yml             # Lint, type-check, unit tests, integration tests
├── build.yml            # Docker image build, scan, push
└── deploy.yml           # (Optional) Staging/production deployment

docker-compose.yaml      # 11 services (4 GPU: taboot-vectors, taboot-embed, taboot-rerank, taboot-ollama; 7 CPU: taboot-graph, taboot-cache, taboot-db, taboot-playwright, taboot-crawler, taboot-app, taboot-worker)
.env.example             # 112 configuration variables (Firecrawl, Neo4j, Qdrant, Redis, PostgreSQL, TEI, Reranker, Ollama, source credentials)
pyproject.toml           # Workspace config (uv managed, 10 packages)
pnpm-workspace.yaml      # (For web frontend, optional)
Makefile                 # Development shortcuts (sync, test, lint, format, run)
```

**Structure Decision**: Multi-package monorepo with strict layering enforces framework-agnostic core. Adapters (ingest, extraction, graph, vector, retrieval) implement ports from core. Apps (api, cli, mcp) are thin I/O shells calling core use-cases. This enables independent testing, debugging, and swapping of components. Per PIPELINE_INVESTIGATION_REPORT, all packages currently contain only empty `__init__.py` files (0% implementation).

## Complexity Tracking

*No violations. All constraints met. Pre-production status allows liberal refactoring without backward compatibility constraints.*

---

## Phase 0: Research (To Be Generated)

Research tasks will consolidate existing investigations and resolve remaining unknowns:

1. **LlamaIndex integration patterns** — VectorStoreIndex + PropertyGraphIndex with Neo4j + Qdrant
2. **spaCy extraction patterns** — Entity ruler + dependency matchers for Tier B entity recognition
3. **Redis DLQ patterns** — Dead-letter queue implementation for extraction failures with TTL cleanup
4. **Qdrant hybrid search** — Namespace filtering + metadata payload schema + HNSW GPU tuning
5. **Neo4j batch write patterns** — UNWIND performance tuning (2–5k rows), deadlock retry strategies, idempotent MERGE
6. **TEI embedding integration** — GPU acceleration, batch sizing, 1024-dim Qwen3-Embedding-0.6B tokenization
7. **Citation builder patterns** — Provenance chain from triples to inline numeric citations + bibliography
8. **Ollama LLM integration** — Qwen3-4B-Instruct JSON schema enforcement, temperature=0, batched 8–16 windows

Research output: `research.md` (consolidates TECH_STACK_SUMMARY + PIPELINE_INVESTIGATION_REPORT findings with decisions + rationale)

---

## Phase 1: Design & Contracts (To Be Generated)

### 1. Data Model (`data-model.md`)
- **Neo4j schema**: 11 node types (Host, Container, Service, Endpoint, Network, User, Credential, Repository, Package, Document, IP)
- **11 relationship types** with properties (RUNS, EXPOSES, BINDS_TO, RESOLVES_TO, CONTAINS, DEPENDS_ON, ROUTES_TO, USES_CREDENTIAL, BUILDS, MENTIONS, RUNS_IN)
- **14 constraints/indexes**: Unique constraints on Service.name, Host.hostname; composite index on Endpoint(service, method, path)
- **Qdrant payload schema**: 15 fields (keyword: doc_id, chunk_id, namespace, url, title, source, job_id, sha256, mime, lang; numeric: chunk_index, text_len; datetime: created_at, updated_at; array: tags)
- **State transitions** for jobs (queued → running → {succeeded|failed|canceled})

### 2. API Contracts (`contracts/api-openapi.yaml`)
- **15+ endpoints**: health, jobs (firecrawl, detail, cancel, purge), ingestions (create, list, detail, cancel), crawl:sync, sessions (active, force-close), graph query, query
- **Request/response schemas** with examples
- **Error codes**: E_URL_BAD, E_ROBOTS, E_403_WAF, E_429_RATE, E_5XX_ORIGIN, E_PARSE, E_TIMEOUT, E_BROWSER, E_QDRANT, E_NEO4J, E_GPU_OOM
- **Bearer JWT authentication** with expiry + refresh mechanics

### 3. Storage Contracts
- **Neo4j**: `contracts/neo4j-schema.cypher` (constraints, indexes, sample MERGE/CREATE statements)
- **Qdrant**: `contracts/qdrant-collection.json` (collection config with HNSW tuning: m=32, ef_construct=128, full_scan_threshold=10000, payload schema)
- **Extraction tiers**: `contracts/extraction-tier-schemas.json` (Tier A/B/C JSON output formats with provenance fields)

### 4. Quick Start (`quickstart.md`)
- Development setup (uv sync, docker compose up, taboot init)
- First-run workflow (ingest URL → extract → query)
- Testing a single pipeline tier (Tier A deterministic parsing example)
- Debugging checklist (service health, logs, Neo4j queries, Qdrant searches)

### 5. Agent Context Update
- Run `.specify/scripts/bash/update-agent-context.sh claude`
- Update Claude Code agent context with new tech stack from this plan
- Preserve manual configuration between markers

---

## Phase 2: Tasks (Generated via `/speckit.tasks`)

tasks.md already generated with 185 tasks across 13 phases organized by user story (US1-US10).

**MVP Scope** (P1 only): Setup + Foundational + US1 (System Init) + US2 (Web Ingestion) + US3 (Deterministic Extraction) = 76 tasks

---

## Key Implementation Notes

### Architecture Principles
- **Core is framework-agnostic**: No FastAPI, LlamaIndex, or framework-specific imports in packages/core
- **Ports-and-adapters pattern**: Adapters (ingest, extraction, graph, vector, retrieval) implement ports from core; swappable
- **Fail-fast**: No fallback modes; external service failures (Firecrawl, TEI, Neo4j, Ollama, Qdrant) stop execution immediately with clear error
- **Precision-first extraction**: Target ≥0.85 precision, ≥0.75 recall (false positives > false negatives for infrastructure graphs)
- **Deterministic Tier A**: Byte-identical outputs for configs; enables reproducible caching
- **Async extraction plane**: Decoupled from ingestion via Redis queues; enables backpressure, DLQ, and reprocessing

### Performance Targets (RTX 4070)
| Component | Target | Notes |
|-----------|--------|-------|
| Tier A | ≥50 pages/sec | CPU-bound, deterministic (regex, JSON/YAML, Aho-Corasick) |
| Tier B | ≥200 sentences/sec (md), ≥40 (trf) | GPU-optional, spaCy NLP |
| Tier C | ≤250ms/window median, p95 ≤750ms | Batched 8–16, Ollama Qwen3-4B-Instruct, Redis cache |
| Neo4j | ≥20k edges/min | 2k-row UNWIND, deadlock retry, idempotent MERGE |
| Qdrant | ≥5k vectors/sec | 1024-dim HNSW GPU, batched upserts |
| Retrieval | <3s p95 | Embed + search + rerank + graph + synthesis |
| F1 Score | ≥0.80 (precision ≥0.85, recall ≥0.75) | On ~300 labeled windows, CI gate: fail if drop ≥2 points |

### Storage Configuration
- **Neo4j**: Bolt 7687, HTTP 7474, single-node (HA optional), APOC plugin for graph algorithms
- **Qdrant**: HTTP 6333 (→7000 external), gRPC 6334 (→7001), GPU-accelerated HNSW, 1024-dim Cosine, 4 shards
- **Redis**: 6379, RDB + AOF persistence, DLQ (sorted sets) + cache (SHA-256 keys) + state (job metadata)
- **PostgreSQL**: 5432, Firecrawl metadata, JDBC driver
- **Volumes**: Persistent for all; Docker volumes or k8s PVCs in production

### Testing Strategy
- **Unit tests** (≥85% coverage in core + extraction): Fast, no dependencies, mirrors packages/ structure
- **Integration tests**: Require Docker services, test end-to-end pipelines (ingest → extract → query)
- **Markers**: unit, integration, slow, gmail, github, reddit, elasticsearch, firecrawl (source-specific)
- **CI gates**: Lint (Ruff), type-check (mypy strict), test pass, coverage ≥85%, F1 ≥0.80 (extraction quality on labeled data)
- **Benchmarks**: Performance regression tests (<5% drop blocks merge)

---

## Next Steps

1. **Run Phase 0 research** (consolidate investigations):
   ```bash
   # Generate research.md from TECH_STACK_SUMMARY + PIPELINE_INVESTIGATION_REPORT
   # Output: research.md with all decisions + rationale + alternatives
   ```

2. **Run Phase 1 design** (generate contracts):
   ```bash
   # Generate data-model.md, contracts/, quickstart.md
   # Update agent context via update-agent-context.sh
   ```

3. **Phase 2 tasks** (already generated):
   ```bash
   # tasks.md complete with 185 tasks, dependency graph, parallel execution examples
   # MVP: 76 tasks (Setup + Foundational + US1-US3)
   ```

4. **Proceed to implementation**:
   - Team coordination on parallel task execution (US1-US3 can run concurrently after Foundational phase)
   - Continuous testing and integration (TDD: Red-Green-Refactor for all new code)
   - Performance benchmarking against RTX 4070 baselines

---

**Status**: ✅ READY FOR PHASE 0 RESEARCH

This plan provides:
- ✅ Complete technical context (Python 3.11+, FastAPI, LlamaIndex, Neo4j, Qdrant, spaCy, Ollama, etc.)
- ✅ Detailed project structure (10-package monorepo, 11-service Docker stack, strict layering)
- ✅ Clear performance targets and constraints (quantified for all tiers)
- ✅ Constitution compliance verification (all 8 principles met)
- ✅ Research agenda for Phase 0 (consolidate existing investigations)
- ✅ Design artifacts for Phase 1 (data-model, contracts, quickstart)
- ✅ Task decomposition complete (tasks.md with 185 atomic tasks organized by user story)

All artifacts ready for Phase 0 research generation and Phase 1 design contract generation.
