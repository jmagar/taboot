# Implementation Plan: Taboot Doc-to-Graph RAG Platform

**Branch**: `001-taboot-rag-platform` | **Date**: 2025-10-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-taboot-rag-platform/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a Doc-to-Graph RAG platform that ingests technical documentation from 11+ sources (web, GitHub, Reddit, YouTube, Gmail, Elasticsearch, Docker Compose, SWAG, Tailscale, Unifi, AI sessions), converts them into a Neo4j property graph with entities (Service, Host, IP, Proxy, Endpoint) and relationships (DEPENDS_ON, ROUTES_TO, BINDS, RUNS, EXPOSES_ENDPOINT, MENTIONS), stores semantic chunks in Qdrant for vector search, and enables natural language querying via hybrid retrieval (vector search + graph traversal + LLM synthesis) with strict source attribution.

**Technical Approach**: Multi-tier extraction pipeline (Tier A: regex/JSON parsing for deterministic patterns, Tier B: spaCy NLP for entity detection, Tier C: Qwen3-4B-Instruct LLM for ambiguous content), LlamaIndex for retrieval framework, TEI for embeddings, and strict architectural layering (`apps → adapters → core`).

## Technical Context

**Language/Version**: Python 3.11+ (managed via `uv` tool)
**Primary Dependencies**: LlamaIndex (readers, retrievers, query engines), FastAPI + Typer (app shells), Neo4j Python Driver, Qdrant Client, spaCy, Firecrawl v2 SDK, TEI client, Ollama Python SDK
**Storage**: Neo4j 5.23+ (graph database with APOC), Qdrant (vector database with GPU HNSW), PostgreSQL 16 (Firecrawl metadata), Redis 7.2 (state/cache/DLQ)
**Testing**: pytest with asyncio support, markers (`unit`, `integration`, `slow`, source-specific), target ≥85% coverage in core/extraction
**Target Platform**: Linux server (Docker Compose), GPU required (NVIDIA RTX 4070 or equivalent for TEI/reranker/Ollama)
**Project Type**: Multi-package monorepo with apps (`api`, `cli`, `mcp`, `worker`), adapters (`ingest`, `extraction`, `graph`, `vector`, `retrieval`), and core
**Performance Goals**: Tier A ≥50 pages/sec, Tier B ≥200 sentences/sec, Tier C ≤250ms median/≤750ms p95, Neo4j ≥20k edges/min, Qdrant ≥5k vectors/sec
**Constraints**: Query latency <5s median/<10s p95, ingestion <60s for 20-page docs, GPU memory usage monitored, strict layering (`apps → adapters → core`)
**Scale/Scope**: Single-user system, 10k+ document chunks initially, 11+ ingestion sources, 6-stage retrieval pipeline, F1 ≥0.85 on extraction validation set

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Single-User, Break-Fast Philosophy ✅
**Status**: PASS
**Justification**: Project explicitly designed as single-developer system with no backwards compatibility requirements. Breaking changes expected and database wipes acceptable.

### II. Strict Architectural Layering ✅
**Status**: PASS
**Justification**: Project structure enforces `apps → adapters → core` dependency flow:
- Core: Business logic in `packages/core/` (no framework deps)
- Adapters: Framework implementations in `packages/{ingest,extraction,graph,vector,retrieval}/`
- Apps: I/O shells in `apps/{api,cli,mcp,worker}` (no business logic)

### III. Framework-Agnostic Core ✅
**Status**: PASS
**Justification**: Core never imports `llama_index.*`, `neo4j.*`, `qdrant_client.*`. Core uses direct imports from adapter packages when needed. All LlamaIndex usage isolated to adapters (`packages/ingest/` for readers, `packages/extraction/` for LLM adapters, `packages/retrieval/` for indices/query engines).

### IV. Deterministic-First Extraction ✅
**Status**: PASS
**Justification**: Multi-tier pipeline escalates from cheap to expensive:
- Tier A: Deterministic regex/JSON (target ≥50 pages/sec)
- Tier B: spaCy NLP (target ≥200 sent/sec)
- Tier C: LLM windows only for ambiguous content (≤250ms median)

### V. Fail Fast, Throw Early ✅
**Status**: PASS
**Justification**: User constitution explicitly requires: "NEVER use any type, use types", "It's okay to break code when refactoring", "ALWAYS throw errors early and often", "Do not use fallbacks". Feature spec requires TDD methodology (FR-048 through FR-053).

### VI. Test Coverage Standards ✅
**Status**: PASS
**Justification**: Spec requires ≥85% coverage in core/extraction (FR-052), pytest with markers, TDD methodology for all production code (FR-048-053).

**CONSTITUTION VERDICT**: ✅ ALL GATES PASS - Proceed to Phase 0

---

## Post-Design Constitution Re-Check

*Re-evaluated after Phase 1 design (data-model, contracts, quickstart)*

### Design Artifacts Review

**Generated Artifacts**:
- `research.md` - Technology decisions with rationale (all unknowns resolved)
- `data-model.md` - 9 entities, 8 relationships, validation rules, state machines
- `contracts/api-openapi.yaml` - REST API specification (10 endpoints)
- `contracts/neo4j-constraints.cypher` - Graph schema constraints and indexes
- `contracts/qdrant-collection.json` - Vector collection configuration
- `contracts/postgresql-schema.sql` - Relational schema (4 tables)
- `quickstart.md` - Setup guide, workflows, TDD examples, troubleshooting

### Constitution Compliance Verification

✅ **I. Single-User, Break-Fast**: No migration guides, no backwards compatibility constraints
✅ **II. Strict Layering**: Design enforces `apps → adapters → core` (verified in data-model entity ownership)
✅ **III. Framework-Agnostic Core**: Core entities defined in data-model are framework-independent; LlamaIndex isolated to adapters (research.md confirms)
✅ **IV. Deterministic-First**: Extraction pipeline clearly tiered A→B→C (data-model ExtractionJob state machine)
✅ **V. Fail Fast, Throw Early**: Validation rules in data-model enforce constraints; quickstart shows TDD with strict type hints
✅ **VI. Test Coverage**: Quickstart demonstrates RED-GREEN-REFACTOR cycle; FR-048-053 from spec enforced

**FINAL VERDICT**: ✅ ALL GATES PASS - Design complies with constitution

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
apps/                           # Application entry points (thin I/O shells)
├── api/                       # FastAPI service (HTTP endpoints)
│   ├── app.py                # Main FastAPI app
│   ├── routes/               # API route handlers
│   └── docs/                 # API documentation
├── cli/                       # Typer CLI (terminal commands)
│   └── main.py               # CLI entry point
├── mcp/                       # MCP server (protocol adapter)
│   └── server.py             # MCP entry point
├── worker/                    # Background extraction worker
│   └── main.py               # Worker entry point
└── web/                       # Next.js dashboard (optional)
    └── [Next.js structure]

packages/                      # Adapter packages (framework implementations)
├── core/                     # Business logic (framework-agnostic)
│   ├── domain/              # Domain models
│   ├── use_cases/           # Use-case orchestration
│   └── interfaces/          # Adapter contracts
├── ingest/                   # LlamaIndex readers, normalizer, chunker
│   ├── readers/             # Source-specific readers (web, github, etc.)
│   ├── normalizer.py        # HTML-to-Markdown + de-boilerplate
│   └── chunker.py           # Semantic chunking
├── extraction/               # Multi-tier extraction engine
│   ├── tier_a/              # Deterministic (regex, JSON, Aho-Corasick)
│   ├── tier_b/              # spaCy NLP (entity_ruler, dependency matchers)
│   ├── tier_c/              # LLM windows (Qwen3-4B via Ollama)
│   └── orchestrator.py      # Tier coordination
├── graph/                    # Neo4j driver, Cypher builders, bulk writers
│   ├── client.py            # Neo4j connection
│   ├── cypher/              # Query builders
│   └── writers.py           # Batched UNWIND operations
├── vector/                   # Qdrant client, hybrid search, reranking
│   ├── client.py            # Qdrant connection
│   ├── search.py            # Vector search
│   └── reranker.py          # SentenceTransformers integration
├── retrieval/                # LlamaIndex indices, retrievers, query engines
│   ├── context/             # Settings (TEI, Ollama LLM), prompts
│   ├── indices/             # Index management
│   ├── retrievers/          # Hybrid retrievers
│   └── query_engines/       # Graph-augmented QA
├── schemas/                  # Pydantic models, OpenAPI schemas
│   └── models.py            # Shared data models
└── common/                   # Logging, config, tracing, utils
    ├── logging.py           # JSON structured logging
    ├── config.py            # Environment config
    └── tracing.py           # Correlation ID tracking

tests/                        # Test suite (mirrors package structure)
├── apps/
├── packages/
│   ├── core/
│   ├── ingest/
│   ├── extraction/
│   └── ...
└── conftest.py              # Shared fixtures

docker-compose.yaml           # Service orchestration
.env.example                  # Environment template
pyproject.toml                # Python project config (uv)
uv.lock                       # Dependency lock file
```

**Structure Decision**: Multi-package monorepo with strict layering. Apps consume adapters, adapters consume core. All LlamaIndex usage isolated to adapter packages (`ingest/` readers, `extraction/` LLM adapters, `retrieval/` indices/query engines). Core remains framework-agnostic for testability.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

**No violations detected.** All constitution gates pass.

