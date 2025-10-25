# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

> **⚠️ Single-User System**: Taboot is designed for a single developer. Breaking changes are acceptable and expected. No backwards compatibility guarantees. When in doubt, wipe and rebuild databases. No need for multiple environments, migration guides, or CONTRIBUTING/SECURITY docs.

Taboot is a **Doc-to-Graph RAG platform** built on LlamaIndex, Firecrawl, Neo4j, and Qdrant. It ingests from 11+ sources (web, GitHub, Reddit, YouTube, Gmail, Elasticsearch, Docker Compose, SWAG, Tailscale, Unifi, AI sessions), converts technical docs/configs into a Neo4j property graph, stores chunks in Qdrant, and answers questions via hybrid retrieval with strict source attribution.

**Key Technologies:**
- Python 3.11+ (managed via `uv`)
- Neo4j 5.23+ (graph database)
- Qdrant (vector database with GPU acceleration)
- LlamaIndex (retrieval framework)
- Firecrawl (web crawling)
- spaCy (NLP extraction) + Qwen3-4B-Instruct (Ollama LLM)
- TEI (embeddings and reranking)
- FastAPI + Typer CLI (app shells)

## Architecture: The Core Layering

**Strict Dependency Flow:** `apps → adapters → core`

**`packages/core/`** — Orchestration logic, domain models, and interfaces. **No framework dependencies.** This is the business truth. Core depends only on `packages/schemas` and `packages/common`.

**Adapter packages** — Pluggable implementations:
- `packages/ingest/` — Firecrawl readers, normalizer, chunker, deterministic code/table parsers
- `packages/extraction/` — Multi-tier extraction engine (Tier A: regex/JSON; Tier B: spaCy; Tier C: LLM windows)
- `packages/graph/` — Neo4j driver, Cypher builders, bulk UNWIND writers
- `packages/vector/` — Qdrant client, hybrid search, reranking
- `packages/retrieval/` — LlamaIndex indices, retrievers, and query engines
- `packages/schemas/` — Pydantic models and OpenAPI schemas
- `packages/common/` — Logging, config, tracing, utilities

**App shells** — Thin I/O layers:
- `apps/api/` — FastAPI service (HTTP)
- `apps/cli/` — Typer CLI (TUI)
- `apps/mcp/` — MCP server protocol adapter
- `apps/web/` — Next.js dashboard (optional)

**Key Rule:** Apps never contain business logic. If an app needs to do something, move it to an adapter or core as a new use-case.

## Data Pipeline Architecture

### Ingestion Plane
Firecrawl + Playwright → Normalizer (de-boilerplate) → Chunker → TEI embeddings (GPU) → Qdrant upserts. Structured sources (Docker Compose, SWAG, Tailscale, Unifi) parsed deterministically to nodes/edges.

### Extraction Plane (Async, Decoupled)

1. **Tier A (Deterministic):** Regex, YAML/JSON parsing, Aho-Corasick for known services/IPs/hosts. Target ≥50 pages/sec (CPU).
1. **Tier B (spaCy):** Entity ruler + dependency matchers + sentence classifier on `en_core_web_md` (or `trf` for prose). Target ≥200 sentences/sec (md).
1. **Tier C (LLM Windows):** Qwen3-4B-Instruct (Ollama) on ≤512-token windows, temperature 0, JSON schema, batched 8–16, Redis cache. Target median ≤250ms/window.

### Retrieval Plane (6-Stage)

1. Query embedding (TEI) → 2. Metadata filter (source, date) → 3. Vector search (Qdrant, top-k) → 4. Rerank (Qwen/Qwen3-Reranker-0.6B) → 5. Graph traversal (≤2 hops Neo4j) → 6. Synthesis (Qwen3-4B) with inline citations + source list.

## Neo4j Graph Model

**Nodes:** `Service{name}`, `Host{hostname}`, `IP{addr}`, `Proxy{name}`, `Endpoint{service,method,path}`, `Doc{doc_id}`

**Edges:** `DEPENDS_ON`, `ROUTES_TO{host,path,tls}`, `BINDS{port,protocol}`, `RUNS{container_id}`, `EXPOSES_ENDPOINT{auth}`, `MENTIONS{span,section,hash}`

**Constraints:** Unique indexes on `Service.name` and `Host.hostname`; composite index on `Endpoint(service, method, path)`.

## Essential Development Commands

### Setup (First Time)
```bash
uv sync                               # install Python workspace deps
pnpm install                          # JS dependencies (web + codegen)
cp .env.example .env && $EDITOR .env # configure endpoints
docker compose up -d                  # start all services
uv run apps/cli init                  # initialize schema and collections
```

### Development Loop
```bash
uv run apps/cli --help                              # list workflows
uv run apps/cli ingest web https://example.com     # ingest a single URL
uv run apps/cli extract pending                     # run extraction worker
uv run apps/cli query "your question"               # test retrieval

uv run pytest -m "not slow"                         # fast unit tests
uv run pytest -m "integration" --tb=short           # integration tests
uv run pytest --cov=packages packages/core          # coverage: core layer

uv run ruff check . && uv run ruff format .         # lint and format
uv run mypy .                                       # strict type-check
```

### Running Services
```bash
# Start API (via Docker only - no CLI entry point)
docker compose up taboot-app

# View logs
docker compose logs -f <service-name>

# Health check
docker compose ps
```

### Debugging
```bash
# Direct Neo4j queries
uv run apps/cli graph query "MATCH (s:Service) RETURN s LIMIT 10"

# View extraction metadata (Redis)
uv run apps/cli status

# Reprocess docs with new extractor
uv run apps/cli extract reprocess --since 7d
```

## Code Style & Conventions

- **Line length:** 100 characters (enforced by Ruff)
- **Python naming:** modules `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`
- **Adapters:** Name for their system (`neo4j_writer.py`, `qdrant_client.py`)
- **Type hints:** All functions annotated; mypy strict mode enabled; never use bare `any` type
- **Error handling:** Throw errors early and often; pre-production codebase, no fallbacks
- **Imports:** Ruff auto-formats; respect layering rules (no reverse imports)

## Testing

- Tests mirror `tests/<package>/<module>/test_*.py` structure
- Markers: `unit`, `integration`, `slow`, `gmail`, `github`, `reddit`, `elasticsearch`, `firecrawl`
- Target: ≥85% coverage in `packages/core` and extraction logic
- Full integration tests require Docker services healthy
- Lightweight fixtures over static payloads

## Framework Integration Notes

**LlamaIndex:** Used across multiple adapter packages:
- `packages/ingest/` — LlamaIndex readers (web, GitHub, Reddit, YouTube, Gmail, file formats)
- `packages/extraction/` — LLM adapters (`llama-index-llms-ollama`) for Tier C extraction
- `packages/vector/` — VectorStoreIndex integration with Qdrant
- `packages/graph/` — PropertyGraphIndex integration with Neo4j
- `packages/retrieval/` — Core retrieval functionality:
  - `context/` — Settings (TEI, Ollama LLM), prompts
  - `indices/` — Index management and configuration
  - `retrievers/` — Hybrid retrievers and reranking
  - `query_engines/` — Graph-augmented QA

**Core never imports `llama_index.*`.** This ensures core is framework-agnostic. Core uses direct imports from adapter packages (`packages.graph`, `packages.vector`, etc.) when needed in use-cases.

## Docker Services & GPU

All services in `docker-compose.yaml`:

| Service | Purpose | GPU |
|---------|---------|-----|
| `taboot-vectors` | Qdrant (HNSW indexing) | ✅ |
| `taboot-embed` | TEI embeddings (Qwen3-Embedding-0.6B) | ✅ |
| `taboot-rerank` | SentenceTransformers Qwen3 reranker | ✅ |
| `taboot-ollama` | Ollama LLM server (Qwen3-4B-Instruct) | ✅ |
| `taboot-graph` | Neo4j 5.23+ with APOC | ❌ |
| `taboot-cache` | Redis 7.2 (state, cursors, DLQ) | ❌ |
| `taboot-db` | PostgreSQL 16 (Firecrawl metadata) | ❌ |
| `taboot-playwright` | Playwright browser microservice | ❌ |
| `taboot-crawler` | Firecrawl v2 API | ❌ |
| `taboot-app` | Unified API (8000) + MCP + Next.js Web (3000) | ❌ |
| `taboot-worker` | Extraction worker (spaCy tiers + LLM windows) | ❌ |

**taboot-app Details:**
- Runs both FastAPI (port 8000) and Next.js web dashboard (port 3000)
- Managed via supervisord for process orchestration
- Includes Python (uv/FastAPI) and Node.js (pnpm/Next.js) runtimes
- Web app includes auth (Prisma), UI components (shadcn/ui), and dashboard

**GPU Notes:** Requires NVIDIA driver + `nvidia-container-toolkit`. Model downloads (Ollama, spaCy) happen on first run; pull sizes may exceed 20GB total.

## Configuration

Primary config via `.env` (copy from `.env.example`). Key variables align with `docker-compose.yaml` defaults:

```env
FIRECRAWL_API_URL=http://taboot-crawler:3002
REDIS_URL=redis://taboot-cache:6379
QDRANT_URL=http://taboot-vectors:6333
NEO4J_URI=bolt://taboot-graph:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=changeme
TEI_EMBEDDING_URL=http://taboot-embed:80
RERANKER_URL=http://taboot-rerank:8000
RERANKER_MODEL=Qwen/Qwen3-Reranker-0.6B
RERANKER_BATCH_SIZE=16
RERANKER_DEVICE=auto
OLLAMA_PORT=11434
LLAMACRAWL_API_URL=http://localhost:8000
```

Per-source credentials (GitHub, Reddit, Gmail, Elasticsearch, Unifi, Tailscale) documented in `docs/`.

## Schema Management

**PostgreSQL:**
- Source of truth: `specs/001-taboot-rag-platform/contracts/postgresql-schema.sql`
- No automated migrations (Alembic removed)
- Manual versioning via version comment in SQL file
- Breaking changes OK: wipe and rebuild with `docker volume rm taboot-db`
- Schema created during `taboot init` via `packages.common.db_schema.create_schema()`

**Neo4j:**
- Constraints: `specs/001-taboot-rag-platform/contracts/neo4j-constraints.cypher`
- Applied idempotently during `taboot init`
- No versioning needed (idempotent CREATE IF NOT EXISTS)

**Qdrant:**
- Collections created on-demand during `taboot init`
- Config: `specs/001-taboot-rag-platform/contracts/qdrant-collection.json`
- Versioning via aliases (managed by application)

**Prisma (TypeScript/Next.js Auth):**
- Schema: `packages-ts/db/prisma/schema.prisma`
- Separate concern from Python RAG platform
- Manages: User, Session, Account, Verification, TwoFactor tables
- Migrations: `pnpm db:migrate` in packages-ts/db

## Performance Targets (RTX 4070)

- Tier A: ≥50 pages/sec (CPU)
- Tier B: ≥200 sentences/sec (md model) or ≥40 (transformer model)
- Tier C: median ≤250ms/window, p95 ≤750ms (batched 8–16)
- Neo4j: ≥20k edges/min with 2k-row UNWIND batches
- Qdrant: ≥5k vectors/sec (1024-dim, HNSW)

## Observability

- **Metrics:** windows/sec, tier hit ratios, LLM p95, cache hit-rate, DB throughput
- **Tracing:** Chain `doc_id → section → windows → triples → Neo4j txId`
- **Validation:** ~300 labeled windows with F1 guardrails; CI fails if F1 drops ≥2 points
- **Logging:** JSON structured via `python-json-logger`

## Troubleshooting

| Issue | Check |
|-------|-------|
| Services won't start | `docker compose ps` and `docker compose logs <service-name>` |
| GPU not detected | NVIDIA driver + `nvidia-container-toolkit` installed |
| Ollama model missing | First run auto-pulls Qwen3-4B; or `docker exec taboot-ollama ollama pull qwen3:4b` |
| Neo4j connection refused | Wait for healthcheck: `docker compose ps taboot-graph` |
| Tests fail | Ensure `docker compose ps` shows all services healthy before running integration tests |
| spaCy model missing | First run auto-downloads `en_core_web_md`; or manually `python -m spacy download en_core_web_md` |

## Commits & PRs

- Use Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`
- Keep commits focused on a single concern
- Note executed test command in PR body
- Request reviewers for cross-layer work (core + adapters)
- Link related issues or docs
