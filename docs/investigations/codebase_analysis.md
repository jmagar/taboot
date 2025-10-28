# Taboot RAG Platform - Comprehensive Codebase Analysis

## Executive Summary

**Taboot** is a production-ready, single-user Doc-to-Graph RAG (Retrieval-Augmented Generation) platform that combines vector search, graph databases, and LLM-powered extraction to transform multi-source documentation into a queryable knowledge graph.

**Project Classification**: Multi-language monorepo with strict architectural layering
**Primary Languages**: Python 3.11+ (backend/RAG), TypeScript (web/tooling)
**Architecture Pattern**: Hexagonal/Clean Architecture (apps → adapters → core)
**Deployment**: Docker Compose with GPU acceleration (NVIDIA)
**Scale**: ~66k files, 8.5GB codebase (includes dependencies)

---

## 1. Project Overview

### Project Type
**Hybrid Platform**: RAG pipeline + Multi-interface applications (API, CLI, MCP, Web Dashboard)

### Core Purpose
1. **Ingestion**: Crawl/read from 11+ sources (web, GitHub, Reddit, YouTube, Gmail, Elasticsearch, Docker Compose configs, SWAG, Tailscale, Unifi, AI sessions)
2. **Extraction**: 3-tier knowledge extraction (deterministic → spaCy NLP → Qwen3-4B LLM)
3. **Storage**: Dual-database (Neo4j graph + Qdrant vectors)
4. **Retrieval**: Hybrid search (vector → rerank → graph traversal → synthesis) with source attribution

### Tech Stack

**Backend (Python)**
- **Runtime**: Python 3.11-3.13 (managed via `uv`)
- **RAG Framework**: LlamaIndex 0.12+
- **Web Framework**: FastAPI (API server)
- **CLI Framework**: Typer
- **Graph DB**: Neo4j 5.23+ (bolt protocol)
- **Vector DB**: Qdrant (HTTP/gRPC with GPU indexing)
- **Cache/Queue**: Redis 7.2
- **NLP**: spaCy (en_core_web_md/trf), sentence-transformers
- **LLM**: Qwen3-4B-Instruct (Ollama), TEI embeddings
- **Crawling**: Firecrawl v2, Playwright, Selenium

**Frontend (TypeScript/React)**
- **Framework**: Next.js 16.1+ (App Router, RSC)
- **Auth**: Better-Auth (custom JWT + session management)
- **UI**: Tailwind CSS + shadcn/ui components
- **Database**: Prisma ORM (PostgreSQL auth schema)
- **Testing**: Vitest, Playwright
- **Validation**: Zod schemas

**Infrastructure**
- **Containerization**: Docker Compose (12 services)
- **GPU**: NVIDIA Container Toolkit (TEI, Qdrant, Ollama, reranker)
- **CI/CD**: GitHub Actions (web tests, Docker builds)
- **Monitoring**: Prometheus metrics, structured JSON logging

### Architecture Pattern

**Strict Hexagonal/Clean Architecture**:
```
apps/          → Thin I/O shells (FastAPI, Typer, MCP, Next.js)
  ↓
packages/      → Adapter implementations (ingest, extraction, graph, vector, retrieval)
  ↓
packages/core/ → Framework-agnostic business logic (use cases, domain models, ports)
```

**Enforcement**:
- Python: `import-linter` rules
- TypeScript: `eslint-plugin-boundaries`
- **Core never imports framework code** (no FastAPI, LlamaIndex, Neo4j drivers in core/)

### Language Versions
- **Python**: 3.11.0 - 3.13.7 (tested on 3.13)
- **Node.js**: 20+ (LTS)
- **TypeScript**: 5.9.2
- **Neo4j**: 5.23+
- **PostgreSQL**: 16+
- **Redis**: 7.2+

---

## 2. Detailed Directory Structure Analysis

### `/apps` - Application Shells (I/O Layer)

**Purpose**: Thin interface layers with zero business logic. Each app exposes the same core functionality through different protocols.

#### **`apps/api/` - FastAPI HTTP Service**
- **Entry**: `app.py` (FastAPI application factory)
- **Routes**: REST endpoints (`/ingest`, `/extract`, `/query`, `/documents`, `/metrics`, `/init`)
- **Middleware**: JWT auth, rate limiting, metrics collection, structured logging
- **Dependencies**: Injects adapters (graph writers, vector clients, extraction pipelines) via `deps/`
- **Docs**: OpenAPI spec (`openapi.yaml`), runbooks, security model

**Key Files**:
- `app.py:45` - FastAPI app factory with CORS, middleware stack
- `routes/query.py:23` - Query endpoint using `packages.core.use_cases.query`
- `middleware/jwt_auth.py:15` - Custom JWT validation (RS256)
- `deps/extraction.py:18` - Dependency injection for extraction services

#### **`apps/cli/` - Typer CLI**
- **Entry**: `main.py` (Typer app with command groups)
- **Commands**: `init`, `ingest`, `extract`, `query`, `list`, `status`, `schema`
- **Style**: Rich console output, progress bars, table formatting
- **Dependencies**: Shares same adapter layer as API

**Key Files**:
- `taboot_cli/main.py:34` - CLI app structure
- `taboot_cli/commands/ingest_web.py:28` - Web ingestion command
- `taboot_cli/commands/schema.py:15` - Database schema management

#### **`apps/mcp/` - Model Context Protocol Server**
- **Purpose**: Expose Taboot as MCP tools for LLM agents (Claude Code, etc.)
- **Protocol**: JSON-RPC over stdio
- **Handlers**: Map MCP tool calls to core use cases
- **Status**: Basic implementation, handlers defined

#### **`apps/web/` - Next.js Dashboard**
- **Framework**: Next.js 16.1+ (App Router, React Server Components)
- **Auth**: Better-Auth (JWT + session cookies, 2FA support)
- **Features**: User management, document browsing, query interface, analytics dashboard
- **Security**: CSP headers, CSRF protection (double-submit cookie), rate limiting (ioredis)
- **Database**: Prisma ORM → PostgreSQL (auth schema: User, Session, Account, AuditLog)
- **Middleware**: Soft delete (User model), audit logging, IP tracking

**Key Files**:
- `app/layout.tsx:12` - Root layout with RSC providers
- `app/(auth)/sign-in/page.tsx:18` - Auth form with CSRF
- `lib/api.ts:45` - Type-safe API client (generated from OpenAPI)
- `middleware.ts:67` - CSRF validation, rate limiting, auth checks
- `packages-ts/db/src/middleware/soft-delete.ts:34` - Prisma middleware for soft deletes

**Patterns**:
- Server Components for data fetching
- Client Components (`'use client'`) for interactivity
- Server Actions for mutations
- Parallel route groups: `(auth)`, `(default)`

---

### `/packages` - Python Adapter Layer (Pluggable Implementations)

**Purpose**: Framework-specific implementations of ports defined in `packages/core`. Each package is independently testable.

#### **`packages/core/` - Business Logic (Framework-Agnostic)**
**Architecture**: Hexagonal/Clean Architecture core

**Structure**:
```
core/
├── entities/        # Domain models (Document, ExtractionJob, ChunkMetadata)
├── value_objects/   # Immutable types (DocumentID, SourceType)
├── ports/           # Interfaces (repositories, services)
│   └── repositories/
├── use_cases/       # Application logic (ingest, extract, query)
└── services/        # Domain services (orchestration)
```

**Key Principles**:
- Zero framework dependencies (only schemas + common)
- All adapters depend on core, never reverse
- Domain-driven design patterns

**Key Files**:
- `use_cases/query.py:56` - Query orchestration (vector → graph → synthesis)
- `entities/document.py:23` - Document aggregate root
- `ports/repositories/document_repository.py:12` - Repository interface

#### **`packages/ingest/` - Data Ingestion Adapters**
**Purpose**: Read, normalize, chunk, and prepare documents for storage

**Components**:
```
ingest/
├── sources/         # Source-specific readers (web, GitHub, Reddit, YouTube, Gmail)
├── readers/         # LlamaIndex reader wrappers
├── normalizers/     # HTML→Markdown, de-boilerplate
├── chunkers/        # Semantic chunking (sentence-based)
├── adapters/        # Redis streams consumer, batch processors
└── services/        # Ingestion orchestration
```

**Technologies**:
- Firecrawl v2 (web crawling)
- LlamaIndex readers (GitHub, Gmail, YouTube)
- BeautifulSoup4 + html2text (normalization)
- spaCy sentence segmentation (chunking)

**Key Files**:
- `sources/web.py:45` - Firecrawl integration
- `normalizers/html_normalizer.py:28` - Markdown conversion
- `chunkers/semantic_chunker.py:67` - Sentence-based chunking

#### **`packages/extraction/` - Multi-Tier Knowledge Extraction**
**Purpose**: Extract structured knowledge (entities, relationships, metadata) from text

**Tiers**:
1. **Tier A (Deterministic)**: Regex, JSON/YAML parsing, Aho-Corasick (≥50 pages/sec)
2. **Tier B (spaCy NLP)**: Entity ruler, dependency matchers (≥200 sentences/sec)
3. **Tier C (LLM)**: Qwen3-4B windows ≤512 tokens (median ≤250ms/window)

**Structure**:
```
extraction/
├── tier_a/          # Deterministic extractors (links, code blocks, tables)
├── tier_b/          # spaCy pipelines (entity ruler, matchers)
├── tier_c/          # LLM window processing (Ollama)
├── pipelines/       # Orchestration (tier selection, batching)
└── utils/           # Caching (Redis), schema validation
```

**Key Files**:
- `tier_a/link_extractor.py:34` - Graph construction from hyperlinks
- `tier_b/spacy_extractor.py:78` - Entity ruler + dependency parsing
- `tier_c/llm_extractor.py:123` - Qwen3 JSON schema enforcement
- `pipelines/orchestrator.py:89` - Tier selection and batch processing

#### **`packages/graph/` - Neo4j Adapter**
**Purpose**: Write entities/relationships to Neo4j graph database

**Structure**:
```
graph/
├── cypher/          # Query builders (CREATE, MERGE, MATCH)
├── writers/         # Bulk UNWIND writers (batched upserts)
├── queries/         # Traversal queries (neighborhood expansion)
├── migrations/      # Schema versioning (constraints, indexes)
└── utils/           # Connection pooling, transaction management
```

**Performance**:
- Batch writes: 2k-row UNWIND (target ≥20k edges/min)
- Connection pooling: async neo4j driver
- Constraints: Unique indexes on natural keys

**Key Files**:
- `writers/bulk_writer.py:45` - Batched UNWIND upserts
- `cypher/builders.py:67` - Dynamic Cypher generation
- `migrations/versioning.py:23` - Idempotent constraint application

#### **`packages/vector/` - Qdrant Adapter**
**Purpose**: Write embeddings and search with hybrid retrieval

**Structure**:
```
vector/
├── writers/         # Batch upsert (HNSW collections)
├── queries/         # Vector search + metadata filtering
├── reranker.py      # Qwen3-Reranker-0.6B integration
├── migrations/      # Collection schema versioning
└── utils/           # Embedding clients (TEI)
```

**Configuration**:
- HNSW indexing (GPU-accelerated)
- Batch size: 5k vectors/sec (1024-dim)
- Reranking: Qwen3 via FastAPI wrapper

**Key Files**:
- `writers/qdrant_writer.py:56` - Bulk vector upserts
- `queries/hybrid_search.py:89` - Vector + metadata filtering
- `reranker.py:34` - Sentence-transformers reranker

#### **`packages/retrieval/` - LlamaIndex Retrieval Adapters**
**Purpose**: Orchestrate hybrid retrieval (vector → rerank → graph → synthesize)

**Structure**:
```
retrieval/
├── context/         # LlamaIndex Settings (embeddings, LLM)
├── indices/         # Index wrappers (VectorStoreIndex, PropertyGraphIndex)
├── retrievers/      # Custom retrievers (hybrid, graph-augmented)
├── query_engines/   # QA synthesis with citations
└── services/        # Retrieval orchestration
```

**6-Stage Pipeline**:
1. Query embedding (TEI)
2. Metadata filtering (source, date)
3. Vector search (Qdrant top-k)
4. Reranking (Qwen3)
5. Graph traversal (Neo4j ≤2 hops)
6. Synthesis (Qwen3 with inline citations)

**Key Files**:
- `retrievers/hybrid.py:123` - Hybrid retrieval coordinator
- `query_engines/qa.py:89` - Citation-aware synthesis
- `context/settings.py:45` - LlamaIndex global config

#### **`packages/schemas/` - Pydantic Models**
**Purpose**: Shared data models, validation, OpenAPI generation

**Key Files**:
- `models/document.py:34` - Document schemas
- `models/extraction_job.py:56` - Job status enums

#### **`packages/common/` - Shared Utilities**
**Purpose**: Logging, config, tracing, DB schema management

**Key Files**:
- `config/__init__.py:23` - Environment variable parsing
- `logging/json_logger.py:45` - Structured JSON logging
- `db_schema.py:67` - PostgreSQL schema versioning

---

### `/packages-ts` - TypeScript Monorepo (pnpm workspace)

**Purpose**: Shared TypeScript packages for web app and tooling

#### **`packages-ts/db/` - Prisma ORM**
**Schema**: PostgreSQL auth database (separate from Python RAG db)

**Models**:
- `User` (soft delete: deletedAt, deletedBy)
- `Session` (JWT + cookie sessions)
- `Account` (OAuth providers)
- `Verification` (email verification tokens)
- `TwoFactor` (TOTP secrets)
- `AuditLog` (permanent compliance record)

**Middleware**:
- Soft delete: Intercepts `delete()` → `update({deletedAt})`
- Automatic filtering: Exclude soft-deleted from queries
- Context injection: Track deletedBy, ipAddress, userAgent

**Key Files**:
- `prisma/schema.prisma:89` - Database schema
- `src/middleware/soft-delete.ts:67` - Soft delete implementation
- `src/context.ts:23` - Request context management

#### **`packages-ts/auth/` - Better-Auth Integration**
**Features**:
- JWT (RS256) + session cookies (dual-token)
- 2FA (TOTP via authenticator apps)
- Email verification
- OAuth providers (GitHub, Google)
- Rate limiting (password endpoints: 5/10min)

**Key Files**:
- `src/server.ts:45` - Auth server configuration
- `src/client.ts:23` - React hooks + client utilities

#### **`packages-ts/api-client/` - Generated TypeScript Client**
**Source**: OpenAPI spec (`apps/api/openapi.yaml`)
**Generator**: `openapi-typescript`
**Usage**: Type-safe API calls from Next.js

#### **`packages-ts/ui/` - shadcn/ui Component Library**
**Components**: Button, Input, Card, Dialog, Sheet, Sidebar, etc.
**Styling**: Tailwind CSS utility classes
**Accessibility**: ARIA attributes, keyboard navigation

#### **`packages-ts/rate-limit/` - ioredis Rate Limiter**
**Algorithm**: Token bucket (sliding window)
**Storage**: Redis (ioredis client)
**Features**: Fail-closed (throws on Redis unavailable)

**Key Files**:
- `src/index.ts:56` - Rate limiter implementation

---

### `/docker` - Docker Infrastructure

**Services** (12 containers):

| Service | Purpose | GPU | Port |
|---------|---------|-----|------|
| `taboot-api` | FastAPI server | ❌ | 8000 |
| `taboot-web` | Next.js app | ❌ | 3000 |
| `taboot-worker` | Extraction worker | ❌ | - |
| `taboot-vectors` | Qdrant | ✅ | 6333 |
| `taboot-embed` | TEI embeddings | ✅ | 80 |
| `taboot-rerank` | Qwen3 reranker | ✅ | 8000 |
| `taboot-ollama` | LLM server | ✅ | 11434 |
| `taboot-graph` | Neo4j | ❌ | 7687 |
| `taboot-cache` | Redis | ❌ | 6379 |
| `taboot-db` | PostgreSQL | ❌ | 5432 |
| `taboot-crawler` | Firecrawl v2 | ❌ | 3002 |
| `taboot-playwright` | Browser service | ❌ | 9222 |

**Dockerfiles**:
- `docker/api/Dockerfile` - Turbo prune + uv install
- `docker/web/Dockerfile` - Standalone Next.js build
- `docker/reranker/Dockerfile` - FastAPI + sentence-transformers

---

### `/tests` - Test Suite

**Structure**:
```
tests/
├── packages/        # Unit tests (pytest markers: unit, fast)
│   ├── core/        # Business logic tests
│   ├── extraction/  # Tier A/B/C tests
│   ├── graph/       # Cypher builder tests
│   ├── vector/      # Qdrant client tests
│   └── retrieval/   # Retriever tests
├── packages-ts/     # TypeScript unit tests (Vitest)
│   └── db/          # Soft delete middleware tests
├── integration/     # E2E tests (pytest markers: integration, slow)
│   ├── test_ingest_web_e2e.py
│   ├── test_extract_e2e.py
│   └── test_query_e2e.py
├── apps/            # App-specific tests
│   ├── api/         # FastAPI route tests
│   ├── cli/         # CLI command tests
│   └── worker/      # Worker pipeline tests
└── live/            # Manual test data (docker-compose configs)
```

**Test Configuration**:
- **Python**: pytest + pytest-asyncio + pytest-cov
- **TypeScript**: Vitest + @testing-library/react
- **E2E**: Playwright (web app)
- **Coverage Target**: ≥85% (core + extraction)

---

### `/docs` - Documentation

**Key Files**:
- `ARCHITECTURE.md` - Platform overview
- `EVALUATION_PLAN.md` - Retrieval metrics, CI gates
- `TECH_STACK_SUMMARY.md` - Technology decisions
- `DEPLOYMENT_COMPLETE.md` - Deployment runbook
- `CSRF_XSS_RISKS.md` - Security threat model

**Subdirectories**:
- `adrs/` - Architecture Decision Records
- `plans/` - Implementation plans

---

### `/specs` - Project Specifications

**Structure**:
```
specs/
└── 001-taboot-rag-platform/
    ├── contracts/           # API contracts, database schemas
    │   ├── openapi.yaml
    │   ├── postgresql-schema.sql
    │   ├── neo4j-constraints.cypher
    │   └── qdrant-collection.json
    ├── quickstart.md
    └── architecture.md
```

---

## 3. File-by-File Breakdown

### Core Application Files

#### **Python Entry Points**
1. **`apps/api/app.py`** (FastAPI application factory)
   - CORS middleware
   - JWT authentication
   - Rate limiting (slowapi)
   - Prometheus metrics
   - Route registration
   - OpenAPI spec generation

2. **`apps/cli/main.py`** (Typer CLI app)
   - Command groups (ingest, extract, query, admin)
   - Rich console formatting
   - Progress tracking
   - Error handling with exit codes

3. **`apps/worker/__main__.py`** (Background extraction worker)
   - Redis Streams consumer
   - Batch processing
   - Graceful shutdown
   - Tier orchestration

#### **TypeScript Entry Points**
1. **`apps/web/app/layout.tsx`** (Next.js root layout)
   - RSC providers (theme, auth)
   - Global metadata
   - Font optimization
   - Analytics initialization

2. **`apps/web/middleware.ts`** (Edge middleware)
   - CSRF validation
   - Rate limiting
   - Auth session checks
   - IP tracking
   - Soft delete context injection (planned)

### Configuration Files

#### **Build & Dev Tools**

**TypeScript/JavaScript**:
- **`package.json`** - Root workspace config (pnpm + Turbo)
- **`apps/web/package.json`** - Next.js dependencies
- **`packages-ts/*/package.json`** - Individual package configs
- **`turbo.json`** - Build caching configuration
- **`tsconfig.json`** - Base TypeScript config (strict mode)
- **`eslint.config.js`** - ESLint 9 flat config + boundaries plugin
- **`apps/web/components.json`** - shadcn/ui configuration
- **`apps/web/tailwind.config.ts`** - Tailwind CSS theme

**Python**:
- **`pyproject.toml`** - Root Python project (uv workspace)
- **`uv.lock`** - Dependency lockfile (deterministic builds)
- **`ruff.toml`** - Ruff linter config (line length: 100)
- **`mypy.ini`** - Mypy strict type checking
- **`pytest.ini`** - pytest configuration (markers, coverage)
- **`.pre-commit-config.yaml`** - Git hooks (ruff, mypy, prettier)

#### **Environment & Docker**

**Environment**:
- **`.env.example`** - Template with all required variables
- **`.envrc`** - direnv configuration (auto-loads .env)
- **`apps/web/.env.example`** - Next.js-specific env vars

**Docker**:
- **`docker-compose.yaml`** - 12-service orchestration
- **`docker/api/Dockerfile`** - FastAPI production image
- **`docker/web/Dockerfile`** - Next.js standalone build
- **`.dockerignore`** - Exclude unnecessary files from build context

#### **Database**

**PostgreSQL (Auth)**:
- **`packages-ts/db/prisma/schema.prisma`** - Prisma schema
- **`packages-ts/db/prisma/migrations/`** - Migration history
- **`specs/001-taboot-rag-platform/contracts/postgresql-schema.sql`** - RAG schema

**Neo4j**:
- **`specs/001-taboot-rag-platform/contracts/neo4j-constraints.cypher`** - Graph constraints

**Qdrant**:
- **`specs/001-taboot-rag-platform/contracts/qdrant-collection.json`** - Collection config

### Data Layer

#### **Models/Schemas (Python)**
- `packages/schemas/models/document.py` - Document entity
- `packages/schemas/models/extraction_job.py` - Job tracking
- `packages/schemas/models/chunk_metadata.py` - Chunk schema
- `packages/schemas/models/graph_nodes.py` - Neo4j node types

#### **Repositories (Python)**
- `packages/core/ports/repositories/document_repository.py` - Interface
- Implementation in adapters (not in core/)

#### **Migrations**
- `packages/graph/migrations/versioning.py` - Neo4j idempotent constraints
- `packages/vector/migrations/versioning.py` - Qdrant collection aliases
- `packages/common/db_schema.py` - PostgreSQL schema versioning (SHA-256 checksums)

### Frontend/UI (Next.js)

#### **Pages (App Router)**
- `apps/web/app/page.tsx` - Landing page
- `apps/web/app/(auth)/sign-in/page.tsx` - Sign-in form
- `apps/web/app/(default)/dashboard/page.tsx` - Dashboard
- `apps/web/app/api/*/route.ts` - API routes (Server Actions)

#### **Components**
- `apps/web/components/auth-form.tsx` - Authentication UI
- `apps/web/components/app-sidebar.tsx` - Navigation sidebar
- `apps/web/components/nav-user.tsx` - User menu
- `packages-ts/ui/src/components/*.tsx` - Shared UI components

#### **Styles**
- `apps/web/app/globals.css` - Tailwind base + custom CSS variables
- `packages-ts/ui/src/index.css` - Component styles

### Testing

#### **Python Tests**
- `tests/packages/core/use_cases/test_query.py` - Query use case
- `tests/packages/extraction/tier_c/test_llm_extractor.py` - LLM extraction
- `tests/integration/test_ingest_web_e2e.py` - Full ingestion pipeline

#### **TypeScript Tests**
- `tests/packages-ts/db/soft-delete.test.ts` - Prisma middleware
- `apps/web/lib/__tests__/csrf-client.test.ts` - CSRF validation
- `apps/web/lib/__tests__/api-formdata.test.ts` - API client

#### **Test Fixtures**
- `tests/live/test-data/` - Sample documents, docker-compose files
- `tests/conftest.py` - Shared pytest fixtures

### Documentation

#### **User-Facing**
- `README.md` - Quick start, architecture overview
- `specs/001-taboot-rag-platform/quickstart.md` - Detailed setup
- `CHANGELOG.md` - Version history

#### **Developer Docs**
- `CLAUDE.md` - AI assistant instructions (project-specific)
- `docs/ARCHITECTURE.md` - Deep dive into design
- `apps/api/docs/API.md` - REST API reference
- `apps/web/TESTING.md` - Testing guide

#### **Operational**
- `apps/api/docs/RUNBOOK.md` - Incident response
- `apps/api/docs/OBSERVABILITY.md` - Monitoring setup
- `docs/DEPLOYMENT_COMPLETE.md` - Deployment checklist

### DevOps

#### **CI/CD**
- `.github/workflows/web-test.yml` - Next.js tests + type checking
- `.github/workflows/docker-build.yml` - Build and push images

#### **Deployment Scripts**
- `apps/web/scripts/cleanup-deleted-users.ts` - GDPR compliance (soft delete cleanup)

---

## 4. API Endpoints Analysis

### FastAPI REST API (`apps/api/`)

**Base URL**: `http://localhost:8000`

#### **Authentication**
- **Method**: JWT (RS256) + API keys
- **Headers**: `Authorization: Bearer <token>` or `X-API-Key: <key>`
- **Middleware**: `apps/api/middleware/jwt_auth.py`

#### **Endpoints**

##### **Initialization**
```
POST /init
Description: Initialize database schemas (Neo4j, Qdrant, PostgreSQL)
Auth: Required
Response: {status: "success", initialized: ["neo4j", "qdrant", "postgresql"]}
```

##### **Ingestion**
```
POST /ingest
Description: Ingest documents from source
Body: {
  source: "web" | "github" | "reddit" | ...,
  target: string,  # URL, repo, subreddit, etc.
  limit?: number,
  metadata?: Record<string, any>
}
Response: {
  job_id: string,
  status: "pending" | "running" | "completed" | "failed",
  documents_created: number
}
```

##### **Extraction**
```
POST /extract
Description: Trigger extraction pipeline
Body: {job_ids?: string[], reprocess?: boolean}
Response: {extraction_jobs: ExtractionJob[]}

GET /extract/status
Description: Get extraction pipeline status
Response: {
  pending: number,
  running: number,
  completed: number,
  failed: number,
  metrics: {tier_a_hit_rate: number, tier_b_hit_rate: number, tier_c_hit_rate: number}
}
```

##### **Query**
```
POST /query
Description: Hybrid retrieval query
Body: {
  query: string,
  filters?: {sources?: string[], after?: string},
  top_k?: number  # default: 10
}
Response: {
  answer: string,
  sources: [{doc_id: string, title: string, url: string, relevance: number}],
  retrieval_time_ms: number
}
```

##### **Documents**
```
GET /documents
Description: List ingested documents
Query: ?limit=10&offset=0&source=web
Response: {
  documents: Document[],
  total: number,
  page: number
}

GET /documents/{doc_id}
Description: Get document details
Response: Document

DELETE /documents/{doc_id}
Description: Soft delete document (marks deletedAt)
Response: {deleted: true, doc_id: string}
```

##### **Metrics**
```
GET /metrics
Description: Prometheus metrics
Response: text/plain (Prometheus exposition format)
```

##### **Health**
```
GET /health
Description: Health check
Response: {status: "ok", services: {neo4j: "up", qdrant: "up", redis: "up"}}
```

#### **Error Responses**

**Standard Format**:
```json
{
  "error": "Error message",
  "detail": "Detailed explanation",
  "status_code": 400
}
```

**Status Codes**:
- 200: Success
- 400: Bad request (validation error)
- 401: Unauthorized (missing/invalid JWT)
- 403: Forbidden (insufficient permissions)
- 404: Not found
- 429: Too many requests (rate limit)
- 500: Internal server error
- 503: Service unavailable (dependency down)

#### **API Versioning**
**Current**: No versioning (pre-v1.0)
**Future**: `/v1/` prefix planned

---

### Next.js API Routes (`apps/web/app/api/`)

**Base URL**: `http://localhost:3000/api`

#### **Auth Routes** (via Better-Auth)
```
POST /api/auth/sign-in
POST /api/auth/sign-up
POST /api/auth/sign-out
POST /api/auth/session
POST /api/auth/verify-email
POST /api/auth/two-factor/setup
POST /api/auth/two-factor/verify
POST /api/password/reset
POST /api/password/update
```

#### **User Management**
```
DELETE /api/users/{id}
POST /api/users/{id}/erase  # Hard delete (admin)
POST /api/admin/users/{id}/restore  # Restore soft delete
```

#### **Health**
```
GET /api/health
Response: {status: "ok", timestamp: string}
```

#### **CSP Reporting**
```
POST /api/csp-report
Description: Content Security Policy violation reports
Body: CSP violation JSON
Response: 204 No Content
```

---

## 5. Architecture Deep Dive

### Overall Application Architecture

**Pattern**: Hexagonal (Ports & Adapters) + Clean Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         APPS (I/O LAYER)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐ │
│  │  FastAPI    │  │   Typer     │  │     MCP     │  │  Next.js  │ │
│  │    API      │  │    CLI      │  │   Server    │  │    Web    │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬─────┘ │
└─────────┼────────────────┼────────────────┼───────────────┼────────┘
          │                │                │               │
          └────────────────┴────────────────┴───────────────┘
                                   │
┌──────────────────────────────────┼────────────────────────────────────┐
│                       ADAPTERS (IMPLEMENTATIONS)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │  Ingest  │  │Extraction│  │  Graph   │  │  Vector  │  │Retrieval│ │
│  │ (11 srcs)│  │ (3 tiers)│  │ (Neo4j)  │  │ (Qdrant) │  │(LlamaIdx│ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───┬────┘ │
└───────┼─────────────┼─────────────┼──────────────┼─────────────┼───────┘
        │             │             │              │             │
        └─────────────┴─────────────┴──────────────┴─────────────┘
                                   │
┌──────────────────────────────────┼────────────────────────────────────┐
│                          CORE (BUSINESS LOGIC)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │  Use Cases   │  │   Entities   │  │    Ports     │               │
│  │  (orchestr.) │  │  (domain)    │  │ (interfaces) │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
└────────────────────────────────────────────────────────────────────────┘
```

### Data Flow & Request Lifecycle

#### **Ingestion Pipeline**

```
User Request (CLI/API)
  ↓
1. SELECT SOURCE READER
   └─ Web: Firecrawl + Playwright
   └─ GitHub: LlamaIndex GitHub reader
   └─ Reddit: PRAW wrapper
   └─ YouTube: youtube-transcript-api
   └─ Gmail: Google API client
   └─ Structured: Direct JSON/YAML parsers
  ↓
2. NORMALIZE CONTENT
   └─ HTML → Markdown (html2text)
   └─ De-boilerplate (content extraction)
   └─ Unicode normalization
  ↓
3. SEMANTIC CHUNKING
   └─ Sentence segmentation (spaCy)
   └─ Target: 256-512 tokens/chunk
   └─ Preserve paragraph boundaries
  ↓
4. EMBED CHUNKS
   └─ TEI endpoint (Qwen3-Embedding-0.6B)
   └─ Batch: 32 chunks
   └─ Output: 1024 dim vectors
  ↓
5. STORE DUAL-DATABASE
   ├─ Qdrant: Upsert vectors + metadata
   └─ PostgreSQL: Document records (rag.documents, rag.document_content)
  ↓
6. QUEUE EXTRACTION
   └─ Redis Streams: Push doc_id to extraction queue
```

#### **Extraction Pipeline** (Background Worker)

```
Redis Streams Consumer (taboot-worker)
  ↓
1. TIER A (DETERMINISTIC)
   └─ Regex patterns (URLs, IPs, ports)
   └─ Fenced code blocks → code graph
   └─ Markdown tables → structured data
   └─ Aho-Corasick dictionaries (services, images)
   └─ Performance: ≥50 pages/sec
   └─ Output: Immediate triples + candidate spans
  ↓
2. TIER B (SPACY NLP)
   └─ Entity ruler (custom patterns)
   └─ Dependency matchers (verb-object relations)
   └─ Sentence classifier (select micro-windows)
   └─ Model: en_core_web_md (or trf for prose)
   └─ Performance: ≥200 sentences/sec
   └─ Output: High-confidence entities + relation candidates
  ↓
3. TIER C (LLM WINDOWS)
   └─ Window selection: Tier B flagged spans
   └─ Context: ≤512 tokens
   └─ Model: Qwen3-4B-Instruct (Ollama)
   └─ Temperature: 0 (deterministic)
   └─ Output: JSON schema (entities, relations, metadata)
   └─ Batch: 8-16 windows
   └─ Cache: Redis (SHA-256 key)
   └─ Performance: median ≤250ms/window, p95 ≤750ms
  ↓
4. WRITE TO NEO4J
   └─ Batch UNWIND (2k-row batches)
   └─ Merge nodes on natural keys
   └─ Create relationships with metadata
   └─ Performance: ≥20k edges/min
  ↓
5. UPDATE JOB STATUS
   └─ PostgreSQL: Update rag.extraction_jobs
   └─ Metrics: tier hit rates, processing time
```

#### **Query Pipeline** (6-Stage Hybrid Retrieval)

```
User Query (CLI/API/Web)
  ↓
1. QUERY EMBEDDING
   └─ TEI endpoint (same model as ingestion)
   └─ Output: Query vector (1024 dim)
  ↓
2. METADATA FILTERING
   └─ Sources: Filter by source type (web, github, etc.)
   └─ Date range: Filter by ingestion_timestamp
   └─ Tags: Custom metadata filters
  ↓
3. VECTOR SEARCH
   └─ Qdrant: Cosine similarity search
   └─ Top-k: Configurable (default 50)
   └─ HNSW index (GPU-accelerated)
   └─ Output: Candidate chunks (scored)
  ↓
4. RERANKING
   └─ Qwen3-Reranker-0.6B (sentence-transformers)
   └─ Cross-encoder scoring
   └─ Top-k: 10-20 chunks
   └─ Output: Re-ranked chunks (higher precision)
  ↓
5. GRAPH TRAVERSAL
   └─ Neo4j: Expand from mentioned entities
   └─ Depth: ≤2 hops
   └─ Relationship types: DEPENDS_ON, ROUTES_TO, MENTIONS
   └─ Output: Related entities + context
  ↓
6. SYNTHESIS
   └─ LlamaIndex QueryEngine
   └─ LLM: Qwen3-4B-Instruct (Ollama)
   └─ Prompt: Answer with inline citations [1][2]
   └─ Context: Chunks + graph context
   └─ Output: {answer: str, sources: []}
```

### Key Design Patterns

#### **1. Hexagonal Architecture (Ports & Adapters)**
**Purpose**: Decouple business logic from frameworks

**Implementation**:
- **Core**: Defines ports (interfaces) for repositories, services
- **Adapters**: Implement ports using specific technologies (Neo4j, Qdrant, FastAPI)
- **Apps**: Compose adapters and expose via protocols (HTTP, CLI, MCP)

**Example**:
```python
# Core: Define port
class DocumentRepository(Protocol):
    async def save(self, doc: Document) -> None: ...
    async def find_by_id(self, doc_id: str) -> Document | None: ...

# Adapter: PostgreSQL implementation
class PostgresDocumentRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def save(self, doc: Document) -> None:
        await self.pool.execute("INSERT INTO documents ...")

# App: Dependency injection
@router.post("/documents")
async def create_document(
    doc: Document,
    repo: DocumentRepository = Depends(get_document_repo)
):
    await repo.save(doc)
```

#### **2. Tiered Extraction Strategy**
**Purpose**: Balance speed vs. accuracy, minimize LLM costs

**Pattern**: Waterfall with early exit
- Tier A: Fast deterministic extraction (regex, parsers)
- Tier B: Medium-cost NLP (spaCy)
- Tier C: Expensive LLM (only for complex spans)

**Optimization**:
- Tier A extracts 60-70% of relations (low-hanging fruit)
- Tier B selects micro-windows for Tier C (reduce LLM tokens)
- Redis cache: De-duplicate identical windows across docs

#### **3. Batch Processing**
**Purpose**: Maximize throughput, minimize round-trips

**Implementations**:
- **Neo4j**: UNWIND batches (2k rows) → single transaction
- **Qdrant**: Batch upserts (5k vectors) → bulk indexing
- **Embeddings**: TEI batches (32 chunks) → GPU utilization
- **LLM**: Ollama batches (8-16 windows) → concurrent inference

#### **4. Hybrid Retrieval**
**Purpose**: Combine vector similarity + graph structure + LLM synthesis

**Strategy**:
- Vector search: Fast recall (cast wide net)
- Reranking: Precision boost (narrow to best matches)
- Graph traversal: Context enrichment (related entities)
- LLM synthesis: Natural language answer + citations

**Rationale**: Vector alone misses relationships, graph alone lacks semantic search

#### **5. Soft Delete + Audit Trail**
**Purpose**: GDPR compliance, accident prevention, forensics

**Implementation**:
- Prisma middleware: Intercept `delete()` → `update({deletedAt})`
- Automatic filtering: `findMany()` excludes soft-deleted
- Audit log: Every deletion → AuditLog table (permanent)
- Restoration: Admin API to undelete within 90 days
- Hard cleanup: Scheduled job (cron) after retention period

#### **6. Fail-Closed Security**
**Purpose**: Secure by default, explicit failures

**Examples**:
- **CSRF**: Missing token → 403 (never silently allow)
- **Rate limiting**: Redis down → 503 (never bypass)
- **Auth**: JWT validation fails → 401 (never assume unauthenticated access)

### Dependencies Between Modules

**Dependency Graph**:
```
apps/api ──────────────┐
apps/cli ──────────────┤
apps/mcp ──────────────┤
                        ├──→ packages/ingest ──┐
                        ├──→ packages/extraction ┤
                        ├──→ packages/graph ─────┤
                        ├──→ packages/vector ────┤
                        ├──→ packages/retrieval ─┤
                        │                        ├──→ packages/core ──→ packages/schemas
                        │                        │                   ──→ packages/common
                        └──→ packages/common ────┘

apps/web ──→ packages-ts/auth ──→ packages-ts/db
         ──→ packages-ts/api-client
         ──→ packages-ts/ui
         ──→ packages-ts/rate-limit
```

**Enforcement**:
- **Python**: `import-linter` checks
- **TypeScript**: `eslint-plugin-boundaries` rules

---

## 6. Environment & Setup Analysis

### Required Environment Variables

#### **Core Services**
```bash
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

# PostgreSQL
DATABASE_URL=postgresql://postgres:postgres@taboot-db:5432/taboot

# TEI Embeddings
TEI_EMBEDDING_URL=http://taboot-embed:80
TEI_EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B

# Reranker
RERANKER_URL=http://taboot-rerank:8000
RERANKER_MODEL=Qwen/Qwen3-Reranker-0.6B
RERANKER_BATCH_SIZE=16
RERANKER_DEVICE=auto  # cuda if GPU available

# Ollama
OLLAMA_HOST=http://taboot-ollama:11434
OLLAMA_MODEL=qwen3:4b
```

#### **Next.js Web App**
```bash
# Auth (Better-Auth)
AUTH_SECRET=<random-256-bit-hex>  # openssl rand -hex 32
AUTH_URL=http://localhost:3000

# Database (Prisma)
DATABASE_URL=postgresql://postgres:postgres@taboot-db:5432/taboot

# CSRF Protection
CSRF_SECRET=<random-256-bit-hex>  # Defaults to AUTH_SECRET if not set

# Rate Limiting
REDIS_URL=redis://taboot-cache:6379
TRUST_PROXY=false  # Set to 'true' only behind verified reverse proxy

# API Backend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

#### **External Services (Optional)**
```bash
# GitHub (for GitHub source ingestion)
GITHUB_TOKEN=ghp_...

# Reddit (for Reddit source ingestion)
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=taboot/0.1

# Gmail (for Gmail source ingestion)
GMAIL_CREDENTIALS_PATH=/path/to/credentials.json
GMAIL_TOKEN_PATH=/path/to/token.json

# Elasticsearch (for Elasticsearch source ingestion)
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_USER=elastic
ELASTICSEARCH_PASSWORD=changeme
```

### Installation and Setup Process

#### **Prerequisites**
1. **Python 3.11+** (managed via `uv`)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Node.js 20+** (LTS)
   ```bash
   # Via nvm
   nvm install 20
   nvm use 20
   ```

3. **pnpm** (package manager)
   ```bash
   npm install -g pnpm
   ```

4. **Docker + Compose V2**
   ```bash
   # Ubuntu
   sudo apt install docker.io docker-compose-v2
   sudo usermod -aG docker $USER
   ```

5. **NVIDIA GPU Setup** (for GPU acceleration)
   ```bash
   # Install NVIDIA driver (e.g., 550+)
   ubuntu-drivers autoinstall

   # Install nvidia-container-toolkit
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
     sudo tee /etc/apt/sources.list.d/nvidia-docker.list
   sudo apt-get update
   sudo apt-get install -y nvidia-container-toolkit
   sudo systemctl restart docker

   # Verify GPU access
   docker run --rm --gpus all nvidia/cuda:12.1-base nvidia-smi
   ```

#### **Setup Steps**

**1. Clone Repository**
```bash
git clone https://github.com/jmagar/taboot.git
cd taboot
```

**2. Install Python Dependencies**
```bash
uv sync  # Installs all workspace packages + dependencies
```

**3. Install JavaScript Dependencies**
```bash
pnpm install  # Installs all monorepo packages
```

**4. Configure Environment**
```bash
cp .env.example .env
$EDITOR .env  # Edit as needed (defaults work for local dev)
```

**5. Start Services**
```bash
docker compose up -d  # Start all 12 services

# Wait for health checks (30-60 seconds)
docker compose ps
```

**6. Initialize Schemas**
```bash
uv run apps/cli init  # Creates Neo4j constraints, Qdrant collections, PostgreSQL tables
```

**7. Verify Setup**
```bash
# Check API health
curl http://localhost:8000/health

# Check web app
curl http://localhost:3000/api/health

# Run tests
uv run pytest -m "not slow"  # Unit tests (~30 seconds)
```

### Development Workflow

#### **Daily Development**

**1. Start Services**
```bash
docker compose up -d taboot-graph taboot-vectors taboot-cache taboot-db taboot-embed taboot-ollama
# Skip crawler/playwright if not ingesting
```

**2. Run in Development Mode**
```bash
# Terminal 1: API server
uv run apps/api/app.py

# Terminal 2: CLI (one-off commands)
uv run taboot ingest web https://example.com --limit 10

# Terminal 3: Web app
cd apps/web && pnpm dev
```

**3. Code Quality Checks**
```bash
# Python
uv run ruff check .          # Linter
uv run ruff format .         # Formatter
uv run mypy .                # Type checker

# TypeScript
pnpm lint                    # ESLint
pnpm format                  # Prettier
pnpm type-check              # TypeScript
```

**4. Run Tests**
```bash
# Unit tests (fast)
uv run pytest -m "not slow" --cov=packages

# Integration tests (requires Docker services)
uv run pytest -m integration

# Web tests
pnpm --filter @taboot/web test
```

#### **Pre-Commit Hooks**
```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### Production Deployment Strategy

**Target**: Docker Compose on single GPU server (RTX 4070 or better)

#### **1. Deployment Checklist**

**Environment**:
- [ ] Generate secure secrets (`openssl rand -hex 32`)
- [ ] Set `AUTH_SECRET`, `CSRF_SECRET`, `NEO4J_PASSWORD`
- [ ] Configure `TRUST_PROXY=true` if behind reverse proxy
- [ ] Set production URLs (`AUTH_URL`, `NEXT_PUBLIC_API_URL`)

**Database**:
- [ ] Backup existing data (`pg_dump`, `neo4j-admin dump`)
- [ ] Run migrations (`uv run apps/cli init`)
- [ ] Verify schema versions (`uv run apps/cli schema version`)

**Docker**:
- [ ] Build production images (`docker compose build`)
- [ ] Push to registry (if using remote)
- [ ] Configure resource limits (memory, CPU)
- [ ] Set restart policies (`restart: unless-stopped`)

**Security**:
- [ ] Enable firewall (only expose 80, 443)
- [ ] Configure Nginx reverse proxy (HTTPS, rate limiting)
- [ ] Set up CSP headers
- [ ] Enable HSTS
- [ ] Configure CORS (whitelist origins)

**Monitoring**:
- [ ] Configure Prometheus scraping (`/metrics`)
- [ ] Set up Grafana dashboards
- [ ] Configure alerting (Prometheus Alertmanager)
- [ ] Enable structured logging (JSON to stdout)
- [ ] Set log retention policies

#### **2. Docker Compose Production Config**

**Changes from Development**:
- Remove volume mounts (use built-in code)
- Add restart policies
- Configure resource limits
- Use production secrets management
- Enable health checks
- Configure logging drivers

**Example Snippet**:
```yaml
services:
  taboot-api:
    image: ghcr.io/jmagar/taboot-api:latest
    restart: unless-stopped
    environment:
      - ENVIRONMENT=production
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
    healthcheck:
      test: curl -f http://localhost:8000/health || exit 1
      interval: 30s
      timeout: 10s
      retries: 3
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

#### **3. Scaling Strategy**

**Horizontal Scaling**:
- API: Scale to 3-5 replicas behind load balancer
- Worker: Scale based on queue depth (monitor Redis)
- Web: Scale to 2-3 replicas (stateless, session in Redis)

**Vertical Scaling**:
- Neo4j: Increase memory (recommend 16GB+)
- Qdrant: Ensure GPU access, increase cache size
- PostgreSQL: Increase shared_buffers, work_mem

**Limitations**:
- Single-user system: No multi-tenancy
- GPU services: Not horizontally scalable (single GPU)
- State: Redis, Neo4j, Qdrant, PostgreSQL (stateful, need backups)

#### **4. Backup Strategy**

**PostgreSQL** (daily):
```bash
pg_dump -h taboot-db -U postgres taboot > backup_$(date +%Y%m%d).sql
```

**Neo4j** (weekly):
```bash
docker exec taboot-graph neo4j-admin dump --to=/backups/neo4j_$(date +%Y%m%d).dump
```

**Qdrant** (snapshots):
```bash
curl -X POST http://taboot-vectors:6333/collections/chunks/snapshots
```

**Redis** (RDB snapshots):
```bash
docker exec taboot-cache redis-cli BGSAVE
```

#### **5. Monitoring Endpoints**

**Health Checks**:
- API: `GET http://taboot-api:8000/health`
- Web: `GET http://taboot-web:3000/api/health`
- Neo4j: Bolt connection test
- Qdrant: `GET http://taboot-vectors:6333/healthz`

**Metrics** (Prometheus):
- API: `GET http://taboot-api:8000/metrics`
- Neo4j: Port 2004 (Prometheus plugin)
- Qdrant: Port 6333/metrics

**Logs**:
- Centralized: Loki + Promtail (scrape Docker logs)
- Format: Structured JSON (pythonjsonlogger, pino)

---

## 7. Technology Stack Breakdown

### Runtime Environment

#### **Python Backend**
- **Version**: 3.11.0 - 3.13.7 (tested on 3.13)
- **Package Manager**: `uv` (Astral, Rust-based)
- **Workspace**: Monorepo with shared dependencies
- **Virtual Environment**: `.venv/` (auto-managed by uv)

#### **Node.js/TypeScript**
- **Version**: 20+ (LTS)
- **Package Manager**: `pnpm` (fast, disk-efficient)
- **Workspace**: Turborepo monorepo
- **Build Cache**: `.turbo/` (cross-machine caching)

### Frameworks and Libraries

#### **Backend Python**

**Web Framework**:
- **FastAPI** 0.115+ - Modern async API framework
- **Starlette** (ASGI) - Underlying web toolkit
- **Uvicorn** - ASGI server (production)

**CLI Framework**:
- **Typer** 0.15+ - Click-based CLI with type hints
- **Rich** - Terminal formatting, progress bars

**RAG Framework**:
- **LlamaIndex** 0.12+ - RAG orchestration
  - `llama-index-core` - Base functionality
  - `llama-index-llms-ollama` - Ollama LLM integration
  - `llama-index-embeddings` - TEI integration
  - `llama-index-vector-stores-qdrant` - Qdrant adapter
  - `llama-index-graph-stores-neo4j` - Neo4j adapter
  - `llama-index-readers-*` - Source readers (GitHub, Gmail, Web, YouTube)

**NLP**:
- **spaCy** 3.7+ - Industrial-strength NLP
  - Models: `en_core_web_md` (default), `en_core_web_trf` (transformer, optional)
  - Components: EntityRuler, DependencyMatcher
- **sentence-transformers** - Reranking (Qwen3-Reranker-0.6B)

**LLM Client**:
- **ollama** (Python SDK) - Qwen3-4B-Instruct integration
- **openai** (SDK) - Compatible with Ollama API

**Database Clients**:
- **neo4j** (async driver) - Graph database
- **qdrant-client** - Vector database
- **asyncpg** - PostgreSQL (async)
- **redis** (async) - Cache + queues

**Data Validation**:
- **Pydantic** 2.10+ - Data validation + serialization
- **pydantic-settings** - Environment variable parsing

**Crawling**:
- **firecrawl-py** - Firecrawl v2 SDK
- **playwright** - Browser automation
- **selenium** - Legacy browser automation
- **beautifulsoup4** - HTML parsing
- **html2text** - HTML → Markdown conversion

**Testing**:
- **pytest** 8.4+ - Test framework
- **pytest-asyncio** - Async test support
- **pytest-cov** - Coverage reporting
- **httpx** - HTTP client (test mocks)

**Code Quality**:
- **ruff** 0.14+ - Fast linter + formatter (replaces black, isort, flake8)
- **mypy** 1.15+ - Static type checker (strict mode)

**Observability**:
- **prometheus-client** - Metrics exposition
- **python-json-logger** - Structured JSON logging

#### **Frontend TypeScript**

**Framework**:
- **Next.js** 16.1+ - React framework (App Router, RSC)
- **React** 19+ - UI library
- **React DOM** 19+ - DOM rendering

**Auth**:
- **better-auth** - Authentication library (JWT, sessions, 2FA)
- **@better-auth/react** - React integration

**Database**:
- **Prisma** 6.2+ - TypeScript ORM
- **@prisma/client** - Generated type-safe client

**UI Components**:
- **@radix-ui/react-*** - Headless UI primitives (dialog, dropdown, etc.)
- **tailwindcss** 3.4+ - Utility-first CSS
- **tailwindcss-animate** - Animation utilities
- **class-variance-authority** - Component variants
- **clsx** + **tailwind-merge** - Class name merging

**State Management**:
- **zustand** (planned) - Lightweight state management
- **React Server Components** - Server-side state

**Forms**:
- **react-hook-form** - Form library
- **zod** - Schema validation

**HTTP Client**:
- **openapi-typescript** - Type-safe API client generation
- **openapi-fetch** - Fetch wrapper with OpenAPI types

**Testing**:
- **Vitest** - Fast unit test runner (Vite-based)
- **@testing-library/react** - Component testing utilities
- **@playwright/test** - E2E browser testing

**Code Quality**:
- **ESLint** 9+ - Linter (flat config)
- **Prettier** 3.6+ - Code formatter
- **TypeScript** 5.9+ - Static type checker (strict mode)

### Database Technologies

#### **Neo4j 5.23+** (Graph Database)
**Purpose**: Store knowledge graph (entities, relationships)

**Features**:
- **Cypher Query Language**: Declarative graph queries
- **APOC Procedures**: Advanced graph algorithms
- **Constraints**: Unique indexes on natural keys
- **Indexes**: Composite indexes for fast lookups

**Schema**:
- **Nodes**: Service, Host, IP, Proxy, Endpoint, Doc
- **Relationships**: DEPENDS_ON, ROUTES_TO, BINDS, RUNS, EXPOSES_ENDPOINT, MENTIONS

**Access**:
- **Protocol**: Bolt (port 7687)
- **Driver**: neo4j Python driver (async)

#### **Qdrant** (Vector Database)
**Purpose**: Store embeddings for semantic search

**Features**:
- **HNSW Indexing**: Fast approximate nearest neighbor search
- **GPU Acceleration**: NVIDIA CUDA support
- **Metadata Filtering**: Filter by source, date, tags
- **Hybrid Search**: Combine vector + metadata filters

**Collections**:
- `chunks`: Document chunks (1024 dim vectors)
- Payload: {doc_id, chunk_index, source, ingestion_timestamp, metadata}

**Access**:
- **HTTP API**: Port 6333
- **gRPC API**: Port 7001 (faster for bulk operations)
- **Client**: qdrant-client Python library

#### **PostgreSQL 16** (Relational Database)
**Purpose**: Store document metadata, job tracking, auth data

**Schemas**:
1. **`rag` schema** (Python backend):
   - `documents`: Ingested documents
   - `document_content`: Full text content
   - `ingestion_jobs`: Crawl job tracking
   - `extraction_jobs`: Extraction job tracking
   - `extraction_windows`: LLM processing windows
   - `schema_versions`: Database versioning

2. **`auth` schema** (Next.js web app):
   - `User`: User accounts (soft delete support)
   - `Session`: Active sessions
   - `Account`: OAuth provider accounts
   - `Verification`: Email verification tokens
   - `TwoFactor`: TOTP secrets
   - `AuditLog`: Permanent audit trail

**Access**:
- **Protocol**: libpq (port 5432)
- **Python Driver**: asyncpg (async)
- **TypeScript ORM**: Prisma

#### **Redis 7.2** (Cache + Queue)
**Purpose**: Caching, job queues, rate limiting

**Data Structures**:
- **Strings**: LLM prompt cache (SHA-256 keys)
- **Hashes**: Entity alias maps
- **Streams**: Extraction job queue
- **Lists**: DLQ (dead letter queue)
- **Sorted Sets**: Rate limiting (sliding window)

**Access**:
- **Protocol**: RESP (port 6379)
- **Python Driver**: redis (async)
- **TypeScript Driver**: ioredis

### Build Tools and Bundlers

#### **Python**
- **uv** 0.6+ - Package installer + resolver (Rust-based, fast)
  - Replaces: pip, pip-tools, virtualenv
  - Features: Lockfile (uv.lock), workspace support, parallel installs
- **pyproject.toml** - PEP 621 project metadata

#### **TypeScript**
- **Turborepo** 2.5+ - Monorepo build system
  - Features: Task caching, remote caching, parallel builds
  - Config: turbo.json
- **Next.js Compiler** (SWC) - Rust-based transpiler
  - Replaces: Babel, webpack (internal to Next.js)
- **pnpm** 10.4+ - Fast package manager
  - Features: Content-addressable store, hardlinks, workspace support

### Testing Frameworks

#### **Python**
- **pytest** 8.4+ - Test runner
- **pytest-asyncio** - Async test support
- **pytest-cov** - Coverage reporting (uses coverage.py)
- **pytest-mock** - Mocking utilities

**Markers**:
- `unit`: Fast unit tests (no external services)
- `integration`: Requires Docker services
- `slow`: Long-running tests (>10 seconds)
- Source-specific: `github`, `gmail`, `reddit`, `elasticsearch`, `firecrawl`

#### **TypeScript**
- **Vitest** 3.2+ - Unit test runner (Vite-based, fast HMR)
- **@testing-library/react** - React component testing
- **@playwright/test** - E2E browser testing
  - Features: Cross-browser (Chromium, Firefox, WebKit), video recording, screenshots

### Deployment Technologies

#### **Containerization**
- **Docker** - Container runtime
- **Docker Compose V2** - Multi-container orchestration
- **nvidia-container-toolkit** - GPU support in containers

#### **GPU Runtime**
- **NVIDIA CUDA** 12.1+ - GPU compute toolkit
- **cuDNN** - Deep learning primitives

#### **GPU Frameworks**
- **PyTorch** 2.5+ - Deep learning framework (for sentence-transformers)
- **TEI** (Text Embeddings Inference) - HuggingFace embedding server
- **Ollama** - Local LLM runtime (Qwen3-4B)

#### **CI/CD**
- **GitHub Actions** - Workflow automation
  - Workflows: `web-test.yml`, `docker-build.yml`
  - Caches: pnpm store, turbo cache, Docker layers

---

## 8. Visual Architecture Diagram

### High-Level System Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                  USERS                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐ │
│  │   Browser    │  │   Terminal   │  │   Claude     │  │   External      │ │
│  │  (Next.js)   │  │     (CLI)    │  │   Code/MCP   │  │   Services      │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └────────┬────────┘ │
└─────────┼──────────────────┼──────────────────┼────────────────────┼──────────┘
          │                  │                  │                    │
          │ HTTPS            │ Typer            │ JSON-RPC           │ Webhooks
          │                  │                  │                    │
┌─────────▼──────────────────▼──────────────────▼────────────────────▼──────────┐
│                           APPLICATION LAYER                                    │
│  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────────┐  │
│  │   Next.js Web      │  │   FastAPI API      │  │       MCP Server       │  │
│  │  ┌──────────────┐  │  │  ┌──────────────┐  │  │  ┌──────────────────┐  │  │
│  │  │ React        │  │  │  │ REST         │  │  │  │ Tool Handlers    │  │  │
│  │  │ Components   │  │  │  │ Endpoints    │  │  │  │ (Query, Ingest)  │  │  │
│  │  └──────────────┘  │  │  └──────────────┘  │  │  └──────────────────┘  │  │
│  │  ┌──────────────┐  │  │  ┌──────────────┐  │  │                        │  │
│  │  │ Server       │  │  │  │ Middleware   │  │  │                        │  │
│  │  │ Actions      │  │  │  │ (Auth, Rate) │  │  │                        │  │
│  │  └──────────────┘  │  │  └──────────────┘  │  │                        │  │
│  │  ┌──────────────┐  │  │                    │  │                        │  │
│  │  │ Better-Auth  │  │  │                    │  │                        │  │
│  │  │ (JWT + 2FA)  │  │  │                    │  │                        │  │
│  │  └──────────────┘  │  │                    │  │                        │  │
│  └────────┬───────────┘  └──────────┬─────────┘  └───────────┬────────────┘  │
│           │                         │                         │               │
│           │ API Client              │                         │               │
│           └─────────────────────────┼─────────────────────────┘               │
└─────────────────────────────────────┼─────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────┼─────────────────────────────────────────┐
│                           BUSINESS LOGIC (CORE)                                │
│  ┌────────────────────────────────────────────────────────────────────────┐   │
│  │                         Use Cases (Orchestration)                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │   │
│  │  │  Ingest     │  │  Extract    │  │   Query     │  │  Initialize  │  │   │
│  │  │  Pipeline   │  │  Pipeline   │  │   Pipeline  │  │   Schemas    │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └──────────────┘  │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│  ┌────────────────────────────────────────────────────────────────────────┐   │
│  │                      Domain Models (Entities)                           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │   │
│  │  │  Document   │  │  Extraction │  │   Chunk     │  │   Triple     │  │   │
│  │  │  Aggregate  │  │     Job     │  │  Metadata   │  │  (Entity+Rel)│  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └──────────────┘  │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│  ┌────────────────────────────────────────────────────────────────────────┐   │
│  │                      Ports (Interfaces)                                 │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │   │
│  │  │ Document    │  │   Graph     │  │   Vector    │  │   Retrieval  │  │   │
│  │  │ Repository  │  │   Writer    │  │   Store     │  │   Service    │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └──────────────┘  │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
┌─────────────────────────────────────┼─────────────────────────────────────────┐
│                         ADAPTER LAYER (IMPLEMENTATIONS)                        │
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐     │
│  │                    INGESTION ADAPTERS                                 │     │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │     │
│  │  │   Web    │  │  GitHub  │  │  Reddit  │  │ YouTube  │  │ Gmail  │ │     │
│  │  │(Firecrawl│  │(LlamaIdx)│  │  (PRAW)  │  │(yt-dlp)  │  │(GAPI)  │ │     │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───┬────┘ │     │
│  │       │             │             │             │             │      │     │
│  │       └─────────────┴─────────────┴─────────────┴─────────────┘      │     │
│  │                                  │                                    │     │
│  │                   ┌──────────────▼──────────────┐                     │     │
│  │                   │      Normalizer             │                     │     │
│  │                   │   (HTML → Markdown)         │                     │     │
│  │                   └──────────────┬──────────────┘                     │     │
│  │                                  │                                    │     │
│  │                   ┌──────────────▼──────────────┐                     │     │
│  │                   │   Semantic Chunker          │                     │     │
│  │                   │   (spaCy sentences)         │                     │     │
│  │                   └──────────────┬──────────────┘                     │     │
│  └────────────────────────────────────┬───────────────────────────────────┘     │
│                                       │                                         │
│  ┌──────────────────────────────────┼─────────────────────────────────────┐   │
│  │              EXTRACTION ADAPTERS  │                                     │   │
│  │  ┌───────────────────────────────▼────────────────────────────────┐    │   │
│  │  │                      Tier Orchestrator                          │    │   │
│  │  │                  (Select tier based on complexity)              │    │   │
│  │  └────┬───────────────────────┬──────────────────────┬─────────────┘    │   │
│  │       │                       │                      │                  │   │
│  │  ┌────▼────────┐   ┌──────────▼────────┐  ┌────────▼──────────────┐   │   │
│  │  │  Tier A     │   │    Tier B          │  │     Tier C            │   │   │
│  │  │(Deterministic│   │    (spaCy)         │  │  (Qwen3-4B LLM)       │   │   │
│  │  │ Regex/JSON) │   │  Entity Ruler      │  │  JSON Schema          │   │   │
│  │  │             │   │  Dep Matcher       │  │  ≤512 tokens          │   │   │
│  │  │ ≥50 pg/sec  │   │ ≥200 sent/sec      │  │  ≤250ms median        │   │   │
│  │  └─────────────┘   └────────────────────┘  └───────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                   RETRIEVAL ADAPTERS (LlamaIndex)                        │  │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │  │
│  │  │                    6-Stage Pipeline                                │  │  │
│  │  │  1. Query Embed (TEI) → 2. Metadata Filter                        │  │  │
│  │  │  3. Vector Search (Qdrant) → 4. Rerank (Qwen3)                    │  │  │
│  │  │  5. Graph Traverse (Neo4j ≤2 hops) → 6. Synthesize (LLM+citations)│  │  │
│  │  └───────────────────────────────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────────┐
│                    INFRASTRUCTURE LAYER (STORAGE)                            │
│                                    │                                         │
│  ┌─────────────────┐  ┌────────────▼──────────┐  ┌────────────────────────┐│
│  │   Neo4j 5.23+   │  │  Qdrant (Vectors)     │  │  PostgreSQL 16         ││
│  │  (Graph DB)     │  │  ┌──────────────────┐ │  │  ┌──────────────────┐  ││
│  │  ┌───────────┐  │  │  │ chunks           │ │  │  │ rag schema       │  ││
│  │  │ Nodes:    │  │  │  │ (1024 dim)   │ │  │  │ - documents      │  ││
│  │  │ Service   │  │  │  │ HNSW index       │ │  │  │ - extraction_jobs│  ││
│  │  │ Host      │  │  │  │ GPU-accelerated  │ │  │  │ - schema_versions│  ││
│  │  │ Endpoint  │  │  │  └──────────────────┘ │  │  └──────────────────┘  ││
│  │  │ Doc       │  │  │                       │  │  ┌──────────────────┐  ││
│  │  │           │  │  │  ┌──────────────────┐ │  │  │ auth schema      │  ││
│  │  │ Edges:    │  │  │  │ Qwen3-Reranker   │ │  │  │ - User (soft del)│  ││
│  │  │ DEPENDS_ON│  │  │  │ (FastAPI wrapper)│ │  │  │ - Session        │  ││
│  │  │ ROUTES_TO │  │  │  └──────────────────┘ │  │  │ - AuditLog       │  ││
│  │  │ MENTIONS  │  │  │                       │  │  └──────────────────┘  ││
│  │  └───────────┘  │  └───────────────────────┘  └────────────────────────┘│
│  │                 │                              │                        ││
│  │  Bolt :7687     │  HTTP :6333 / gRPC :7001    │  libpq :5432           ││
│  └─────────────────┘  └─────────────────────────┘  └────────────────────────┘│
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                       Redis 7.2 (Cache + Queue)                       │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  ┌───────────┐  │   │
│  │  │ LLM Prompt   │  │ Extraction   │  │ Rate Limit │  │ Entity    │  │   │
│  │  │ Cache        │  │ Job Queue    │  │ (Sliding   │  │ Aliases   │  │   │
│  │  │ (SHA-256)    │  │ (Streams)    │  │  Window)   │  │ (Hashes)  │  │   │
│  │  └──────────────┘  └──────────────┘  └────────────┘  └───────────┘  │   │
│  │                                                                       │   │
│  │  RESP :6379                                                           │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                        GPU SERVICES (NVIDIA Runtime)                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────────────┐ │
│  │  TEI Embeddings  │  │  Ollama LLM      │  │  Qdrant (GPU Indexing)     │ │
│  │  Qwen3-Embed     │  │  Qwen3-4B-Instruct│  │  HNSW on GPU               │ │
│  │  :80             │  │  :11434          │  │  :6333                     │ │
│  └──────────────────┘  └──────────────────┘  └────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Component Relationships

```
┌─────────────────────────────────────────────────────────────────────┐
│                         APP DEPENDENCIES                            │
└─────────────────────────────────────────────────────────────────────┘

apps/api ────────┐
apps/cli ────────┤
apps/mcp ────────┤
                 │
                 ├──→ packages/ingest ──────┐
                 ├──→ packages/extraction ──┤
                 ├──→ packages/graph ────────┤
                 ├──→ packages/vector ───────┤
                 ├──→ packages/retrieval ────┤
                 │                           │
                 │                           ├──→ packages/core ──┐
                 │                           │                    │
                 └──→ packages/common ───────┘                    │
                                                                  │
                                                                  ├──→ packages/schemas
                                                                  └──→ packages/common

apps/web ────┐
             ├──→ packages-ts/auth ──┐
             ├──→ packages-ts/db ────┤
             ├──→ packages-ts/ui ────┤──→ @radix-ui/*
             ├──→ packages-ts/api-client ──→ (Generated from OpenAPI)
             └──→ packages-ts/rate-limit ──→ ioredis
```

### Data Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                      INGESTION DATA FLOW                             │
└──────────────────────────────────────────────────────────────────────┘

User Query ────→ API/CLI
                   │
                   ▼
            Source Reader (Firecrawl/LlamaIndex/etc.)
                   │
                   ▼ Raw HTML/JSON
            Normalizer (HTML→Markdown)
                   │
                   ▼ Clean Markdown
            Chunker (spaCy sentences, 256-512 tokens)
                   │
                   ▼ Chunks[]
            TEI Embeddings (batch 32)
                   │
                   ├──→ Qdrant (vectors + metadata)
                   ├──→ PostgreSQL (document records)
                   └──→ Redis Streams (extraction queue)

┌──────────────────────────────────────────────────────────────────────┐
│                     EXTRACTION DATA FLOW                             │
└──────────────────────────────────────────────────────────────────────┘

Redis Streams Consumer (Worker)
                   │
                   ▼
            Tier Orchestrator
                   │
      ┌────────────┼────────────┐
      │            │            │
      ▼            ▼            ▼
  Tier A       Tier B       Tier C
  (Regex)      (spaCy)      (LLM)
      │            │            │
      └────────────┼────────────┘
                   │
                   ▼ Triples (Entity, Relation, Entity)
            Neo4j Writer (UNWIND batch 2k)
                   │
                   ▼
            Graph Database (Service, Host, Endpoint nodes)

┌──────────────────────────────────────────────────────────────────────┐
│                       QUERY DATA FLOW                                │
└──────────────────────────────────────────────────────────────────────┘

User Query ────→ API/CLI/Web
                   │
                   ▼
            Query Embedding (TEI)
                   │
                   ▼
            Qdrant Vector Search (top-k=50)
                   │
                   ▼
            Qwen3 Reranker (top-k=10)
                   │
                   ▼
            Neo4j Graph Traversal (≤2 hops)
                   │
                   ▼
            LLM Synthesis (Qwen3-4B + context)
                   │
                   ▼
            {answer: str, sources: [...]}
                   │
                   ▼
            User Response (with citations)
```

---

## 9. Key Insights & Recommendations

### Code Quality Assessment

#### **Strengths**

1. **Architectural Discipline**
   - Strict hexagonal architecture enforced via linters
   - Clear separation: apps → adapters → core
   - Framework-agnostic business logic (testable, portable)
   - Zero reverse dependencies (core never imports frameworks)

2. **Type Safety**
   - Python: mypy strict mode, Pydantic V2
   - TypeScript: strict mode, generated API types (OpenAPI)
   - Shared schemas (consistency across Python/TypeScript)

3. **Performance Optimization**
   - Batch processing everywhere (Neo4j, Qdrant, TEI, LLM)
   - GPU acceleration (TEI, Qdrant, Ollama)
   - Redis caching (LLM prompts, entities)
   - Async I/O (asyncpg, neo4j, httpx)

4. **Testing Strategy**
   - Unit tests for all core logic
   - Integration tests for full pipelines
   - Pytest markers for selective runs
   - Coverage tracking (target ≥85%)

5. **Security**
   - Fail-closed semantics (CSRF, rate limiting)
   - JWT + session dual-token auth
   - HTTPS enforcement (production)
   - CSP headers (XSS prevention)
   - Soft delete + audit trail (GDPR)

#### **Weaknesses & Areas for Improvement**

1. **Test Coverage Gaps**
   - **Current**: Unit tests exist, but coverage varies
   - **Missing**: E2E tests for full RAG pipeline (ingest → extract → query)
   - **Recommendation**:
     - Add Playwright E2E tests for web app (authentication flow, query interface)
     - Add integration tests for multi-source ingestion
     - Measure coverage: `uv run pytest --cov=packages --cov-report=html`

2. **Error Handling**
   - **Current**: Basic try/catch, some exceptions logged
   - **Missing**: Structured error taxonomy, retry policies
   - **Recommendation**:
     - Define error hierarchy (TransientError, PermanentError, UserError)
     - Implement retry with exponential backoff (tenacity library)
     - Add circuit breakers for external services (neo4j, qdrant)
     - Example:
       ```python
       from tenacity import retry, stop_after_attempt, wait_exponential

       @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
       async def query_neo4j(query: str):
           # Retries on connection errors, fails fast on syntax errors
       ```

3. **Observability Gaps**
   - **Current**: Prometheus metrics, JSON logs
   - **Missing**: Distributed tracing, correlation IDs
   - **Recommendation**:
     - Add OpenTelemetry instrumentation
     - Trace requests: `API → Ingest → Chunk → Embed → Store`
     - Correlation IDs: Pass `request_id` through entire pipeline
     - Example tools: Jaeger (tracing), Grafana Loki (logs)

4. **Documentation**
   - **Current**: Extensive markdown docs, inline comments
   - **Missing**: API examples, architecture diagrams (visual)
   - **Recommendation**:
     - Add Mermaid diagrams to docs (sequence diagrams, architecture)
     - Create video walkthrough (setup → ingest → query)
     - API examples: cURL + Python SDK + JavaScript

5. **Dependency Management**
   - **Current**: uv + pnpm (modern, fast)
   - **Risk**: Dependency updates break compatibility
   - **Recommendation**:
     - Pin major versions only (allow minor/patch updates)
     - Weekly dependabot PRs (automated updates)
     - Lock files in CI (prevent surprise updates)

### Potential Improvements

#### **1. Performance Optimizations**

**a. Caching Strategy**
- **Current**: Redis cache for LLM prompts (SHA-256 keys)
- **Improvement**: Add multi-layer cache
  - L1: In-memory LRU (lru_cache for hot queries)
  - L2: Redis (shared across workers)
  - L3: Disk (embeddings, large responses)

**b. Batch Size Tuning**
- **Current**: Fixed batch sizes (32 chunks, 16 LLM windows)
- **Improvement**: Dynamic batching based on GPU memory
  - Monitor VRAM usage (`nvidia-smi`)
  - Increase batch size if <80% utilization
  - Adaptive batching library: `huggingface_hub.InferenceClient.auto_batch`

**c. Parallel Extraction**
- **Current**: Single worker, sequential tier processing
- **Improvement**: Parallel workers + tier parallelization
  - Worker pool: 3-5 workers (CPU-bound for Tier A/B)
  - Tier parallelization: Run Tier A + Tier B concurrently
  - Pub/sub: Redis Streams with consumer groups

**d. Index Optimization**
- **Neo4j**: Add composite indexes on frequent queries
  - Example: `CREATE INDEX endpoint_lookup ON Endpoint(service, method, path)`
- **Qdrant**: Tune HNSW parameters (m, ef_construct)
  - Higher `m` → better recall, slower indexing
  - Higher `ef_construct` → better index quality

#### **2. Security Enhancements**

**a. Secrets Management**
- **Current**: Environment variables in .env
- **Improvement**: Secrets manager (Vault, AWS Secrets Manager)
  - Rotate secrets automatically (JWT keys, database passwords)
  - Audit secret access (who, when, what)

**b. Rate Limiting Improvements**
- **Current**: Fixed limits (5/10min for passwords)
- **Improvement**: Adaptive rate limiting
  - User reputation scores (trust established users)
  - Geographic rate limits (block suspicious regions)
  - Challenge-response (CAPTCHA after N failures)

**c. Content Security Policy**
- **Current**: CSP headers set
- **Improvement**: Stricter CSP
  - Remove `unsafe-inline` (move inline scripts to files)
  - Add `nonce` for dynamic scripts
  - Report-only mode → enforce mode (gradual rollout)

**d. Audit Logging**
- **Current**: Basic audit log (User actions)
- **Improvement**: Comprehensive audit trail
  - Log all mutations (create, update, delete)
  - Include context (IP, user-agent, session ID)
  - Tamper-proof (signed with HMAC, write-once storage)

#### **3. Maintainability Improvements**

**a. Monorepo Tooling**
- **Current**: Turborepo (JS), uv (Python)
- **Improvement**: Unified monorepo tool (Nx, Bazel)
  - Cross-language task graph (Python tests → JS tests)
  - Affected detection (only test changed packages)
  - Remote caching (share build artifacts)

**b. Code Generation**
- **Current**: OpenAPI → TypeScript client
- **Improvement**: Bidirectional code generation
  - Pydantic models → OpenAPI (ensure sync)
  - OpenAPI → Python client (for testing)
  - GraphQL schema → TypeScript types (if GraphQL added)

**c. Dependency Injection**
- **Current**: Manual DI in FastAPI (Depends)
- **Improvement**: DI container (python-dependency-injector)
  - Centralized configuration (swap implementations)
  - Lifecycle management (singleton, transient)
  - Easier testing (mock entire dependency tree)

**d. Database Migrations**
- **Current**: Manual SQL scripts, version tracking
- **Improvement**: Migration tool (Alembic for Python, Prisma for TS)
  - Auto-generate migrations from schema changes
  - Rollback support (undo bad migrations)
  - Schema versioning (track history)

#### **4. Scalability Improvements**

**a. Horizontal Scaling**
- **Current**: Single instance per service
- **Improvement**: Load balancing + auto-scaling
  - API: 3-5 replicas behind ALB/nginx
  - Worker: Scale based on queue depth (Redis Streams lag)
  - Web: 2-3 replicas (stateless, session in Redis)

**b. Database Sharding**
- **Current**: Single PostgreSQL instance
- **Improvement**: Shard by tenant/source
  - Tenant sharding: Each user → separate database
  - Source sharding: web docs → shard 1, github → shard 2
  - Tools: Citus (PostgreSQL sharding), Vitess (MySQL)

**c. Caching Layer**
- **Current**: Redis (shared state)
- **Improvement**: CDN + edge caching
  - CDN: Static assets (Cloudflare, Fastly)
  - Edge compute: Lambda@Edge (auth, rate limiting)
  - Cache query results (TTL: 5 minutes)

**d. GPU Pooling**
- **Current**: Single GPU per service (TEI, Ollama)
- **Improvement**: GPU pool + queue
  - Pool: Multiple GPUs, shared queue
  - Load balancing: Round-robin or least-loaded
  - Tools: Ray (distributed computing), Triton (inference server)

#### **5. User Experience Improvements**

**a. Real-Time Updates**
- **Current**: Polling for job status
- **Improvement**: WebSockets or SSE (Server-Sent Events)
  - Push status updates to browser
  - Live progress bars (ingestion, extraction)
  - Example: Socket.IO, Pusher

**b. Query Suggestions**
- **Current**: Freeform text input
- **Improvement**: Autocomplete + suggestions
  - Extract common queries from history
  - Suggest related queries based on current query
  - Example: ElasticSearch suggester, OpenAI embeddings

**c. Source Attribution UI**
- **Current**: JSON array of sources
- **Improvement**: Visual source cards
  - Show document preview (title, snippet, URL)
  - Clickable citations (scroll to relevant chunk)
  - Source ranking (relevance score)

**d. Query History**
- **Current**: No history
- **Improvement**: Saved queries + favorites
  - Store in PostgreSQL (user_id, query, timestamp)
  - UI: Recent queries, starred queries
  - Analytics: Popular queries, slow queries

### Performance Optimization Opportunities

#### **1. Query Pipeline**

**Bottleneck Analysis**:
- **Embedding** (10-50ms): Fast, GPU-accelerated
- **Vector Search** (50-100ms): HNSW is fast, but scales with top-k
- **Reranking** (100-300ms): Cross-encoder is slow
- **Graph Traversal** (50-200ms): Depends on hop depth
- **LLM Synthesis** (500-2000ms): Slowest step

**Optimization Priority**:
1. **LLM Synthesis** (biggest gain):
   - Cache common questions (SHA-256 of query + context)
   - Streaming responses (start returning before full completion)
   - Quantization: 4-bit Qwen3 (faster, same quality)

2. **Reranking** (second biggest):
   - Reduce candidates: 50 → 20 before reranking
   - Smaller reranker: Qwen3-Reranker-0.5B (faster, slight quality loss)
   - GPU batching: Rerank 20 in parallel

3. **Graph Traversal** (optimization):
   - Limit hop depth: 2 → 1 for fast queries
   - Cache common paths (service → dependencies)
   - Index hot relationships (DEPENDS_ON, MENTIONS)

#### **2. Extraction Pipeline**

**Bottleneck Analysis**:
- **Tier A** (10-20ms/page): Fast
- **Tier B** (20-50ms/page): spaCy is CPU-bound
- **Tier C** (200-500ms/window): LLM is slow

**Optimization Priority**:
1. **Tier C LLM** (biggest gain):
   - Reduce windows: Better Tier B filtering (precision over recall)
   - Smaller model: Qwen3-2B (faster, slight quality loss)
   - Batch larger: 16 → 32 windows (GPU utilization)

2. **Tier B spaCy** (CPU-bound):
   - Parallel processing: 4-8 worker processes (multiprocessing)
   - Lighter model: en_core_web_sm (3x faster, slight quality loss)
   - Disable unused components (NER, lemmatizer if not needed)

3. **Tier A Regex** (already fast):
   - Compile patterns once (re.compile)
   - Use Aho-Corasick for multi-pattern search

#### **3. Storage Writes**

**Bottleneck Analysis**:
- **Neo4j** (100-500ms/batch): UNWIND is fast, but locks graph
- **Qdrant** (50-200ms/batch): HNSW indexing is GPU-accelerated
- **PostgreSQL** (10-50ms/batch): Fast for bulk inserts

**Optimization Priority**:
1. **Neo4j UNWIND**:
   - Increase batch size: 2k → 5k rows (fewer transactions)
   - Parallel writes: Multiple workers, different node types
   - Avoid locks: Use MERGE sparingly (CREATE if possible)

2. **Qdrant Indexing**:
   - Increase batch size: 5k → 10k vectors (better GPU utilization)
   - Async indexing: Continue ingestion while indexing
   - Tune HNSW: Higher ef_construct (better quality, slower)

3. **PostgreSQL**:
   - Connection pooling: 20-50 connections (asyncpg)
   - Bulk inserts: COPY instead of INSERT (10x faster)
   - Disable constraints during bulk load (re-enable after)

### Maintainability Suggestions

#### **1. Code Organization**

**Current Structure**: Good separation (apps/packages), but some large files

**Improvements**:
- **Split large files**:
  - `apps/api/routes/query.py` (200+ lines) → split by endpoint
  - `packages/extraction/tier_c/llm_extractor.py` (300+ lines) → separate window selection, LLM calls, caching
- **Create utility modules**:
  - `packages/common/retry.py` - Centralized retry logic
  - `packages/common/circuit_breaker.py` - Circuit breaker pattern
- **Extract constants**:
  - Magic numbers (512 tokens, 2k batch) → named constants
  - File: `packages/common/constants.py`

#### **2. Testing Strategy**

**Current**: Good unit tests, some integration tests

**Improvements**:
- **Increase E2E coverage**:
  - Full RAG pipeline: ingest web → extract → query → verify citations
  - Multi-source: Ingest GitHub + Reddit → query combined
  - Failure scenarios: Neo4j down, Qdrant down, LLM timeout
- **Property-based testing**:
  - Use Hypothesis (Python) to generate random inputs
  - Test invariants: "Extracted triples always have 3 fields"
- **Performance regression tests**:
  - Benchmark queries: Store p50/p95/p99 latencies
  - Fail if latency increases >20% (performance CI)
- **Contract testing**:
  - OpenAPI → Pact contracts (API consumer/provider)
  - Ensure TypeScript client matches Python API

#### **3. Documentation**

**Current**: Extensive markdown, inline comments

**Improvements**:
- **Architecture diagrams**:
  - Mermaid: Sequence diagrams (request flow), C4 diagrams (architecture)
  - PlantUML: Component diagrams, deployment diagrams
- **API documentation**:
  - Swagger UI (built-in FastAPI)
  - ReDoc (alternate OpenAPI renderer)
  - Postman collection (importable API examples)
- **Video tutorials**:
  - Setup walkthrough (0 to running query in 10 minutes)
  - Architecture deep dive (explain hexagonal pattern)
  - Deployment guide (Docker Compose → production)
- **Decision records**:
  - ADRs (Architecture Decision Records) in `docs/adrs/`
  - Template: Context, Decision, Consequences
  - Examples: "Why Neo4j over PostgreSQL graph?", "Why Qwen3 over commercial LLMs?"

#### **4. CI/CD**

**Current**: GitHub Actions (web tests, Docker builds)

**Improvements**:
- **Expand CI checks**:
  - Python tests (unit + integration)
  - Code coverage (fail if <85%)
  - Security scans (Snyk, Dependabot)
  - Docker image scans (Trivy, Clair)
- **CD Pipeline**:
  - Auto-deploy to staging (on merge to main)
  - Manual approval for production
  - Blue-green deployments (zero downtime)
  - Rollback strategy (previous Docker tag)
- **Performance CI**:
  - Benchmark queries on every PR
  - Compare to baseline (fail if >20% slower)
  - Tools: pytest-benchmark, GitHub Actions artifacts

### Security Considerations

#### **1. Authentication & Authorization**

**Current**: Better-Auth (JWT + sessions), 2FA optional

**Improvements**:
- **Enforce 2FA**: Require for admin actions (user deletion, data export)
- **Session management**: Auto-logout after 30 minutes inactivity
- **Credential rotation**: Force password reset every 90 days
- **OAuth providers**: Add Microsoft, GitLab (in addition to GitHub, Google)

#### **2. Data Protection**

**Current**: HTTPS (production), database encryption at rest

**Improvements**:
- **Field-level encryption**: Encrypt sensitive fields (email, IP addresses)
  - Use PostgreSQL pgcrypto extension
  - Key management: AWS KMS, Vault
- **Data masking**: Redact sensitive data in logs (emails, IPs)
  - Example: `user@example.com` → `u***@e*****.com`
- **Anonymization**: Replace PII with pseudonyms (user IDs)
  - GDPR compliance: Right to erasure

#### **3. Network Security**

**Current**: Docker internal network, services not exposed

**Improvements**:
- **Service mesh**: Istio, Linkerd (mTLS between services)
- **Firewall rules**: Only allow necessary ports (80, 443)
- **VPN**: Require VPN for admin access (Neo4j, Qdrant dashboards)
- **DDoS protection**: Cloudflare, AWS Shield

#### **4. Supply Chain Security**

**Current**: Dependency pinning (uv.lock, pnpm-lock.yaml)

**Improvements**:
- **Dependency scanning**: Snyk, Dependabot (auto PRs for CVEs)
- **License compliance**: Check licenses (FOSSA, BlackDuck)
- **SBOM**: Generate Software Bill of Materials (CycloneDX)
  - Track all dependencies + versions
  - Audit for vulnerabilities
- **Signed commits**: Require GPG signatures (verify commit author)

#### **5. Incident Response**

**Current**: Runbook (`apps/api/docs/RUNBOOK.md`)

**Improvements**:
- **Incident playbooks**: Step-by-step guides for common incidents
  - Neo4j down → Switch to read-only mode
  - Qdrant down → Fall back to keyword search
  - LLM timeout → Return partial results
- **Automated remediation**: Self-healing scripts
  - Restart failed services
  - Scale up under load
  - Rollback bad deployments
- **Post-incident reviews**: Blameless retrospectives
  - What happened? Why? How to prevent?
  - Update runbooks, add alerts

---

## Final Recommendations

### Immediate Actions (Next 1-2 Sprints)

1. **Add E2E Tests** (Priority: High)
   - Full RAG pipeline test (ingest → extract → query)
   - Playwright tests for web authentication flow
   - Target: 70% E2E coverage

2. **Improve Error Handling** (Priority: High)
   - Define error hierarchy (TransientError, PermanentError)
   - Add retry policies (tenacity)
   - Circuit breakers for external services

3. **Expand Observability** (Priority: Medium)
   - Add OpenTelemetry tracing
   - Correlation IDs across pipeline
   - Grafana dashboards (latency, throughput, errors)

4. **Security Hardening** (Priority: High)
   - Enforce 2FA for admin actions
   - Secrets manager (Vault, AWS Secrets Manager)
   - Dependency scanning (Snyk, Dependabot)

### Mid-Term Goals (3-6 Months)

1. **Performance Optimization**
   - Cache query results (Redis, 5-minute TTL)
   - Streaming LLM responses (start returning before completion)
   - Parallel extraction workers (3-5 workers)

2. **Scalability**
   - Horizontal scaling (API, worker, web)
   - Load balancing (ALB, nginx)
   - Database sharding (tenant-based)

3. **User Experience**
   - Real-time status updates (WebSockets)
   - Query suggestions (autocomplete)
   - Visual source attribution UI

4. **Maintainability**
   - Mermaid diagrams in docs
   - Video tutorials (setup, architecture)
   - Expand CI checks (security scans, performance tests)

### Long-Term Vision (6-12 Months)

1. **Multi-Tenancy**
   - Separate databases per tenant
   - Tenant isolation (Neo4j, Qdrant)
   - Usage quotas (rate limiting per tenant)

2. **Advanced Features**
   - Multi-hop reasoning (graph + LLM)
   - Query optimization (automatic query rewriting)
   - Document versioning (track changes over time)

3. **Cloud-Native Deployment**
   - Kubernetes (EKS, GKE, AKS)
   - Helm charts (templated deployments)
   - Service mesh (Istio, Linkerd)

4. **AI Improvements**
   - Fine-tune extractors (spaCy, LLM)
   - Active learning (user feedback → training data)
   - Multi-modal RAG (images, PDFs, videos)

---

## Conclusion

**Taboot** is a well-architected, production-ready RAG platform with:
- **Strengths**: Clean architecture, type safety, GPU acceleration, comprehensive testing
- **Opportunities**: E2E tests, error handling, observability, scalability

The codebase demonstrates strong engineering discipline (hexagonal architecture, dependency injection, batch processing) and is well-positioned for growth. Key improvements should focus on:
1. **Testing** (E2E coverage, performance regression tests)
2. **Observability** (tracing, metrics dashboards)
3. **Scalability** (horizontal scaling, caching layers)
4. **Security** (secrets management, audit logging)

With these improvements, Taboot can scale from single-user to multi-tenant production deployment while maintaining code quality and performance.

---

**Generated**: 2025-10-26
**Codebase Version**: 0.4.0
**Analysis Tool**: Claude Code (Sonnet 4.5)
