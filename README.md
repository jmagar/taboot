# Taboot — Doc-to-Graph RAG Platform

> **Single-User System**: Taboot is designed for a single developer. Breaking changes are acceptable and expected. No backwards compatibility guarantees. When in doubt, wipe and rebuild databases.

A clean-slate, production-minded foundation for multi-source RAG with a **shared business core**, pluggable adapters (ingest, extraction, vector, graph, retrieval), and thin app shells (API, CLI, MCP, Web). Taboot ingests from 11+ sources, converts technical docs/configs into a **Neo4j property graph**, stores chunks in **Qdrant**, and answers questions via **hybrid retrieval** (vector → rerank → graph traversal → synthesis) with strict **source attribution**.

---

## Key Features

* **11+ Ingestion Sources**: Web, GitHub, Reddit, YouTube, Gmail, Elasticsearch, Docker Compose, SWAG, Tailscale, Unifi, AI sessions
* **Multi-Tier Extraction**: Tier A (regex/JSON), Tier B (spaCy NLP), Tier C (Qwen3-4B LLM)
* **Hybrid Retrieval**: Vector search → Reranking → Graph traversal → LLM synthesis
* **Strict Architecture**: `apps → adapters → core` with framework-agnostic business logic
* **GPU Accelerated**: TEI embeddings, Qwen reranker, Ollama LLM on NVIDIA GPUs
* **Source Attribution**: Every answer includes inline citations with source links

---

## Quick Start

### Prerequisites

- Docker with Compose V2 + nvidia-container-toolkit
- NVIDIA GPU (RTX 4070 or equivalent, 12GB+ VRAM)
- Python 3.11+ (managed via `uv`)
- 16GB+ RAM, 50GB+ disk space

### Setup (5 minutes)

```bash
# 1. Clone and install dependencies
git clone https://github.com/yourusername/taboot.git
cd taboot
uv sync

# 2. Configure environment
cp .env.example .env
# Edit .env if needed (defaults work for local development)

# 3. Start all services (Neo4j, Qdrant, Redis, TEI, Ollama, etc.)
docker compose up -d

# 4. Initialize database schemas
uv run apps/cli init
```

### Example Workflow

```bash
# Ingest documentation
uv run apps/cli ingest web https://docs.python.org --limit 20

# Extract knowledge graph
uv run apps/cli extract pending

# Query with natural language
uv run apps/cli query "What are Python decorators?"

# List ingested documents
uv run apps/cli list documents --limit 10

# Check system status
uv run apps/cli extract status
```

See [quickstart.md](specs/001-taboot-rag-platform/quickstart.md) for detailed workflows and troubleshooting.

---

## Repository Layout (no `src/` directories)

```
.
├── apps/
│   ├── api/          # FastAPI service
│   ├── cli/          # Typer CLI
│   ├── mcp/          # MCP server
│   └── web/          # Next.js dashboard (optional)
├── packages/
│   ├── core/         # Business layer: domain models, use-cases, ports (no framework deps)
│   ├── ingest/       # Firecrawl readers, normalizer, chunker, deterministic code/table parsers
│   ├── extraction/   # Tier A/B/C: spaCy, matchers, Qwen (Ollama), JSON schemas
│   ├── graph/        # Neo4j adapter: drivers, Cypher, bulk UNWIND writers
│   ├── vector/       # Qdrant adapter: collections, HNSW config, hybrid search
│   ├── retrieval/    # LlamaIndex adapters: indices (Vector/PropertyGraph), retrievers, query engines
│   ├── schemas/      # Pydantic models, JSON Schema, OpenAPI source
│   ├── clients/      # Generated API clients (TS + Py) from OpenAPI/JSON Schema
│   └── common/       # Logging, config, tracing, utilities
├── docker/           # Dockerfiles (neo4j, postgres, app)
│   ├── neo4j/
│   ├── postgres/
│   └── taboot/
├── docs/             # Setup, configuration, architecture, runbooks, ADRs
├── .github/workflows/ # CI pipelines
├── docker-compose.yml
├── .env.example
├── pyproject.toml
├── package.json
├── pnpm-workspace.yaml
├── turbo.json
├── uv.lock
├── .pre-commit-config.yaml
└── .editorconfig
```

### Layering rules

* **apps → adapters → core**. Apps never contain business logic.
* **core** depends only on `packages/schemas` and `packages/common`.
* Enforced via `import-linter` (Python) and `eslint-plugin-boundaries` (TS).

---

## Documentation Map

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Platform architecture overview.
- [docs/EVALUATION_PLAN.md](docs/EVALUATION_PLAN.md) — Retrieval datasets, metrics, and CI gates.
- [apps/api/docs/API.md](apps/api/docs/API.md) — FastAPI resources and schemas.
- [apps/api/docs/API_EXAMPLES.md](apps/api/docs/API_EXAMPLES.md) — cURL and Python request samples.
- [apps/api/docs/JOB_LIFECYCLE.md](apps/api/docs/JOB_LIFECYCLE.md) — Crawl and ingestion state machine.
- [apps/api/docs/RUNBOOK.md](apps/api/docs/RUNBOOK.md) — Incident response and restart playbook.
- [apps/api/docs/OBSERVABILITY.md](apps/api/docs/OBSERVABILITY.md) — Logging, metrics, and tracing guidance.
- [apps/api/docs/BACKPRESSURE_RATELIMITING.md](apps/api/docs/BACKPRESSURE_RATELIMITING.md) — Concurrency and throttling policies.
- [apps/api/docs/SECURITY_MODEL.md](apps/api/docs/SECURITY_MODEL.md) — Threat model and hardening checklist.
- [apps/api/docs/DATA_GOVERNANCE.md](apps/api/docs/DATA_GOVERNANCE.md) — Retention and erasure procedures.
- [apps/api/docs/MIGRATIONS.md](apps/api/docs/MIGRATIONS.md) — Neo4j and Qdrant migration workflow.
- [packages/extraction/docs/EXTRACTION_SPEC.md](packages/extraction/docs/EXTRACTION_SPEC.md) — Tiered extractor implementation guide.
- [packages/vector/docs/VECTOR_SCHEMA.md](packages/vector/docs/VECTOR_SCHEMA.md) — Qdrant payload schema and tuning knobs.
- [packages/graph/docs/GRAPH_SCHEMA.md](packages/graph/docs/GRAPH_SCHEMA.md) — Node labels and Cypher upsert patterns.
- [docs/MAKEFILE_REFERENCES.md](docs/MAKEFILE_REFERENCES.md) — Automation targets for local tooling.
- [docs/adrs](docs/adrs) — Architecture decision records (Neo4j, Qwen3 models, tiered extraction).
- [BENCHMARKS.md](BENCHMARKS.md) — Current performance versus targets.

---

## Architecture

### Ingestion plane

* Firecrawl + Playwright → Normalizer (de-boilerplate, HTML→MD) → Chunker (semantic) → **TEI embeddings (GPU)** → **Qdrant** upserts.
* Structured sources (Docker Compose, SWAG, Tailscale, Unifi, Elasticsearch) parsed deterministically to nodes/edges.

### Extraction plane (async, decoupled)

1. **Tier A (Deterministic):** link/anchor graph, fenced code & tables, Aho-Corasick dictionaries for hosts/services/images/paths → immediate triples + candidate spans.
2. **Tier B (spaCy):** `entity_ruler` + dependency matchers + light sentence classifier to select **micro-windows**.
3. **Tier C (LLM windows):** Qwen3-4B-Instruct (Ollama) on ≤512-token windows, temperature 0, JSON-only schema; batch 8–16; cache by SHA-256.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for expanded diagrams and component responsibilities.

### Storage

* **Qdrant**: chunk vectors (BGE/e5/EmbeddingGemma class via TEI), metadata filters.
* **Neo4j**: property graph with labels `Service`, `Host`, `IP`, `Proxy`, `Endpoint`, `Doc`; batched `UNWIND` writes; constraints on natural keys.
* **Redis**: prompt/window cache, entity alias map, cursor state, DLQ.

### Retrieval (6-stage)

1. Query embedding (TEI)
2. Metadata filtering (source, date, tags)
3. Vector search (top-k in Qdrant)
4. Rerank (Qwen/Qwen3-Reranker-0.6B)
5. Graph traversal (≤2 hops in Neo4j)
6. Synthesis (Qwen3-4B) with inline numeric citations and source list.

---

## Data Model (Neo4j)

**Nodes**
`Service{name}`, `Host{hostname}`, `IP{addr}`, `Proxy{name}`, `Endpoint{service,method,path}`, `Doc{doc_id}`

**Edges**
`DEPENDS_ON`, `ROUTES_TO{host,path,tls}`, `BINDS{port,protocol}`, `RUNS{container_id?}`, `EXPOSES_ENDPOINT{auth?}`, `MENTIONS{span,section,hash}`

**Constraints**

```cypher
CREATE CONSTRAINT service_name IF NOT EXISTS
FOR (s:Service) REQUIRE s.name IS UNIQUE;

CREATE CONSTRAINT host_hostname IF NOT EXISTS
FOR (h:Host) REQUIRE h.hostname IS UNIQUE;

CREATE INDEX endpoint_key IF NOT EXISTS
FOR (e:Endpoint) ON (e.service, e.method, e.path);
```

Full label and relationship definitions live in [packages/graph/docs/GRAPH_SCHEMA.md](packages/graph/docs/GRAPH_SCHEMA.md).

---

## Prerequisites

* **Python** 3.11+ (tested on 3.13 via `uv`)
* **Node.js** 20+ (for web + codegen)
* **Docker** with **Compose**
* **NVIDIA GPU** (RTX 4070 recommended): recent driver + `nvidia-container-toolkit`
* **uv** package manager: `curl -LsSf https://astral.sh/uv/install.sh | sh`

---

## Quick Start

```bash
# Clone
git clone https://github.com/your-org/taboot
cd taboot

# Install Python deps (workspace)
uv sync

# JS workspace (for web + codegen)
pnpm install

# Config templates
cp docs/.env.example .env
cp docs/config.example.yaml config.yaml
$EDITOR .env
$EDITOR config.yaml

# Bring up infra (Qdrant, Neo4j, Redis, TEI, Ollama, Firecrawl, Playwright)
docker compose up -d
docker compose ps

# Initialize schema, collections, warmups
uv run apps/cli -h
uv run apps/cli init

# Try an ingestion
uv run apps/cli ingest web https://example.com --limit 50
uv run apps/cli extract pending     # run extraction worker on new docs

# Query
uv run apps/cli query "Which services expose port 8080?"
```

---

## Commands (CLI)

**Note**: Most commands are in development. The following shows the planned interface:

```bash
# System initialization
taboot init                          # Initialize Neo4j schema, Qdrant collections, indexes

# Ingestion (supports: web, github, reddit, youtube, gmail, elasticsearch,
#            docker-compose, swag, tailscale, unifi)
taboot ingest SOURCE TARGET [--limit N]
taboot ingest web https://example.com --limit 20
taboot ingest github owner/repo
taboot ingest reddit r/python --limit 100

# Extraction pipeline
taboot extract pending               # Process all docs awaiting extraction
taboot extract reprocess --since 7d  # Re-run extraction on docs from last 7 days
taboot extract status                # Show extraction pipeline status & metrics

# Querying
taboot query "your question" [--sources SOURCE1,SOURCE2] [--after DATE] [--top-k N]
taboot query "what changed in auth?" --sources github,reddit --after 2025-01-01

# System management
taboot status [--component COMPONENT] [--verbose]
taboot list RESOURCE [--limit N] [--filter EXPR]
```

---

## Docker Compose

`docker-compose.yml` lives at repository root and includes these services:

| Service             | Purpose                                        | GPU |
| ------------------- | ---------------------------------------------- | --- |
| `taboot-vectors`    | Qdrant vector DB (GPU indexing)                | ✅   |
| `taboot-embed`      | TEI embeddings (e.g., Qwen3-Embedding-0.6B)    | ✅   |
| `taboot-rerank`     | SentenceTransformers Qwen3 reranker service    | ✅   |
| `taboot-graph`      | Neo4j 5.23+ with APOC                          | ❌   |
| `taboot-cache`      | Redis 7.2 (state, cursors, caches, DLQ)        | ❌   |
| `taboot-db`         | PostgreSQL 16 (Firecrawl metadata)             | ❌   |
| `taboot-playwright` | Playwright browser microservice                | ❌   |
| `taboot-crawler`    | Firecrawl v2 API                               | ❌   |
| `taboot-ollama`     | Ollama LLM server (pull Qwen3-4B on first run) | ✅   |
| `taboot-app`        | Unified API + MCP + Web container              | ❌   |
| `taboot-worker`     | Extraction pipeline worker (spaCy + LLM tiers) | ❌   |

> Port and image settings align with `.env.example` provided below.

`taboot-app` bundles the FastAPI surface, MCP server, and web dashboard into a single container to keep the compose stack compact. Override the start command in
`docker/app/Dockerfile` if you need a different process supervisor.

Operational runbooks and production responses are documented in [apps/api/docs/RUNBOOK.md](apps/api/docs/RUNBOOK.md), while crawl etiquette and throttling live in [apps/api/docs/BACKPRESSURE_RATELIMITING.md](apps/api/docs/BACKPRESSURE_RATELIMITING.md).

---

## Configuration

Use `.env` to configure endpoints, credentials, and ports. The sample aligns with `docker-compose.yml`.

Key variables (excerpt):

```env
# Firecrawl
FIRECRAWL_API_URL=http://taboot-crawler:3002
FIRECRAWL_API_KEY=changeme

# Redis
REDIS_URL=redis://taboot-cache:6379

# Qdrant
QDRANT_URL=http://taboot-vectors:6333
QDRANT_HTTP_PORT=7000
QDRANT_GRPC_PORT=7001

# Neo4j
NEO4J_URI=bolt://taboot-graph:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=changeme

# TEI
TEI_EMBEDDING_URL=http://taboot-embed:80
TEI_EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B

# Reranker (SentenceTransformers)
RERANKER_URL=http://taboot-rerank:8000
RERANKER_MODEL=Qwen/Qwen3-Reranker-0.6B
RERANKER_BATCH_SIZE=16
RERANKER_DEVICE=auto

# Ollama
OLLAMA_PORT=11434

# API (optional)
LLAMACRAWL_API_URL=http://localhost:8000
```

See `docs/configuration.md` for per-source credentials (GitHub, Reddit, Gmail, Elasticsearch, Unifi, Tailscale).

Review [apps/api/docs/SECURITY_MODEL.md](apps/api/docs/SECURITY_MODEL.md) and [apps/api/docs/DATA_GOVERNANCE.md](apps/api/docs/DATA_GOVERNANCE.md) before rolling credentials or purging tenant data.

---

## LLM & NLP

* **spaCy:** start with `en_core_web_md`; selectively use `en_core_web_trf` for complex prose; emphasize `entity_ruler` and domain patterns.
* **LLM (Tier C):** Qwen3-4B-Instruct via Ollama; windows ≤512 tokens; temperature 0; strict JSON schema; batch 8–16; Redis prompt cache.
* **Embeddings (TEI):** BGE/e5/EmbeddingGemma-class models (768–1024 dims); batch aggressively; monitor VRAM.
* **Reranking (SentenceTransformers):** `Qwen/Qwen3-Reranker-0.6B` served via a small
  FastAPI wrapper (GPU if available). TEI does not yet ship Qwen3 rerankers, so we run
  the model through `sentence-transformers` instead of the TEI container.

Implementation details for the tiered extractor live in [packages/extraction/docs/EXTRACTION_SPEC.md](packages/extraction/docs/EXTRACTION_SPEC.md).

---

## Performance Targets (RTX 4070)

* **Tier A**: ≥50 pages/sec parse (CPU)
* **Tier B**: ≥200 sentences/sec (`md`), ≥40 (`trf`)
* **Tier C**: median ≤250 ms/window, p95 ≤750 ms (quantized 4B), batch≈12
* **Neo4j writes**: ≥20k edges/min with 2k-row `UNWIND`
* **Qdrant upserts**: ≥5k vectors/sec (1024-dim, HNSW)

Vector collection layout and tuning guidance are captured in [packages/vector/docs/VECTOR_SCHEMA.md](packages/vector/docs/VECTOR_SCHEMA.md).

---

## Observability & QA

* **Metrics:** windows/sec, tier hit ratios, LLM p95, cache hit-rate, Qdrant/Neo4j throughput.
* **Tracing:** `doc_id → section → windows → triples → txId`.
* **Validation:** ~300 labeled windows with F1 guardrails in CI; regression fails if F1 drops by ≥2 points.

Dashboards, alert thresholds, and evaluation procedures are described in [apps/api/docs/OBSERVABILITY.md](apps/api/docs/OBSERVABILITY.md) and [docs/EVALUATION_PLAN.md](docs/EVALUATION_PLAN.md).

---

## Development & CI

* **Python:** uv workspace; Ruff, Pyright, pytest.
* **JS/TS:** pnpm + Turborepo; ESLint, Vitest/Playwright.
* **Pre-commit:** Ruff/Black/Pyright + ESLint/Prettier.
* **CI (GitHub Actions):** lint, typecheck, test, build, dockerize api/mcp; cache uv + pnpm + turbo.

Automation-friendly targets are listed in [docs/MAKEFILE_REFERENCES.md](docs/MAKEFILE_REFERENCES.md) if you need scripted workflows.

---

## LlamaIndex Placement (important)

LlamaIndex is a framework concern and lives in **`packages/retrieval/`**:

* `context/` for Settings (TEI embed, Ollama LLM), prompts.
* `indices/` for VectorStoreIndex (Qdrant) and PropertyGraphIndex (Neo4jPGStore).
* `retrievers/` for hybrid retrievers and node post-processors.
* `query_engines/` for graph-augmented QA.

**Core never imports `llama_index.*`.** Apps depend on ports defined in `packages/core` that are implemented by adapters in `packages/retrieval`.

---

## Docker Services (reference)

The compose file at repo root reflects the services below; see inline comments there for ports, healthchecks, and GPU flags.

* **GPU-accelerated:** `taboot-vectors`, `taboot-embed`, `taboot-rerank`, `taboot-ollama`
* **CPU:** `taboot-graph`, `taboot-cache`, `taboot-db`, `taboot-playwright`, `taboot-crawler`, `taboot-app`, `taboot-worker`

---

## Roadmap

* Optional spaCy relation extractor fine-tune to offload common relations from LLM.
* Graph-aware chunk indexing for faster neighborhood expansion.
* Incremental crawlers (watchers) with backpressure & DLQ UI.
* Web graph visual analytics (impact analysis, blast radius).

---
